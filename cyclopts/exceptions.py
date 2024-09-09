import inspect
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Callable, Optional

from attrs import define, field

import cyclopts.utils
from cyclopts.group import Group
from cyclopts.token import Token

if TYPE_CHECKING:
    from rich.console import Console

    from cyclopts.argument import Argument
    from cyclopts.core import App


__all__ = [
    "CoercionError",
    "CommandCollisionError",
    "CycloptsError",
    "DocstringError",
    "InvalidCommandError",
    "MissingArgumentError",
    "MixedArgumentError",
    "RepeatArgumentError",
    "UnknownOptionError",
    "UnusedCliTokensError",
    "ValidationError",
    "format_cyclopts_error",
]


def _get_function_info(func):
    return inspect.getsourcefile(func), inspect.getsourcelines(func)[1]


class CommandCollisionError(Exception):
    """A command with the same name has already been registered to the app."""

    # This doesn't derive from CycloptsError since this is a developer error
    # rather than a runtime error.


class DocstringError(Exception):
    """The docstring either has a syntax error, or inconsistency with the function signature."""


@define(kw_only=True)
class CycloptsError(Exception):
    """Root exception for runtime errors.

    As CycloptsErrors bubble up the Cyclopts stack, more information is added to it.
    Finally, :func:`cyclopts.exceptions.format_cyclopts_error` formats the message nicely for the user.
    """

    msg: Optional[str] = None
    """
    If set, override automatic message generation.
    """

    verbose: bool = True
    """
    More verbose error messages; aimed towards developers debugging their Cyclopts app.
    Defaults to ``False``.
    """

    root_input_tokens: Optional[list[str]] = None
    """
    The parsed CLI tokens that were initially fed into the :class:`App`.
    """

    unused_tokens: Optional[list[str]] = None
    """
    Leftover tokens after parsing is complete.
    """

    target: Optional[Callable] = None
    """
    The python function associated with the command being parsed.
    """

    argument: Optional["Argument"] = None
    """
    :class:`Argument` that was matched.
    """

    command_chain: Optional[Iterable[str]] = None
    """
    List of command that lead to ``target``.
    """

    app: Optional["App"] = None
    """
    The Cyclopts application itself.
    """

    console: Optional["Console"] = field(default=None, kw_only=True)
    """
    Rich console to display runtime errors.
    """

    def __str__(self):
        if self.msg is not None:
            return self.msg

        strings = []
        if self.verbose:
            strings.append(type(self).__name__)
            if self.target:
                file, lineno = _get_function_info(self.target)
                strings.append(f'Function defined in file "{file}", line {lineno}:')
                strings.append(f"    {self.target.__name__}{cyclopts.utils.signature(self.target)}")
            if self.root_input_tokens is not None:
                strings.append(f"Root Input Tokens: {self.root_input_tokens}")
        else:
            pass

        if strings:
            return "\n".join(strings) + "\n"
        else:
            return ""


@define(kw_only=True)
class ValidationError(CycloptsError):
    """Validator function raised an exception."""

    value: str
    """Parenting Assertion/Value/Type Error message."""

    group: Optional[Group] = None
    """If a group validator caused the exception."""

    def __attrs_post_init__(self):
        # Make sure only 1 is set.
        assert (bool(self.argument) + bool(self.group)) == 1

    def __str__(self):
        if self.argument:
            if len(self.argument.tokens) == 1 and not self.argument.children:
                token = self.argument.tokens[0]
                if token.keyword is None:
                    # Provided positionally
                    positional_name = self.argument.name.lstrip("-").upper()
                    message = f'Invalid value "{token.value}" for {positional_name}.'
                else:
                    message = f"Invalid value {self.argument.value!r} for {token.keyword}."
            else:
                message = "TODO"
        elif self.group:
            message = f'Invalid values for group "{self.group}".'
        else:
            raise NotImplementedError
        return f"{super().__str__()}{message} {self.value}"


@define(kw_only=True)
class UnknownOptionError(CycloptsError):
    """Unknown/unregistered option provided by the cli."""

    token: str

    def __str__(self):
        return super().__str__() + f'Unknown option: "{self.token}".'


