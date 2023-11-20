import inspect
import typing
from typing import Any, Callable, Iterable, List, Optional, Protocol, Tuple, Type, Union, get_origin

from attrs import field, frozen
from typing_extensions import Annotated

from cyclopts.coercion import coerce, resolve
from cyclopts.exceptions import MultipleParameterAnnotationError


def _str_to_tuple_converter(input_value: Union[str, Iterable[str]]) -> Tuple[str, ...]:
    if isinstance(input_value, str):
        return (input_value,)
    return tuple(input_value)


def _optional_str_to_tuple_converter(input_value: Union[None, str, Iterable[str]]) -> Optional[Tuple[str, ...]]:
    if input_value is None:
        return None

    return _str_to_tuple_converter(input_value)


def _default_validator(type_, arg):
    pass


def _token_count_validator(instance, attribute, value):
    if value is not None and instance.converter is coerce:
        raise ValueError('Must specify a "converter" if setting "token_count".')


class Converter(Protocol):
    def __call__(self, type_: Type, *args: str) -> Any:
        ...


class Validator(Protocol):
    def __call__(self, type_: Type, value: Any) -> None:
        ...


@frozen
class Parameter:
    """Additional cyclopts configuration for individual function parameters.

    Parameters
    ----------
    name: Union[str, Iterable[str]]
        Defaults to the python parameter's name, prepended with ``--``.
    negative: Union[None, str, Iterable[str]]
        Name(s) for empty iterables or false boolean flags.
        For booleans, defaults to ``--no-{name}``.
        For iterables, defaults to ``--empty-{name}``.
        Set to an empty list to disable this feature.
    help: str
       Help string to be displayed in the help page.
    show_default: bool
        If a variable has a default, display the default in the help page.
        Defaults to ``True``.
    converter: Optional[Converter]
        A function that converts string token(s) into an object. The converter must have signature:

        .. code-block:: python

            def converter(type_, *args) -> Any:
                pass

        where ``Any`` is the intended type of the annotated variable.
        If not provided, defaults to Cyclopts's coercion engine.
    validator: Validator
        A function that validates data returned by the ``converter``.

        .. code-block:: python

            def validator(type_, value: Any) -> None:
                pass  # Raise any exception here if data is invalid.
    token_count: Optional[int]
       Number of CLI tokens this parameter consumes.
       Used when the annotated parameter is a custom class that consumes more
       (or less) than the standard single token.
       If specified, a custom ``converter`` **must** also be specified.
       Defaults to autodetecting based on type annotation.
    """

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
    # Typically this is a single token.
    # The returned value will be supplied to the command.
    converter: Converter = field(default=coerce)

    # User provided validator function with signatre:
    #
    #    def validator(type_, arg):
    #        pass
    #
    # The validator (if provided) will be invoked AFTER the converter/implicit-coercion.
    validator: Validator = field(default=_default_validator)

    negative: Optional[Tuple[str, ...]] = field(default=None, converter=_optional_str_to_tuple_converter)

    token_count: Optional[int] = field(default=None, validator=_token_count_validator)

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
                raise NotImplementedError("All parameters should have started with '-' or '--'.")

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
    """Get the type hint and Cyclopts :class:`Parameter` from a possibly annotated inspect Parameter."""
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
