import inspect
from typing import Callable, List, Optional

from attrs import define, field
from rich import box
from rich.panel import Panel
from rich.text import Text


def _get_function_info(func):
    return inspect.getsourcefile(func), inspect.getsourcelines(func)[1]


@define(kw_only=True)
class CycloptsError(Exception):
    """Root exception."""

    msg: Optional[str] = None

    verbose: bool = True

    input_tokens: Optional[List[str]] = None
    unused_tokens: Optional[List[str]] = None
    target: Optional[Callable] = None

    def __str__(self):
        if self.msg is not None:
            return self.msg

        strings = []
        if self.verbose:
            if self.target:
                file, lineno = _get_function_info(self.target)
                strings.append(
                    "Error parsing tokens for function\n"
                    f"    {self.target.__name__}{inspect.signature(self.target)}\n"
                    f'Defined in file "{file}", line {lineno}'
                )
            if self.input_tokens is not None:
                strings.append(f"Input Tokens: {self.input_tokens}")
        else:
            raise NotImplementedError

        return "\n".join(strings) + "\n"


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
        s = super().__str__()
        return s + f'Parameter "{self.parameter.name}" requires {count} arguments. Parsed: {self.tokens_so_far}'


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
