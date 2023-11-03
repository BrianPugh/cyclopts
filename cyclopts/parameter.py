import inspect
import typing
from typing import Callable, Optional, Tuple, Union

from attrs import frozen
from typing_extensions import Annotated

from cyclopts.exceptions import MultipleParameterAnnotationError, RepeatKeywordError

# from types import NoneType is available >=3.10
NoneType = type(None)


@frozen
class Parameter:
    # User Options
    name: str = ""
    coercion: Optional[Callable] = None
    show_default = True
    help: str = ""


def get_hint_parameter(parameter: inspect.Parameter) -> Tuple[type, Parameter]:
    """Get the type hint and Cyclopts ``Parameter`` from a possibly annotated inspect Parameter.

    Unions will be resolved to the first non-NoneType
    """
    hint = parameter.annotation

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

    # Resolve Union types to a single type
    while typing.get_origin(hint) is Union:
        # Note: origin of ``Optional`` is also ``Union``
        if typing.get_origin(hint) is Union:
            for hint_arg in typing.get_args(hint):
                if hint_arg is NoneType:
                    continue
                hint = hint_arg
                break

    return hint, cyclopts_parameter
