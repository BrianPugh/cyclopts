import inspect
import json
from collections.abc import Callable, Iterator, Sequence
from enum import Enum
from itertools import chain
from typing import TYPE_CHECKING, Any, Literal, Optional, get_args, get_origin

from attrs import define, field

import cyclopts.utils
from cyclopts.annotations import get_hint_name
from cyclopts.command_spec import CommandSpec
from cyclopts.group import Group
from cyclopts.token import Token
from cyclopts.utils import is_option_like, json_decode_error_verbosifier

if TYPE_CHECKING:
    from rich.console import Console
    from rich.text import Text

    from cyclopts.argument import Argument, ArgumentCollection
    from cyclopts.core import App


# Rich style palette for error messages. Kept conservative; this is error
# output, not a TUI. Empty string in a segment means "no styling".
_STYLE_VALUE = "bold red"  # offending user-supplied value
_STYLE_NAME = "bold"  # parameter / command name
_STYLE_CHOICE = "cyan"  # valid choices in "Choose from:" lists
_STYLE_SUGGESTION = "bold green"  # "Did you mean ..." suggestion
_STYLE_DIM = "dim"  # source suffixes like " from <CONFIG>"


__all__ = [
    "CoercionError",
    "CommandCollisionError",
    "CycloptsError",
    "DocstringError",
    "UnknownCommandError",
    "MissingArgumentError",
    "ConsumeMultipleError",
    "MixedArgumentError",
    "RepeatArgumentError",
    "RequiresEqualsError",
    "UnknownOptionError",
    "UnusedCliTokensError",
    "ValidationError",
    "CombinedShortOptionError",
]


def _get_function_info(func):
    return inspect.getsourcefile(func), inspect.getsourcelines(func)[1]


class CommandCollisionError(Exception):
    """A command with the same name has already been registered to the app."""

    # This doesn't derive from CycloptsError since this is a developer error
    # rather than a runtime error.


class DocstringError(Exception):
    """The docstring either has a syntax error, or inconsistency with the function signature."""


@define  # (kw_only=True)
class CycloptsError(Exception):
    """Root exception for runtime errors.

    As CycloptsErrors bubble up the Cyclopts call-stack, more information is added to it.
    """

    msg: str | None = None
    """
    If set, override automatic message generation.
    """

    verbose: bool = True
    """
    More verbose error messages; aimed towards developers debugging their Cyclopts app.
    Defaults to ``False``.
    """

    root_input_tokens: list[str] | None = None
    """
    The parsed CLI tokens that were initially fed into the :class:`App`.
    """

    unused_tokens: list[str] | None = None
    """
    Leftover tokens after parsing is complete.
    """

    target: Callable | None = None
    """
    The python function associated with the command being parsed.
    """

    argument: Optional["Argument"] = None
    """
    :class:`Argument` that was matched.
    """

    command_chain: Sequence[str] | None = None
    """
    List of command that lead to ``target``.
    """

    app: Optional["App"] = None
    """
    The Cyclopts application itself.
    """

    console: Optional["Console"] = field(default=None, kw_only=True)
    """:class:`~rich.console.Console` to display runtime errors."""

    def __str__(self):
        if self.msg is not None:
            return self.msg

        strings = []
        if self.verbose:
            strings.append(type(self).__name__)
            if self.target:
                file, lineno = _get_function_info(self.target)
                strings.append(f'Function defined in file "{file}", line {lineno}:')
                strings.append(f"    {self.target.__name__}{inspect.signature(self.target)}")
            if self.root_input_tokens is not None:
                strings.append(f"Root Input Tokens: {self.root_input_tokens}")
        else:
            pass

        if strings:
            return "\n".join(strings) + "\n"
        else:
            return ""


@define(kw_only=True)
class CombinedShortOptionError(CycloptsError):
    """Cannot combine short, token-consuming options with short flags."""


