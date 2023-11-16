import inspect
import typing
from typing import Callable, Iterable, List, Optional, Tuple, Union, get_origin

from attrs import field, frozen
from typing_extensions import Annotated

from cyclopts.coercion import resolve
from cyclopts.exceptions import MultipleParameterAnnotationError, UnreachableError


def _str_to_tuple_converter(input_value: Union[str, Iterable[str]]) -> Tuple[str, ...]:
    if isinstance(input_value, str):
        return (input_value,)
    return tuple(input_value)


def _optional_str_to_tuple_converter(input_value: Union[None, str, Iterable[str]]) -> Optional[Tuple[str, ...]]:
    if input_value is None:
        return None

    return _str_to_tuple_converter(input_value)


@frozen
class Parameter:
    """User-facing parameter annotation."""

    # User Options

    # Name(s) that this parameter should be exposed to the cli as.
    # These should start with ``--`` (or ``-`` for single-character).
    name: Tuple[str, ...] = field(default=[], converter=_str_to_tuple_converter)

    # User provided converter function with signature:
    #
    #    def converter(type_, *args):
    #        pass
    #
    # Where ``type_`` is the parameter type hint, and ``args`` are all string
    # tokens that were parsed to be associated with this parameter.
    # Typically this is a single token. The returned value will be supplied to
    # the command.
    converter: Optional[Callable] = field(default=None)

    negative: Optional[Tuple[str, ...]] = field(default=None, converter=_optional_str_to_tuple_converter)

    show_default: bool = field(default=True)
    help: str = field(default="")

    def get_negatives(self, type_, *names) -> Tuple[str, ...]:
        type_ = get_origin(type_) or type_

        if self.negative is not None:
            return self.negative
        elif type_ not in (bool, list, set):
            return ()

        out = []
        for name in names:
            if name.startswith("--"):
                prefix = "--"
                name = name[2:]
            elif name.startswith("-"):
                # Don't currently support short flags
                continue
            else:
                # Should never reach here.
                raise UnreachableError

            if type_ is bool:
                negative_word = "no"
            else:
                negative_word = "empty"

            out.append(f"{prefix}{negative_word}-{name}")
        return tuple(out)


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

    return resolve(hint), cyclopts_parameter
