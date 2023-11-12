import inspect
import typing
from typing import Callable, Iterable, List, Optional, Tuple, Union

from attrs import field, frozen
from typing_extensions import Annotated

from cyclopts.exceptions import (
    MultipleParameterAnnotationError,
)


def _str_to_tuple_converter(input_value: Union[str, Iterable[str]]) -> Tuple[str, ...]:
    if isinstance(input_value, str):
        return (input_value,)
    return tuple(input_value)


@frozen
class Parameter:
    """User-facing parameter annotation."""

    # User Options
    name: Tuple[str, ...] = field(default=[], converter=_str_to_tuple_converter)
    coercion: Optional[Callable] = None
    show_default = True
    help: str = ""


def get_names(parameter: inspect.Parameter) -> List[str]:
    """Derive the CLI name for an ``inspect.Parameter``."""
    _, param = get_hint_parameter(parameter.annotation)
    if param.name:
        names = list(param.name)
    else:
        if parameter.kind is parameter.POSITIONAL_ONLY:
            # Name is only used for help-string
            names = [parameter.name.upper()]
        else:
            names = ["--" + parameter.name.replace("_", "-")]

    return names


def get_hint_parameter(hint) -> Tuple[type, Parameter]:
    """Get the type hint and Cyclopts ``Parameter`` from a possibly annotated inspect Parameter."""
    if typing.get_origin(hint) is Annotated:
        hint_args = typing.get_args(hint)
        hint = hint_args[0]
        cyclopts_parameters = [x for x in hint_args[1:] if isinstance(x, Parameter)]
        if len(cyclopts_parameters) > 2:
            raise MultipleParameterAnnotationError
        elif len(cyclopts_parameters) == 1:
            cyclopts_parameter = cyclopts_parameters[0]
        else:
            cyclopts_parameter = Parameter()
    else:
        cyclopts_parameter = Parameter()

    return hint, cyclopts_parameter