@define(kw_only=True)
class ValidationError(CycloptsError):
    """Validator function raised an exception."""

    exception_message: str = ""
    """Parenting Assertion/Value/Type Error message."""

    group: Group | None = None
    """If a group validator caused the exception."""

    value: Any = cyclopts.utils.UNSET
    """Converted value that failed validation."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        body: list[tuple[str, str]] = []

        if self.argument:
            value = self.argument.value if self.value is cyclopts.utils.UNSET else self.value
            try:
                token = self.argument.tokens[0]
            except IndexError:
                pass
            else:
                provided_by = "" if not token.source or token.source == "cli" else f" provided by {token.source}"
                name = token.keyword if token.keyword else self.argument.name.lstrip("-").upper()
                body.append(('Invalid value "', ""))
                body.append((f"{value}", _STYLE_VALUE))
                body.append(('" for ', ""))
                body.append((name, _STYLE_NAME))
                if provided_by:
                    body.append((provided_by, _STYLE_DIM))
                body.append((".", ""))
        elif self.group:
            if self.group.name:
                body.append(("Invalid values for group ", ""))
                body.append((self.group.name, _STYLE_NAME))
                body.append((".", ""))
        elif self.command_chain:
            body.append(('Invalid values for command "', ""))
            body.append((self.command_chain[-1], _STYLE_NAME))
            body.append(('".', ""))
        else:
            raise NotImplementedError

        prefix = super().__str__()
        if prefix:
            yield prefix, ""
        yield from body

        cyclopts_message_nonempty = bool(prefix) or bool(body)
        if self.exception_message:
            if cyclopts_message_nonempty:
                yield " ", ""
            yield self.exception_message, ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class UnknownOptionError(CycloptsError):
    """Unknown/unregistered option provided by the cli.

    A nearest-neighbor parameter suggestion may be printed.
    """

    token: Token
    """Token without a matching parameter."""

    argument_collection: "ArgumentCollection"
    """Argument collection of plausible options."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        value = self.token.keyword or self.token.value

        prefix = super().__str__()
        if prefix:
            yield prefix, ""

        yield 'Unknown option: "', ""
        yield value, _STYLE_VALUE
        if self.token.source == "cli":
            yield '".', ""
        else:
            yield '"', ""
            yield f" from {self.token.source}", _STYLE_DIM
            yield ".", ""

        if keyword := self.token.keyword or self.token.value:
            import difflib

            candidates = list(chain.from_iterable(x.names for x in self.argument_collection if x.parse))

            close_matches = difflib.get_close_matches(keyword, candidates, n=1, cutoff=0.6)
            if close_matches:
                yield " Did you mean ", ""
                yield close_matches[0], _STYLE_SUGGESTION
                yield "?", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class CoercionError(CycloptsError):
    """There was an error performing automatic type coercion."""

    token: Optional["Token"] = None
    """
    Input token that couldn't be coerced.
    """

    target_type: type | None = None
    """
    Intended type to coerce into.
    """

    def _segments(self) -> Iterator[tuple[str, str]]:
        """Yield (text, style) pairs that compose the error message.

        Empty string in the style position means "no styling". Drives both
        ``__str__`` (which joins the text) and ``__rich__`` (which applies
        the styles).
        """
        # Branch 1: explicit msg override. Yield exactly what str() would
        # produce as a single unstyled segment -- user content stays plain.
        if self.msg is not None:
            if not self.token or self.token.keyword is None:
                yield self.msg, ""
            else:
                yield f"Invalid value for {self.token.keyword}: {self.msg}", ""
            return

        # Branch 2: JSONDecodeError verbosifier path. Plain, like branch 1.
        if isinstance(self.__cause__, json.JSONDecodeError):
            verbosified = json_decode_error_verbosifier(self.__cause__)  # pyright: ignore[reportArgumentType]
            if not self.token or self.token.keyword is None:
                yield verbosified, ""
            else:
                yield f"Invalid value for {self.token.keyword}: {verbosified}", ""
            return

        assert self.argument is not None
        assert self.target_type is not None

        prefix = super().__str__()
        if prefix:
            yield prefix, ""

        choice_strs: list[str] | None = None
        plain_choices: list[str] | None = None
        if get_origin(self.target_type) is Literal:
            args = get_args(self.target_type)
            choice_strs = [f'"{x}"' if isinstance(x, str) else repr(x) for x in args]
            plain_choices = [x for x in args if isinstance(x, str)]
        elif isinstance(self.target_type, type) and issubclass(self.target_type, Enum):
            nt = self.argument.parameter.name_transform
            members = [nt(x) for x in self.target_type.__members__]
            choice_strs = [f'"{x}"' for x in members]
            plain_choices = members

        # Branch 3: Literal/Enum with a token -- "Choose from" + suggestion.
        if choice_strs is not None and self.token is not None:
            name = self.token.keyword if self.token.keyword else self.argument.name.lstrip("-").upper()
            yield 'Invalid value "', ""
            yield self.token.value, _STYLE_VALUE
            yield '" for ', ""
            yield name, _STYLE_NAME
            if self.token.source not in ("", "cli"):
                yield f" from {self.token.source}", _STYLE_DIM
            yield ". Choose from: ", ""
            for i, choice in enumerate(choice_strs):
                if i:
                    yield ", ", ""
                yield choice, _STYLE_CHOICE
            yield ".", ""

            import difflib

            close = difflib.get_close_matches(self.token.value, plain_choices or [], n=1, cutoff=0.6)
            if close:
                yield ' Did you mean "', ""
                yield close[0], _STYLE_SUGGESTION
                yield '"?', ""
            return

        # Branch 4: fallback -- "unable to convert ... into <type>".
        target_type_name = (
            get_hint_name(self.target_type) if choice_strs is None else f"one of {{{', '.join(choice_strs)}}}"
        )

        if not self.token:
            yield "Invalid value for ", ""
            yield self.argument.name, _STYLE_NAME
            yield f": unable to convert value to {target_type_name}.", ""
            return

        if self.token.keyword is None:
            display_name = self.argument.name.lstrip("-").upper()
        else:
            display_name = self.token.keyword

        yield "Invalid value for ", ""
        yield display_name, _STYLE_NAME
        if self.token.source not in ("", "cli"):
            yield f" from {self.token.source}", _STYLE_DIM
        yield ': unable to convert "', ""
        yield self.token.value, _STYLE_VALUE
        yield f'" into {target_type_name}.', ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


