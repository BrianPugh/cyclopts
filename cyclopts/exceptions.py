import inspect
from typing import Callable, List, Optional

from attrs import define, field


def _get_function_info(func):
    return inspect.getsourcefile(func), inspect.getsourcelines(func)[1]


@define(kw_only=True)
class CycloptsError(Exception):
    """Root exception."""

    msg: Optional[str] = None
    tokens: List[str] = field(factory=list)

    target: Optional[Callable] = None

    def __str__(self):
        if self.msg is not None:
            return self.msg

        strings = []
        if self.target:
            file, lineno = _get_function_info(self.target)
            strings.append(
                "Error parsing tokens for function\n"
                f"    {self.target.__name__}{inspect.signature(self.target)}\n"
                f"Defined in File {file}, line {lineno}"
            )
        return "\n" + "\n".join(strings)


class UnreachableError(CycloptsError):
    """Code-block should be unreachable."""


class CoercionError(CycloptsError):
    pass


class UnsupportedPositionalError(CycloptsError):
    pass


class CommandCollisionError(CycloptsError):
    pass


@define(kw_only=True)
class UnusedCliTokensError(CycloptsError):
    unused_tokens: List[str]

    def __str__(self):
        s = super().__str__()
        return s + f"\nUnused Tokens: {self.unused_tokens}"


class MissingArgumentError(CycloptsError):
    pass


class MultipleParameterAnnotationError(CycloptsError):
    pass
