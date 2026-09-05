"""Runtime engine for dynamic (Python-invoked) shell completion.

The static ``bash``/``zsh``/``fish`` generators bake command, option, and static
choice names into a script at install time. When an argument has a
:attr:`.Parameter.completer`, that script also calls back at TAB time through the
reserved ``__complete`` command, which routes here to run the completer and emit
its candidate values.
"""

import os
import sys
from collections.abc import Callable, Iterable
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple

from cyclopts.bind import _parse_configs, _parse_env, _parse_kw_and_flags, _parse_pos
from cyclopts.exceptions import CycloptsError, MissingArgumentError
from cyclopts.utils import UNSET, frozen, is_option_like


def completion_debug_enabled() -> bool:
    """Whether the ``CYCLOPTS_COMPLETION_DEBUG`` diagnostic is switched on."""
    return bool(os.environ.get("CYCLOPTS_COMPLETION_DEBUG"))


def _exc(e: BaseException) -> str:
    """Concise one-line exception summary (Cyclopts error reprs are enormous)."""
    text = str(e).strip().splitlines()
    summary = text[0] if text else ""
    return f"{type(e).__name__}: {summary}"[:200] if summary else type(e).__name__


def debug(message: str) -> None:
    """Print a ``[cyclopts:completion]`` diagnostic to stderr when ``CYCLOPTS_COMPLETION_DEBUG`` is set.

    Completion otherwise swallows all output, so this is the escape hatch for
    running ``<prog> __complete <words...>`` by hand.
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
    """A best-effort view of another argument's typed-so-far value.

    Handed out by ``context[name]`` so a completer can branch on sibling
    arguments already on the command line.
    """

    argument: "Argument"

    @property
    def provided(self) -> bool:
        """Whether the user has supplied a value for this argument yet."""
        return self.argument.has_tokens

    @property
    def raw(self) -> str | None:
        """The raw string the user typed, or :obj:`None` if not provided (first token only; see :attr:`raw_tokens`)."""
        tokens = self.argument.tokens
        return tokens[0].value if tokens else None

    @property
    def raw_tokens(self) -> tuple[str, ...]:
        """Every raw string token supplied for this argument, in order."""
        return tuple(token.value for token in self.argument.tokens)

    @property
    def value(self) -> Any:
        """Best-effort coerced value, or :obj:`~.UNSET` if unavailable.

        Runs the argument's normal conversion over the tokens typed so far (may
        invoke a user :attr:`.Parameter.converter` on partial input); returns
        :obj:`~.UNSET` instead of raising on failure, and does not validate.
        Falls back to the parameter's default when no tokens were given.
        """
        if not self.argument.has_tokens:
            default = self.argument.field_info.default
            return UNSET if default is self.argument.field_info.empty else default
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

    @property
    def parameter(self):
        """The :class:`.Parameter` of the argument currently being completed."""
        return self.argument.parameter

    def _match(self, name: str) -> "Argument":
        # ``_match_explicit`` matches ``name`` against declared options while
        # skipping the ``**kwargs`` catch-all, so a bare name like ``"region"``
        # keeps falling through to the explicit field/option-name scan below.
        argument = self.arguments._match_explicit(name)
        if argument is not None:
            return argument
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

    A bare :class:`str` or :class:`tuple` is one candidate — ``("us-west",
    "Oregon")`` is a single described record, not two values. Any other iterable
    is a collection of such items. An empty tuple (bare or as an item) means "no
    candidate" and is dropped, like ``None`` or ``[]``.
    """
    if result is None:
        return []
    items: Iterable[str | tuple] = [result] if isinstance(result, (str, tuple)) else result
    normalized = [_normalize_item(item) for item in items]
    return [pair for pair in normalized if pair is not None]


def _normalize_item(item: "str | tuple") -> "tuple[str, str] | None":
    if isinstance(item, str):
        return (item, "")
    if isinstance(item, tuple):
        if not item:
            return None
        value, *rest = item
        return (str(value), str(rest[0]) if rest else "")
    # Not a str or (value, description) tuple (e.g. a completer yielding ints):
    # coerce to its string form rather than raising mid-completion.
    return (str(item), "")


#: Stands in for the word being completed while the real parser distributes
#: tokens. Contains NUL so it can never collide with a real shell word, and is
#: never option-like, so the parser routes it exactly like the value the user
#: is about to type.
_ACTIVE_SENTINEL = "\x00cyclopts-active\x00"


def _merge_wordbreaks(words: list[str]) -> list[str]:
    """Rejoin bash ``COMP_WORDBREAKS`` splits (``--user=al`` arrives as ``['--user', '=', 'al']``) into single tokens.

    Matches what zsh and fish send. ``=`` is rejoined only for option forms
    (``--opt=value``); ``:`` always, since a lone break word only comes from
    splitting a contiguous string.
    """
    merged: list[str] = []
    i = 0
    n = len(words)
    while i < n:
        word = words[i]
        eq_join = word == "=" and merged and merged[-1].startswith("-") and "=" not in merged[-1]
        colon_join = word == ":" and merged
        if eq_join or colon_join:
            # Glue the break char onto the previous word and absorb the following
            # word too (the char sat between the two halves of one token).
            merged[-1] += word
            if i + 1 < n:
                merged[-1] += words[i + 1]
                i += 2
            else:
                i += 1
            continue
        merged.append(word)
        i += 1
    return merged


