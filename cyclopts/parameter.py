import inspect
import typing
from collections import abc
from typing import Callable, List, Optional, Tuple, Union

from attrs import frozen
from typing_extensions import Annotated

from cyclopts.coercion import lookup as coercion_lookup
from cyclopts.exceptions import (
    MissingTypeError,
    MultipleParameterAnnotationError,
    UnsupportedTypeHintError,
)

# from types import NoneType is available >=3.10
NoneType = type(None)


@frozen
class Parameter:
    # User Options
    name: str = ""
    coercion: Optional[Callable] = None
    show_default = True
    help: str = ""


def get_name(parameter: inspect.Parameter) -> str:
    _, param = get_hint_parameter(parameter)
    if param.name:
        name = param.name
    else:
        name = "--" + parameter.name.replace("_", "-")

    if parameter.kind is parameter.POSITIONAL_ONLY:
        # Name is only used for help-string
        return name.upper()
    else:
        return name


def get_coercion(parameter: inspect.Parameter) -> Tuple[Callable, bool]:
    is_iterable = False
    hint, param = get_hint_parameter(parameter)

    if typing.get_origin(hint) in _iterable_reduce_set:
        is_iterable = True
        hint = typing.get_args(hint)[0]

    hint = typing.get_origin(hint) or hint

    coercion = param.coercion if param.coercion else coercion_lookup.get(hint, hint)

    return coercion, is_iterable


def reduce_hint(hint: type):
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


_iterable_reduce_set = {list, abc.Iterable}


def _reduce_hint_iterable(hint: type):
    """Converts and validates type to list."""
    # Note: typing.get_origin(typing.Iterable) == collections.abc.Iterable
    if typing.get_origin(hint) not in _iterable_reduce_set:
        return hint

    list_args = typing.get_args(hint)
    if not list_args:
        raise MissingTypeError("List annotations must supply element type.")
    element_type = typing.get_origin(list_args[0]) or list_args[0]
    if element_type in _iterable_reduce_set:
        raise UnsupportedTypeHintError("Cannot have nested iterable types.")
    return List[element_type]


# Common types that an end-user might accidentally attempt to use.
_unsupported_types = {tuple, set, frozenset, range, dict, Callable}


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

    hint_origin = typing.get_origin(hint)
    if hint_origin in _unsupported_types:
        raise UnsupportedTypeHintError(f"Unsupported type: {hint_origin}")

    hint = reduce_hint(hint)

    return hint, cyclopts_parameter