class UnknownCommandError(CycloptsError):
    """CLI token combination did not yield a valid command."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.unused_tokens
        token = self.unused_tokens[0]

        prefix = super().__str__()
        if prefix:
            yield prefix, ""

        yield 'Unknown command "', ""
        yield token, _STYLE_VALUE
        yield '".', ""

        if not (self.app and self.app._commands):
            return

        import difflib

        visible_commands: list[str] = []
        for name, app_or_spec in self.app._commands.items():
            if name in self.app._help_flags or name in self.app._version_flags:
                continue

            subapp = app_or_spec.resolve(self.app) if isinstance(app_or_spec, CommandSpec) else app_or_spec

            if not isinstance(subapp, type(self.app)):
                continue

            if subapp.show:
                visible_commands.append(name)

        close_matches = difflib.get_close_matches(token, visible_commands, n=1, cutoff=0.6)
        if close_matches:
            yield ' Did you mean "', ""
            yield close_matches[0], _STYLE_SUGGESTION
            yield '"?', ""

        # Heuristic: list the visible commands to help users who forgot the command name.
        max_commands = 8
        available_commands = [name for name in visible_commands if not name.startswith("-")]
        if not available_commands:
            return

        yield " Available commands: ", ""
        if len(available_commands) > max_commands:
            shown = available_commands[:max_commands]
            for i, name in enumerate(shown):
                if i:
                    yield ", ", ""
                yield name, _STYLE_CHOICE
            yield ", ...", ""
        else:
            for i, name in enumerate(available_commands):
                if i:
                    yield ", ", ""
                yield name, _STYLE_CHOICE
            yield ".", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class UnusedCliTokensError(CycloptsError):
    """Not all CLI tokens were used as expected."""

    def __str__(self):
        assert self.unused_tokens is not None
        return super().__str__() + f"Unused Tokens: {self.unused_tokens}."


@define(kw_only=True)
class MissingArgumentError(CycloptsError):
    """A required argument was not provided."""

    tokens_so_far: list[str] = field(factory=list)
    """If the matched parameter requires multiple tokens, these are the ones we have parsed so far."""

    keyword: str | None = None
    """The keyword that was used when the error was raised (e.g., '-o' instead of '--option')."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.argument is not None
        count, _ = self.argument.token_count()
        if count == 0:
            required_string = "flag required"
            only_got_string = ""
        elif count == 1:
            required_string = "requires an argument"
            only_got_string = ""
        else:
            required_string = f"requires {count} positional arguments"
            received_count = len(self.tokens_so_far) % count
            only_got_string = f" Only got {received_count}." if received_count else ""

        close_match: str | None = None
        if self.unused_tokens and self.argument.field_info.is_keyword:
            import difflib

            candidates = [x for x in self.unused_tokens if is_option_like(x)]
            matches = difflib.get_close_matches(self.argument.name, candidates, n=1, cutoff=0.6)
            if matches and matches[0] not in self.argument.names:
                close_match = matches[0]

        param_name = self.argument.name
        if self.keyword is not None:
            param_name = self.keyword
        elif self.argument.tokens:
            for token in reversed(self.argument.tokens):
                if token.keyword is not None:
                    param_name = token.keyword
                    break

        prefix = super().__str__()
        if prefix:
            yield prefix, ""

        if self.command_chain:
            yield 'Command "', ""
            yield " ".join(self.command_chain), _STYLE_NAME
            yield '" parameter ', ""
        else:
            yield "Parameter ", ""
        yield param_name, _STYLE_NAME
        yield f" {required_string}.{only_got_string}", ""

        if close_match is not None:
            yield " Did you mean ", ""
            yield self.argument.name, _STYLE_SUGGESTION
            yield " instead of ", ""
            yield close_match, _STYLE_VALUE
            yield "?", ""

        if self.verbose:
            yield f"  Parsed: {self.tokens_so_far}.", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class ConsumeMultipleError(MissingArgumentError):
    """The number of values provided doesn't meet consume_multiple constraints."""

    min_required: int = 0
    max_allowed: int | None = None
    actual_count: int = 0

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.argument is not None
        param_name = self.keyword or self.argument.name

        if self.actual_count < self.min_required:
            constraint = f"requires at least {self.min_required}"
        else:
            constraint = f"accepts at most {self.max_allowed}"

        # Skip MissingArgumentError.__str__ chain; we want just the base verbose prefix.
        prefix = CycloptsError.__str__(self)
        if prefix:
            yield prefix, ""

        if self.command_chain:
            yield 'Command "', ""
            yield " ".join(self.command_chain), _STYLE_NAME
            yield '" parameter ', ""
        else:
            yield "Parameter ", ""
        yield param_name, _STYLE_NAME
        yield f" {constraint} elements. Got {self.actual_count}.", ""