def _resolve_active_argument(
    arguments: "ArgumentCollection",
    tokens: list[str],
    end_of_options_delimiter: str,
) -> "Argument | None":
    """Run the real parser over ``tokens`` and return the argument owning the cursor.

    ``tokens`` end with a sentinel standing in for the word being completed.
    Reusing the real :mod:`.bind` parser (minus ``_convert``/validation) makes
    option-value consumption, ``=`` forms, ``--``, and variadics behave exactly
    like a real invocation, and leaves prior tokens on the sibling arguments.
    Whichever argument the sentinel lands on is active; it is stripped afterward.
    """
    active: Argument | None = None
    try:
        unused, _, contiguous, _ = _parse_kw_and_flags(
            arguments, tokens, end_of_options_delimiter=end_of_options_delimiter
        )
        _parse_pos(
            arguments,
            unused,
            end_of_options_delimiter=end_of_options_delimiter,
            contiguous_positional_count=contiguous,
        )
    except MissingArgumentError as e:
        # A multi-token argument (e.g. ``tuple[int, int]``) raised before the
        # sentinel could complete its token set: the cursor is filling its next
        # element. Best effort — the error can also stem from malformed *prior*
        # input, in which case the real parse would reject the line anyway.
        active = e.argument
        debug(f"active argument resolved from incomplete multi-token argument: {_exc(e)}")
    except Exception as e:
        debug(f"parsing prior tokens {tokens[:-1]!r} failed: {_exc(e)}")
        return None

    for argument in arguments:
        if any(token.value == _ACTIVE_SENTINEL for token in argument.tokens):
            active = argument
            argument.tokens = [token for token in argument.tokens if token.value != _ACTIVE_SENTINEL]
    return active


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
        Candidates from the active slot's :attr:`.Parameter.completer`. Empty
        when it has no completer (the generated script handles static choices,
        command names, and option names).
    """
    if not words:
        words = [""]
    words = _merge_wordbreaks(words)
    prior, incomplete = words[:-1], words[-1]
    debug(f"words={words!r} prior={prior!r} incomplete={incomplete!r}")

    # The sentinel stands in for the word being completed. For an eq-form token
    # (``--user=al``) the sentinel replaces only the value part so the real
    # parser routes it to ``--user``; a plain option-name-in-progress has no
    # value slot to complete (that's the static script's job).
    parse_token = _ACTIVE_SENTINEL
    if is_option_like(incomplete):
        if "=" not in incomplete:
            debug("completing an option name; static completion handles it")
            return []
        option, _, incomplete = incomplete.partition("=")
        parse_token = f"{option}={_ACTIVE_SENTINEL}"

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

    # The app_stack context applies stack-resolved configuration — e.g. an
    # ``App(default_parameter=Parameter(completer=...))`` — exactly like the
    # real parse (core.py) and the static extractor (_base.py) do.
    with app.app_stack(execution_path):
        try:
            arguments = command_app.assemble_argument_collection(parse_docstring=False)
            # Merge keyword parameters contributed by meta launchers on the path
            # (mirroring the static extractor): a meta option like ``--env`` shares
            # the command line with the resolved command (``myapp deploy --env
            # prod``), so its value slot must resolve here too. Positionals stay
            # command-only — launcher positionals are consumed before the command
            # name and must not shift the command's own slots.
            from cyclopts.core import _iter_resolution_argument_collections

            for subapp, collection in _iter_resolution_argument_collections(execution_path, parse_docstring=False):
                if subapp is command_app:
                    continue
                arguments.extend(argument for argument in collection if not argument.field_info.is_positional)
        except Exception as e:
            debug(f"assembling arguments failed: {_exc(e)}")
            return []
        end_of_options_delimiter = app.app_stack.resolve("end_of_options_delimiter", fallback="--")

        active = _resolve_active_argument(arguments, [*unused, parse_token], end_of_options_delimiter)

        if active is None:
            debug("no argument occupies this slot (option name or unmatched slot); no dynamic candidates")
            return []
        if active.parameter.completer is None:
            debug(f"active argument {active.name!r} has no completer; static completion handles it")
            return []
        debug(
            f"active argument={active.name!r} completer={getattr(active.parameter.completer, '__name__', active.parameter.completer)!r}"
        )

        # The sibling arguments already carry the CLI tokens from the same parse
        # that resolved the active argument. Layer in env-var and config-sourced
        # values (like the real binding pass) so a dependent completer sees the
        # same sibling values the command itself would receive. Best effort — a
        # broken config source must not kill completion.
        try:
            _parse_env(arguments)
            configs = command_app.app_stack.resolve("_config") or ()
            _parse_configs(arguments, tuple(partial(x, command_app, command_chain) for x in configs))
        except Exception as e:
            debug(f"applying env/config sources failed (sibling values may be partial): {_exc(e)}")

        context = CompletionContext(
            incomplete=incomplete,
            argument=active,
            arguments=arguments,
        )

        completions = active.get_completions(context)
    debug(f"completer returned {len(completions or [])} candidate(s): {completions!r}")
    if not completions:
        return []
    # The completer already received ``context.incomplete`` and owns its own
    # filtering (mirroring Click/Cobra); we do not re-filter here.
    return [Completion(value, help) for value, help in completions]
