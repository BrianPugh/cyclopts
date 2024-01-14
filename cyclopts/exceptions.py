import difflib
import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type

from attrs import define
from rich import box
from rich.panel import Panel
from rich.text import Text

from cyclopts.utils import ParameterDict

if TYPE_CHECKING:
    from cyclopts.core import App


__all__ = [
    "CoercionError",
    "CommandCollisionError",
    "CycloptsError",
    "DocstringError",
    "InvalidCommandError",
    "MissingArgumentError",
    "UnusedCliTokensError",
    "ValidationError",
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

    root_input_tokens: Optional[List[str]] = None
    """
    The parsed CLI tokens that were initially fed into the :class:`App`.
    """

    unused_tokens: Optional[List[str]] = None
    """
    Leftover tokens after parsing is complete.
    """

    target: Optional[Callable] = None
    """
    The python function associated with the command being parsed.
    """

    cli2parameter: Optional[Dict[str, Tuple[inspect.Parameter, Any]]] = None
    """
    Dictionary mapping CLI strings to python parameters.
    """

    parameter2cli: Optional[ParameterDict] = None
    """
    Dictionary mapping function parameters to possible CLI tokens.
    """

    command_chain: Optional[List[str]] = None
    """
    List of command that lead to ``target``.
    """

    app: Optional["App"] = None
    """
    The Cyclopts application itself.
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
                strings.append(f"    {self.target.__name__}{inspect.signature(self.target)}")
            if self.root_input_tokens is not None:
                strings.append(f"Root Input Tokens: {self.root_input_tokens}")
        else:
            pass

        if strings:
            return "\n".join(strings) + "\n"
        else:
            return ""

    def _find_and_replace(self, s: str) -> str:
        """Replaces all instances of "--python-variable-name" with "--cli-variable-name"."""
        if self.parameter2cli is None:
            return s
        for p, names in self.parameter2cli.items():
            target = f"--{p.name}"
            replacement = names[0]
            s = s.replace(target, replacement)
        return s


@define(kw_only=True)
class ValidationError(CycloptsError):
    """Validator function raised an exception."""

    value: str
    """Parenting Assertion/Value/Type Error message."""

    parameter: Optional[inspect.Parameter] = None
    """Parameter who's ``validator`` function failed."""

    def __str__(self):
        if self.parameter is None:
            self.value = self._find_and_replace(self.value)
            return super().__str__() + self.value
        else:
            assert self.parameter2cli is not None
            parameter_cli_name = ",".join(self.parameter2cli[self.parameter])
            return super().__str__() + f"Invalid value for {parameter_cli_name}. {self.value}"


@define(kw_only=True)
class CoercionError(CycloptsError):
    """There was an error performing automatic type coercion."""

    input_value: str = ""
    """
    String input token that couldn't be coerced.
    """

    target_type: Optional[Type] = None
    """
    Intended type to coerce into.
    """

    parameter: Optional[inspect.Parameter] = None

    def __str__(self):
        if self.parameter:
            assert self.parameter2cli is not None
            parameter_cli_name = ",".join(self.parameter2cli[self.parameter])

        if self.msg is not None:
            if self.parameter:
                return f"{parameter_cli_name}: " + self.msg  # pyright: ignore[reportUnboundVariable]
            else:
                return self.msg

        response = f'Error converting value "{self.input_value}"'

        if self.target_type is not None:
            target_type = str(self.target_type).lstrip("typing.")  # lessens the verbosity a little bit.
            response += f" to {target_type}"

        if self.parameter:
            response += f' for "{parameter_cli_name}"'  # pyright: ignore[reportUnboundVariable]

        return super().__str__() + response + "."


class InvalidCommandError(CycloptsError):
    """CLI token combination did not yield a valid command."""

    def __str__(self):
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
    """A parameter had insufficient tokens to be populated."""

    parameter: inspect.Parameter
    """
    The parameter that failed to parse.
    """

    tokens_so_far: List[str]
    """
    The tokens that were parsed so far for this Parameter.
    """

    def __str__(self):
        from cyclopts._convert import token_count

        count, _ = token_count(self.parameter)
        if count == 0:
            required_string = "flag required"
            only_got_string = ""
        elif count == 1:
            required_string = "requires an argument"
            only_got_string = ""
        else:
            required_string = f"requires {count} arguments"
            only_got_string = f" Only got {len(self.tokens_so_far)}."

        assert self.parameter2cli is not None
        parameter_cli_name = ",".join(self.parameter2cli[self.parameter])

        strings = []
        if self.command_chain:
            strings.append(
                f'Command "{" ".join(self.command_chain)}" parameter "{parameter_cli_name}" {required_string}.{only_got_string}'
            )
        else:
            strings.append(f'Parameter "{parameter_cli_name}" {required_string}.{only_got_string}')

        if self.verbose:
            strings.append(f" Parsed: {self.tokens_so_far}.")

        return super().__str__() + " ".join(strings)


@define(kw_only=True)
class RepeatArgumentError(CycloptsError):
    """The same parameter has erroneously been specified multiple times."""

    parameter: inspect.Parameter
    """
    The repeated parameter.
    """

    def __str__(self):
        assert self.parameter2cli is not None
        parameter_cli_name = ",".join(self.parameter2cli[self.parameter])
        return super().__str__() + f"Parameter {parameter_cli_name} specified multiple times."


def format_cyclopts_error(e: Any):
    panel = Panel(
        Text(str(e), "default"),
        title="Error",
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        style="red",
    )
    return panel