@define(kw_only=True)
class RequiresEqualsError(CycloptsError):
    """A long option requires ``=`` to assign a value (e.g., ``--option=value``)."""

    keyword: str | None = None
    """The keyword that was used (e.g., '--name')."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.argument is not None
        param_name = self.keyword or self.argument.name
        prefix = super().__str__()
        if prefix:
            yield prefix, ""
        yield "Parameter ", ""
        yield param_name, _STYLE_NAME
        yield " requires a value assigned with `=`. Use ", ""
        yield param_name, _STYLE_NAME
        yield "=VALUE.", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class RepeatArgumentError(CycloptsError):
    """The same parameter has erroneously been specified multiple times."""

    token: "Token"
    """The repeated token."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        # Invariant: positional duplication is routed to UnusedCliTokensError by the binder,
        # so any token reaching this error path was matched by keyword.
        assert self.token.keyword is not None
        prefix = super().__str__()
        if prefix:
            yield prefix, ""
        yield "Parameter ", ""
        yield self.token.keyword, _STYLE_NAME
        yield " specified multiple times.", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class ArgumentOrderError(CycloptsError):
    """Cannot supply a POSITIONAL_OR_KEYWORD argument with a keyword, and then a later POSITIONAL_OR_KEYWORD argument positionally."""

    token: str
    prior_positional_or_keyword_supplied_as_keyword_arguments: list["Argument"]

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.argument is not None
        plural = len(self.prior_positional_or_keyword_supplied_as_keyword_arguments) > 1
        display_name = next((x.keyword for x in self.argument.tokens if x.keyword), self.argument.name).lstrip("-")
        prior_list = [x.tokens[0].keyword for x in self.prior_positional_or_keyword_supplied_as_keyword_arguments]
        prior_display = prior_list[0] if len(prior_list) == 1 else prior_list

        prefix = super().__str__()
        if prefix:
            yield prefix, ""
        yield 'Cannot specify token "', ""
        yield self.token, _STYLE_VALUE
        yield '" positionally for parameter ', ""
        yield display_name, _STYLE_NAME
        yield f" due to previously specified keyword{'s' if plural else ''} ", ""
        yield f"{prior_display}", _STYLE_NAME
        yield ". ", ""
        yield f"{prior_display}", _STYLE_NAME
        yield ' must either be passed positionally, or "', ""
        yield self.token, _STYLE_VALUE
        yield '" must be passed as a keyword to ', ""
        yield self.argument.name, _STYLE_NAME
        yield ".", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out


@define(kw_only=True)
class MixedArgumentError(CycloptsError):
    """Cannot supply keywords and non-keywords to the same argument."""

    def _segments(self) -> Iterator[tuple[str, str]]:
        assert self.argument is not None
        display_name = next((x.keyword for x in self.argument.tokens if x.keyword), self.argument.name)
        prefix = super().__str__()
        if prefix:
            yield prefix, ""
        yield "Cannot supply keyword & non-keyword arguments to ", ""
        yield display_name, _STYLE_NAME
        yield ".", ""

    def __str__(self):
        return "".join(text for text, _ in self._segments())

    def __rich__(self) -> "Text":
        from rich.text import Text

        out = Text()
        for text, style in self._segments():
            out.append(text, style=style or None)
        return out