@define(kw_only=True)
class CoercionError(CycloptsError):
    """There was an error performing automatic type coercion."""

    token: Optional["Token"] = None
    """
    Input token that couldn't be coerced.
    """

    target_type: Optional[type] = None
    """
    Intended type to coerce into.
    """

    def __str__(self):
        assert self.argument is not None
        assert self.token is not None
        assert self.target_type is not None

        if self.msg is not None:
            if self.token.keyword is None:
                return self.msg
            else:
                return f"{self.token.keyword}: {self.msg}"

        msg = super().__str__()
        target_type_name = cyclopts.utils.get_hint_name(self.target_type)
        if self.token.keyword is None:
            if self.token.source == "" or self.token.source == "cli":
                msg += f'Invalid value for "{self.argument.name}": unable to convert "{self.token.value}" into {target_type_name}.'
            else:
                msg += f'Invalid value for "{self.argument.name}" from {self.token.source}: unable to convert "{self.token.value}" into {target_type_name}.'
        else:
            if self.token.source == "" or self.token.source == "cli":
                msg += f'Invalid value for "{self.token.keyword}": unable to convert value "{self.token.value}" into {target_type_name}.'
            else:
                msg += f'Invalid value for "{self.token.keyword}" from {self.token.source}: unable to convert value "{self.token.value}" into {target_type_name}.'

        return msg


class InvalidCommandError(CycloptsError):
    """CLI token combination did not yield a valid command."""

    def __str__(self):
        import difflib

        assert self.unused_tokens
        token = self.unused_tokens[0]
        response = super().__str__() + f'Unable to interpret valid command from "{token}".'

        if self.app and self.app._commands:
            close_matches = difflib.get_close_matches(token, self.app._commands, n=1, cutoff=0.8)
            if close_matches:
                response += f' Did you mean "{close_matches[0]}"?'

        return response


@define(kw_only=True)
class UnusedCliTokensError(CycloptsError):
    """Not all CLI tokens were used as expected."""

    def __str__(self):
        assert self.unused_tokens is not None
        return super().__str__() + f"Unused Tokens: {self.unused_tokens}."


@define(kw_only=True)
class MissingArgumentError(CycloptsError):
    tokens_so_far: list[str] = field(factory=list)

    def __str__(self):
        assert self.argument is not None
        strings = []
        count, _ = self.argument.token_count()
        if count == 0:
            required_string = "flag required"
            only_got_string = ""
        elif count == 1:
            required_string = "requires an argument"
            only_got_string = ""
        else:
            required_string = f"requires {count} arguments"
            received_count = len(self.tokens_so_far) % count
            only_got_string = f" Only got {received_count}." if received_count else ""

        if self.command_chain:
            strings.append(
                f'Command "{" ".join(self.command_chain)}" parameter "{self.argument.names[0]}" {required_string}.{only_got_string}'
            )
        else:
            strings.append(f'Parameter "{self.argument.names[0]}" {required_string}.{only_got_string}')

        if self.verbose:
            strings.append(f" Parsed: {self.tokens_so_far}.")

        return super().__str__() + " ".join(strings)


@define(kw_only=True)
class RepeatArgumentError(CycloptsError):
    """The same parameter has erroneously been specified multiple times."""

    token: "Token"

    def __str__(self):
        return super().__str__() + f"Parameter {self.token.keyword} specified multiple times."


@define(kw_only=True)
class ArgumentOrderError(CycloptsError):
    """Cannot supply a POSITIONAL_OR_KEYWORD argument with a keyword, and then a later POSITIONAL_OR_KEYWORD argument positionally."""

    token: str
    prior_positional_or_keyword_supplied_as_keyword_arguments: list["Argument"]

    def __str__(self):
        assert self.argument is not None
        plural = len(self.prior_positional_or_keyword_supplied_as_keyword_arguments) > 1
        display_name = next((x.keyword for x in self.argument.tokens if x.keyword), self.argument.name).lstrip("-")
        prior_display_names = [
            x.tokens[0].keyword for x in self.prior_positional_or_keyword_supplied_as_keyword_arguments
        ]
        if len(prior_display_names) == 1:
            prior_display_names = prior_display_names[0]

        return (
            super().__str__()
            + f"Cannot specify token {self.token!r} positionally for parameter {display_name!r} due to previously specified keyword{'s' if plural else ''} {prior_display_names!r}. {prior_display_names!r} must either be passed positionally, or {self.token!r} must be passed as a keyword to {self.argument.name!r}."
        )


@define(kw_only=True)
class MixedArgumentError(CycloptsError):
    """Cannot supply keywords and non-keywords to the same argument."""

    def __str__(self):
        assert self.argument is not None
        display_name = next((x.keyword for x in self.argument.tokens if x.keyword), self.argument.name)
        return super().__str__() + f'Cannot supply keyword & non-keyword arguments to "{display_name}".'


def format_cyclopts_error(e: Any):
    from rich import box
    from rich.panel import Panel
    from rich.text import Text

    panel = Panel(
        Text(str(e), "default"),
        title="Error",
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        style="red",
    )
    return panel
