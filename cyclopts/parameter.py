import inspect
import typing
from functools import lru_cache
from typing import Iterable, List, Optional, Tuple, Type, Union, get_origin

from attrs import field, frozen
from typing_extensions import Annotated

from cyclopts.coercion import AnnotatedType, coerce, get_origin_and_validate, resolve
from cyclopts.exceptions import MultipleParameterAnnotationError
from cyclopts.protocols import Converter, Validator


def _str_to_tuple_converter(input_value: Union[str, Iterable[str]]) -> Tuple[str, ...]:
    if isinstance(input_value, str):
        return (input_value,)
    return tuple(input_value)


def _optional_str_to_tuple_converter(input_value: Union[None, str, Iterable[str]]) -> Optional[Tuple[str, ...]]:
    if input_value is None:
        return None

    if not input_value:
        return ()

    return _str_to_tuple_converter(input_value)


def _token_count_validator(instance, attribute, value):
    if value is not None and instance.converter is coerce:
        raise ValueError('Must specify a "converter" if setting "token_count".')


def validate_command(f):
    """Validate if a function abides by Cyclopts's rules.

    Raises
    ------
    ValueError
        Function has naming or parameter/signature inconsistencies.
    """
    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        _ = get_origin_and_validate(iparam.annotation)
        _, cparam = get_hint_parameter(iparam.annotation)
        if not cparam.parse and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")


@frozen
class Parameter:
    """Cyclopts configuration for individual function parameters."""

    name: Union[str, Iterable[str]] = field(default=[], converter=_str_to_tuple_converter)
    """
    Name(s) to expose to the CLI.
    Defaults to the python parameter's name, prepended with ``--``.
    Single-character options should start with ``-``.
    Full-name options should start with ``--``.
    """

    converter: Converter = field(default=coerce)
    """
    A function that converts string token(s) into an object. The converter must have signature:

    .. code-block:: python

        def converter(type_, *args) -> Any:
            pass

    where ``Any`` is the intended type of the annotated variable.
    If not provided, defaults to :ref:`Cyclopts's internal coercion engine <Coercion Rules>`.
    """

    validator: Optional[Validator] = field(default=None)
    """
    A function that validates data returned by the ``converter``.

    .. code-block:: python

        def validator(type_, value: Any) -> None:
            pass  # Raise a TypeError, ValueError, or AssertionError here if data is invalid.
    """

    negative: Union[None, str, Iterable[str]] = field(default=None, converter=_optional_str_to_tuple_converter)
    """
    Name(s) for empty iterables or false boolean flags.
    For booleans, defaults to ``--no-{name}``.
    For iterables, defaults to ``--empty-{name}``.
    Set to an empty list to disable this feature.
    """

    token_count: Optional[int] = field(default=None, validator=_token_count_validator)
    """
    Number of CLI tokens this parameter consumes.
    For advanced usage when the annotated parameter is a custom class that consumes more
    (or less) than the standard single token.
    If specified, a custom ``converter`` **must** also be specified.
    Defaults to autodetecting based on type annotation.
    """

    parse: bool = field(default=True)
    """
    Attempt to use this parameter while parsing.
    Intended only for advance usage with custom command invocation.
    Annotated parameter **must** be keyword-only.
    Defaults to ``True``.
    """

    show: Optional[bool] = field(default=None)
    """
    Show this parameter in the help screen.
    If ``False``, state of all other ``show_*`` flags are ignored.
    Defaults to ``parse`` value (``True``).
    """

    show_default: bool = field(default=True)
    """
    If a variable has a default, display the default in the help page.
    Defaults to ``True``.
    """

    show_choices: bool = field(default=True)
    """
    If a variable has a set of choices (``Literal``, ``Enum``), display the default in the help page.
    Defaults to ``True``.
    """

    help: Optional[str] = field(default=None)
    """
    Help string to be displayed in the help page.
    If not specified, defaults to the docstring.
    """

    @property
    def show_(self):
        if self.show is not None:
            return self.show
        elif self.parse:
            return True
        else:
            return False

    def get_negatives(self, type_, *names) -> Tuple[str, ...]:
        type_ = get_origin(type_) or type_

        if self.negative is not None:
            assert isinstance(self.negative, tuple)
            return self.negative
        elif type_ not in (bool, list, set):
            return ()

        out = []
        for name in names:
            if name.startswith("--"):
                prefix = "--"
                name = name[2:]
            elif name.startswith("-"):
                # Do not support automatic negation for short flags.
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
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL):
            # Name is only used for help-string
            names = [parameter.name.upper()]
        else:
            names = ["--" + parameter.name.replace("_", "-")]

    return names


@lru_cache
def get_hint_parameter(type_: Type) -> Tuple[Type, Parameter]:
    """Get the type hint and Cyclopts :class:`Parameter` from a type-hint.

    If a ``cyclopts.Parameter`` is not found, a default Parameter is returned.
    """
    if type_ is inspect.Parameter.empty:
        return str, Parameter()

    if type(type_) is AnnotatedType:
        annotations = type_.__metadata__  # pyright: ignore[reportGeneralTypeIssues]
        type_ = typing.get_args(type_)[0]
        cyclopts_parameters = [x for x in annotations if isinstance(x, Parameter)]
        if len(cyclopts_parameters) > 2:
            raise MultipleParameterAnnotationError
        elif len(cyclopts_parameters) == 1:
            cyclopts_parameter = cyclopts_parameters[0]
        else:
            cyclopts_parameter = Parameter()
    else:
        cyclopts_parameter = Parameter()

    return resolve(type_), cyclopts_parameter
