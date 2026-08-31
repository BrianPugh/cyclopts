"""Runtime engine for dynamic (Python-invoked) shell completion.

Unlike the *static* generators in this package (``bash``/``zsh``/``fish``),
which bake commands, options, and statically-enumerable choices into a shell
script at install time, this module runs *at completion time*. The generated
script calls back into the application through the reserved ``__complete``
command (see :meth:`cyclopts.App.__call__`), which routes here to compute
candidate values by invoking user-supplied :attr:`.Parameter.completer`
callbacks.

The static script remains responsible for subcommand names, option names, and
static choice lists; this engine only contributes the values a completer emits.
"""

import os
import sys
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, NamedTuple

from attrs import field

from cyclopts.exceptions import CycloptsError
from cyclopts.field_info import VAR_KEYWORD
from cyclopts.utils import UNSET, frozen


def completion_debug_enabled() -> bool:
    """Whether the ``CYCLOPTS_COMPLETION_DEBUG`` diagnostic is switched on."""
    return bool(os.environ.get("CYCLOPTS_COMPLETION_DEBUG"))


def _exc(e: BaseException) -> str:
    """Concise one-line exception summary (Cyclopts error reprs are enormous)."""
    text = str(e).strip().splitlines()
    summary = text[0] if text else ""
    return f"{type(e).__name__}: {summary}"[:200] if summary else type(e).__name__


def debug(message: str) -> None:
    """Print a completion diagnostic to stderr when ``CYCLOPTS_COMPLETION_DEBUG`` is set.

    Runtime completion normally swallows everything (a stray byte on stdout, or a
    traceback, corrupts the shell's candidate list). This is the escape hatch:
    with the env var set, run ``<prog> __complete <words...>`` by hand and watch
    how the engine resolves the active argument and what the completer returns.
    """
    if completion_debug_enabled():
        print(f"[cyclopts:completion] {message}", file=sys.stderr)


if TYPE_CHECKING:
    from cyclopts import App
    from cyclopts.argument import Argument, ArgumentCollection

#: What a :attr:`.Parameter.completer` may return: a single value, or an iterable
#: of values and/or ``(value, description)`` tuples.
CompletionResult = str | Iterable[str | tuple[str, str]]

#: The signature of a :attr:`.Parameter.completer` callback.
Completer = Callable[["CompletionContext"], "CompletionResult"]


class Completion(NamedTuple):
    """A single dynamic completion candidate emitted to the shell."""

    value: str
    help: str = ""


@frozen
class ArgumentValue:
    """A best-effort view of what the user has already typed for one argument.

    Handed out by :meth:`CompletionContext.__getitem__`. Provides both the raw
    string a user typed and a best-effort coerced value, so a completer can make
    decisions based on *other* arguments already present on the command line.
    """

    argument: "Argument"

    @property
    def provided(self) -> bool:
        """Whether the user has supplied a value for this argument yet."""
        return self.argument.has_tokens

    @property
    def raw(self) -> str | None:
        """The raw string the user typed, or :obj:`None` if not provided.

        For multi-token arguments this is the first token; use :attr:`raw_tokens`
        for the full list.
        """
        tokens = self.argument.tokens
        return tokens[0].value if tokens else None

    @property
    def raw_tokens(self) -> tuple[str, ...]:
        """Every raw string token supplied for this argument, in order."""
        return tuple(token.value for token in self.argument.tokens)

    @property
    def value(self) -> Any:
        """Best-effort coerced value, or :obj:`~.UNSET` if unavailable.

        Runs the argument's normal type conversion over the tokens typed so far,
        which means it may invoke a user-supplied :attr:`.Parameter.converter` on
        partial input. Intended for the common cases (``str``/``int``/``Path``/
        ``Literal``/``Enum``/simple unions); if conversion fails (partial input,
        or a complex type) this returns :obj:`~.UNSET` rather than raising. The
        value is *not* validated.
        """
        if not self.argument.has_tokens:
            return UNSET
        try:
            return self.argument.convert()
        except Exception:
            return UNSET


@frozen
class CompletionContext:
    """Completion-time context passed to a :attr:`.Parameter.completer`.

    A completer is always invoked as ``completer(context)``. The word being
    completed is :attr:`incomplete`; the values the user has already typed for
    other arguments are reachable via ``context[name]``.
    """

    incomplete: str
    argument: "Argument"
    arguments: "ArgumentCollection"
    tokens: tuple[str, ...] = field(factory=tuple)

    @property
    def parameter(self):
        """The :class:`.Parameter` of the argument currently being completed."""
        return self.argument.parameter

    def _match(self, name: str) -> "Argument":
        try:
            argument, _, _ = self.arguments.match(name)
            return argument
        except ValueError:
            pass
        for argument in self.arguments:
            if argument.field_info.name == name or name in argument.names or f"--{name}" in argument.names:
                return argument
        raise KeyError(name)

    def __getitem__(self, name: str) -> ArgumentValue:
        """Look up an argument by option name (``"--region"``/``"region"``) or field name."""
        return ArgumentValue(self._match(name))

    def get(self, name: str, default: Any = None) -> "ArgumentValue | Any":
        """Like ``context[name]`` but returns ``default`` for an unknown ``name``."""
        try:
            return self[name]
        except KeyError:
            return default


def normalize_completions(result: "CompletionResult | None") -> list[tuple[str, str]]:
    """Normalize a completer's return value to ``(value, description)`` pairs.

    A bare :class:`str` is a single candidate (never iterated per-character). A
    :class:`tuple` is likewise a single record - ``(value,)`` or
    ``(value, description)`` - so ``("us-west", "Oregon")`` is one described
    candidate, not two. Any other iterable (list, set, generator, ...) is a
    collection whose items are each a ``str`` or a ``(value, description)`` tuple.
    """
    if result is None:
        return []
    if isinstance(result, (str, tuple)):
        return [_normalize_item(result)]
    return [_normalize_item(item) for item in result]


