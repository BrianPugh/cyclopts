import inspect
from typing import Iterable, List, Optional, Tuple, Type, Union, get_args, get_origin

from attrs import field, frozen

from cyclopts.coercion import (
    AnnotatedType,
    coerce,
    get_origin_and_validate,
    optional_str_to_tuple_converter,
    resolve,
    resolve_optional,
    str_to_tuple_converter,
)
from cyclopts.exceptions import MultipleParameterAnnotationError
from cyclopts.protocols import Converter, Validator


def _token_count_validator(instance, attribute, value):
    if value is not None and instance.converter is None:
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
        type_, cparam = get_hint_parameter(iparam.annotation)
        if cparam.parse is False and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")
        if get_origin(type_) is tuple:
            if ... in get_args(type_):
                raise ValueError("Cannot use a variable-length tuple.")


@frozen
class Parameter:
    """Cyclopts configuration for individual function parameters."""

    _name: Union[None, str, Iterable[str]] = field(
        default=None, converter=optional_str_to_tuple_converter, alias="name"
    )
    """
    Name(s) to expose to the CLI.
    Defaults to the python parameter's name, prepended with ``--``.
    Single-character options should start with ``-``.
    Full-name options should start with ``--``.
    """

    converter: Optional[Converter] = field(default=None)
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

    negative: Union[None, str, Iterable[str]] = field(default=None, converter=optional_str_to_tuple_converter)
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

    parse: Optional[bool] = field(default=None)
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

    show_default: Optional[bool] = field(default=None)
    """
    If a variable has a default, display the default in the help page.

    Defaults to ``None``, which is similar to ``True``, but will not display the default if it's ``None``.
    """

    show_choices: Optional[bool] = field(default=None)
    """
    If a variable has a set of choices (``Literal``, ``Enum``), display the default in the help page.
    Defaults to ``True``.
    """

    help: Optional[str] = field(default=None)
    """
    Help string to be displayed in the help page.
    If not specified, defaults to the docstring.
    """

    show_env_var: Optional[bool] = field(default=None)
    """
    If a variable has ``env_var`` set, display the variable name in the help page.
    Defaults to ``True``.
    """

    _env_var: Union[None, str, Iterable[str]] = field(
        default=None, converter=optional_str_to_tuple_converter, alias="env_var"
    )
    """
    Fallback to environment variable(s) if CLI value not provided.
    If multiple environment variables are given, the left-most environment variable with a set value will be used.
    If no environment variable is set, Cyclopts will fallback to the function-signature default.
    """

    @property
    def name(self):
        return str_to_tuple_converter(self._name)

    @property
    def env_var(self):
        return str_to_tuple_converter(self._env_var)

    @property
    def show_(self):
        if self.show is not None:
            return self.show
        elif self.parse is False:
            return False
        else:
            return True

    @property
    def converter_(self):
        if self.converter:
            return self.converter
        else:
            return coerce

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


def get_hint_parameter(type_: Type) -> Tuple[Type, Parameter]:
    """Get the type hint and Cyclopts :class:`Parameter` from a type-hint.

    If a ``cyclopts.Parameter`` is not found, a default Parameter is returned.
    """
    if type_ is inspect.Parameter.empty:
        return str, Parameter()

    type_ = resolve_optional(type_)

    if type(type_) is AnnotatedType:
        annotations = type_.__metadata__  # pyright: ignore[reportGeneralTypeIssues]
        type_ = get_args(type_)[0]
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
