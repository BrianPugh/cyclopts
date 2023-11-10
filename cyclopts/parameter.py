import inspect
import typing
from typing import Callable, Iterable, List, Optional, Tuple, Union

from attrs import field, frozen
from typing_extensions import Annotated

from cyclopts.exceptions import (
    MissingTypeError,
    MultipleParameterAnnotationError,
    UnsupportedTypeHintError,
)
from cyclopts.typing import is_iterable_type_hint

# from types import NoneType is available >=3.10
NoneType = type(None)


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
    _, param = get_hint_parameter(parameter)
    if param.name:
        names = list(param.name)
    else:
        if parameter.kind is parameter.POSITIONAL_ONLY:
            # Name is only used for help-string
            names = [parameter.name.upper()]
        else:
            names = ["--" + parameter.name.replace("_", "-")]

    return names


def _reduce_hint(hint: type):
    """Unified type-hint reduction."""
    while True:
        pre_reduced_hint = hint
        hint = _reduce_hint_union(hint)
        hint = _reduce_hint_iterable(hint)
        if pre_reduced_hint == hint:
            break
    return hint


def _reduce_hint_union(hint: type):
    """Resolve Optional/Union types to a single type."""
    while typing.get_origin(hint) is Union:
        # Note: origin of ``Optional`` is also ``Union``
        if typing.get_origin(hint) is Union:
            for hint_arg in typing.get_args(hint):
                if hint_arg is NoneType:
                    continue
                hint = hint_arg
                break
    return hint


def _reduce_hint_iterable(hint: type):
    """Converts and validates type to list."""
    if not is_iterable_type_hint(hint):
        return hint

    list_args = typing.get_args(hint)
    if not list_args:
        raise MissingTypeError("List annotations must supply element type.")
    element_type = typing.get_origin(list_args[0]) or list_args[0]
    if is_iterable_type_hint(element_type):
        raise UnsupportedTypeHintError("Cannot have nested iterable types.")
    return List[element_type]


# Common types that an end-user might accidentally attempt to use.
_unsupported_types = {tuple, set, frozenset, range, dict, Callable}


def get_hint_parameter(parameter: inspect.Parameter) -> Tuple[type, Parameter]:
    """Get the type hint and Cyclopts ``Parameter`` from a possibly annotated inspect Parameter.

    Unions will be resolved to the first non-NoneType.
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

    hint_origin = typing.get_origin(hint)
    if hint_origin in _unsupported_types:
        raise UnsupportedTypeHintError(f"Unsupported type: {hint_origin}")

    hint = _reduce_hint(hint)

    return hint, cyclopts_parameter