def _normalize_item(item: "str | tuple") -> tuple[str, str]:
    if isinstance(item, str):
        return (item, "")
    value, *rest = item
    return (str(value), str(rest[0]) if rest else "")


def _value_option_argument(arguments: "ArgumentCollection", token: str) -> "Argument | None":
    """Return the argument ``token`` names iff it consumes a value (not a flag)."""
    if not token.startswith("-") or "=" in token:
        return None
    try:
        argument, _, implicit_value = arguments.match(token)
    except ValueError:
        return None
    if implicit_value is not UNSET or argument.is_flag():
        return None  # a flag/count: no value token follows
    return argument


def _positional_arguments(arguments: "ArgumentCollection") -> list["Argument"]:
    """Arguments (in signature order) that can be filled positionally."""
    return [
        argument
        for argument in arguments
        if argument.show and argument.field_info.is_positional and argument.field_info.kind is not VAR_KEYWORD
    ]


def _active_positional(arguments: "ArgumentCollection", prior: list[str]) -> "Argument | None":
    """Resolve which positional slot the next token would fill.

    Walks the already-typed ``prior`` tokens, skipping option names and their
    value tokens, to count how many positional values have been consumed.
    """
    positionals = _positional_arguments(arguments)
    consumed = 0
    skip_next = False
    for token in prior:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            if _value_option_argument(arguments, token) is not None:
                skip_next = True  # the following token is this option's value
            continue
        consumed += 1
    if consumed < len(positionals):
        return positionals[consumed]
    return None


def _attach_prior_tokens(arguments: "ArgumentCollection", prior: list[str]) -> None:
    """Best-effort: distribute already-typed ``prior`` tokens onto ``arguments``.

    Reuses the real parser (:func:`._parse_kw_and_flags`/:func:`._parse_pos`) so
    ``--opt=value``, ``--opt value``, and positionals all land on the right
    argument, but deliberately stops short of ``_convert``/validation so partial
    input never raises. Whatever attaches before an error is kept. Safe to mutate
    ``arguments`` in place because the collection is freshly assembled per
    :func:`compute_completions` call and discarded afterward.
    """
    from cyclopts.bind import _parse_kw_and_flags, _parse_pos

    try:
        unused, _, contiguous, _ = _parse_kw_and_flags(arguments, prior)
        _parse_pos(arguments, unused, contiguous_positional_count=contiguous)
    except Exception as e:
        debug(f"attaching prior tokens {prior!r} failed (sibling values may be partial): {_exc(e)}")


def compute_completions(app: "App", words: list[str]) -> list[Completion]:
    """Compute dynamic completion candidates for a partial command line.

    Parameters
    ----------
    app : App
        Root application.
    words : list[str]
        Command-line words following the program name. The final element is the
        (possibly empty) word currently being completed; everything before it is
        already-committed input.

    Returns
    -------
    list[Completion]
        Candidates contributed by :attr:`.Parameter.completer` callbacks for the
        active slot. Empty when the active slot has no dynamic completer (static
        choices, subcommand names, and option names are handled by the generated
        script, not here).
    """
    if not words:
        words = [""]
    prior, incomplete = words[:-1], words[-1]
    debug(f"words={words!r} prior={prior!r} incomplete={incomplete!r}")

    # Resolve the active command from the tokens typed so far. ``unused`` strips
    # the resolved command chain, leaving only option/positional tokens so slot
    # accounting below never miscounts a subcommand name as a positional value.
    try:
        command_chain, execution_path, unused = app.parse_commands(prior)
    except (CycloptsError, ValueError, TypeError) as e:
        debug(f"command resolution failed for {prior!r}: {_exc(e)}")
        return []
    command_app = execution_path[-1]
    debug(f"resolved command={command_chain!r} unused={unused!r}")

    if command_app.default_command is None:
        debug("resolved command has no default_command; nothing to complete")
        return []
    try:
        arguments = command_app.assemble_argument_collection(parse_docstring=False)
    except Exception as e:
        debug(f"assembling arguments failed: {_exc(e)}")
        return []

    active: Argument | None = None

    # Case 1: completing the *value* of the preceding option (e.g. ``--user <TAB>``).
    if unused:
        active = _value_option_argument(arguments, unused[-1])

    # Case 2: completing a positional value (not an option name).
    if active is None and not incomplete.startswith("-"):
        active = _active_positional(arguments, unused)

    if active is None:
        debug("no argument occupies this slot (option name or unmatched slot); no dynamic candidates")
        return []
    if active.parameter.completer is None:
        debug(f"active argument {active.name!r} has no completer; static completion handles it")
        return []
    debug(
        f"active argument={active.name!r} completer={getattr(active.parameter.completer, '__name__', active.parameter.completer)!r}"
    )

    # Only now (a completer is definitely going to run) pay for building the
    # context: attach what the user already typed so the completer can inspect
    # sibling argument values.
    _attach_prior_tokens(arguments, list(unused))
    context = CompletionContext(
        incomplete=incomplete,
        argument=active,
        arguments=arguments,
        tokens=tuple(unused),
    )

    completions = active.get_completions(context)
    debug(f"completer returned {len(completions or [])} candidate(s): {completions!r}")
    if not completions:
        return []
    # The completer already received ``context.incomplete`` and owns its own
    # filtering (mirroring Click/Cobra); we do not re-filter here.
    return [Completion(value, help) for value, help in completions]
