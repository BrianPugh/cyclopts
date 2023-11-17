import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from attrs import define, field
from rich import box
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from cyclopts.core import App


def _get_function_info(func):
    return inspect.getsourcefile(func), inspect.getsourcelines(func)[1]


@define(kw_only=True)
class CycloptsError(Exception):
    """Root exception."""

    msg: Optional[str] = None

    verbose: bool = True

    root_input_tokens: Optional[List[str]] = None
    unused_tokens: Optional[List[str]] = None
    target: Optional[Callable] = None
    cli2parameter: Optional[Dict[str, Tuple[inspect.Parameter, Any]]] = None
    parameter2cli: Optional[Dict[inspect.Parameter, List[str]]] = None

    # Tokens that led up to the actual command being executed.
    command_chain: Optional[List[str]] = None

    app: Optional["App"] = None

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


class UnreachableError(CycloptsError):
    """Code-block should be unreachable."""


class CoercionError(CycloptsError):
    pass


class CommandCollisionError(CycloptsError):
    pass


@define(kw_only=True)
class UnusedCliTokensError(CycloptsError):
    unused_tokens: List[str]

    def __str__(self):
        s = super().__str__()
        return s + f"Unused Tokens: {self.unused_tokens}"


@define(kw_only=True)
class MissingArgumentError(CycloptsError):
    parameter: inspect.Parameter
    tokens_so_far: List[str]

    def __str__(self):
        from cyclopts.coercion import token_count

        # TODO: need to go from parameter -> cli_name

        count = token_count(self.parameter.annotation)
        if count == 0:
            required_string = "flag required"
        elif count == 1:
            required_string = "requires an argument"
        else:
            required_string = f"requires {count} arguments"

        assert self.parameter2cli is not None
        parameter_cli_name = ",".join(self.parameter2cli[self.parameter])

        strings = []
        if self.command_chain:
            strings.append(
                f'Command "{" ".join(self.command_chain)}" parameter "{parameter_cli_name}" {required_string}.'
            )
        else:
            strings.append(f'Parameter "{parameter_cli_name}" {required_string}.')

        if self.verbose:
            strings.append(f" Parsed: {self.tokens_so_far}.")

        return " ".join(strings)


class MultipleParameterAnnotationError(CycloptsError):
    pass


def format_cyclopts_error(e: CycloptsError):
    panel = Panel(
        Text(str(e), "default"),
        title="Error",
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        style="red",
    )
    return panel
