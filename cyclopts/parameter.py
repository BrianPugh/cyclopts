import inspect
from typing import Iterable, List, Optional, Tuple, Type, Union, get_args, get_origin

from attrs import field, frozen

from cyclopts.coercion import (
    AnnotatedType,
    coerce,
    get_origin_and_validate,
    optional_to_tuple_converter,
    resolve,
    resolve_optional,
    to_tuple_converter,
)
from cyclopts.protocols import Converter, Validator
from cyclopts.utils import record_init_kwargs


def _token_count_validator(instance, attribute, value):
    if value is not None and instance._converter is None:
        raise ValueError('Must specify a "converter" if setting "token_count".')


def _double_hyphen_validator(instance, attribute, values):
    if not values:
        return

    for value in values:
        if value is not None and not value.startswith("--"):
            raise ValueError(f'{attribute.alias} value must start with "--".')


@record_init_kwargs("_provided_args")
@frozen
class Parameter:
    """Cyclopts configuration for individual function parameters."""

    # All documentation has been moved to ``docs/api.rst`` for greater control with attrs.

    _name: Union[None, str, Iterable[str]] = field(default=None, converter=optional_to_tuple_converter, alias="name")

    _converter: Optional[Converter] = field(default=None, alias="converter")

    validator: Union[None, Validator, Iterable[Validator]] = field(default=None, converter=to_tuple_converter)

    negative: Union[None, str, Iterable[str]] = field(default=None, converter=optional_to_tuple_converter)

    token_count: Optional[int] = field(default=None, validator=_token_count_validator)

    parse: Optional[bool] = field(default=None)

    _show: Optional[bool] = field(default=None, alias="show")

    show_default: Optional[bool] = field(default=None)

    show_choices: Optional[bool] = field(default=None)

    help: Optional[str] = field(default=None)

    show_env_var: Optional[bool] = field(default=None)

    _env_var: Union[None, str, Iterable[str]] = field(
        default=None, converter=optional_to_tuple_converter, alias="env_var"
    )

    _negative_bool: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=optional_to_tuple_converter,
        validator=_double_hyphen_validator,
        alias="negative_bool",
    )

    _negative_iterable: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=optional_to_tuple_converter,
        validator=_double_hyphen_validator,
        alias="negative_iterable",
    )

    # Populated by the record_attrs_init_args decorator.
    _provided_args: Tuple[str] = field(default=(), init=False, eq=False)

    @property
    def name(self):
        return to_tuple_converter(self._name)

    @property
    def env_var(self):
        return to_tuple_converter(self._env_var)

    @property
    def show(self):
        if self._show is not None:
            return self._show
        elif self.parse is False:
            return False
        else:
            return True

    @property
    def converter(self):
        if self._converter:
            return self._converter
        else:
            return coerce

    @property
    def negative_bool(self):
        if self._negative_bool is None:
            return ("--no-",)
        else:
            return self._negative_bool

    @property
    def negative_iterable(self):
        if self._negative_iterable is None:
            return ("--empty-",)
        else:
            return self._negative_iterable

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
                name = name[2:]
            elif name.startswith("-"):
                # Do not support automatic negation for short flags.
                continue
            else:
                # Should never reach here.
                raise NotImplementedError("All parameters should have started with '-' or '--'.")

            negative_prefixes = self.negative_bool if type_ is bool else self.negative_iterable

            for negative_prefix in negative_prefixes:
                out.append(f"{negative_prefix}{name}")
        return tuple(out)

    def __repr__(self):
        """Only shows non-default values."""
        content = ", ".join(
            [
                f"{a.alias}={getattr(self, a.name)!r}"
                for a in self.__attrs_attrs__  # pyright: ignore[reportGeneralTypeIssues]
                if a.alias in self._provided_args
            ]
        )
        return f"{type(self).__name__}({content})"

    @classmethod
    def combine(cls, *parameters: Optional["Parameter"]) -> "Parameter":
        """Returns a new Parameter with values of ``new_parameters`` overriding ``self``.

        Parameters
        ----------
        `*parameters`: Optional[Parameter]
             Parameters who's attributes override ``self`` attributes.
             Ordered from least-to-highest attribute priority.
        """
        kwargs = {}
        for parameter in parameters:
            if parameter is None:
                continue
            for a in parameter.__attrs_attrs__:  # pyright: ignore[reportGeneralTypeIssues]
                if a.init and a.alias in parameter._provided_args:
                    kwargs[a.alias] = getattr(parameter, a.name)

        return cls(**kwargs)

    @classmethod
    def default(cls) -> "Parameter":
        """Create a Parameter with all Cyclopts-default values.

        This is different than just ``Parameter()`` because it will override
        all values of upstream Parameters.
        """
        return cls(
            **{a.alias: a.default for a in cls.__attrs_attrs__ if a.init}  # pyright: ignore[reportGeneralTypeIssues]
        )


def validate_command(f, default_parameter: Optional[Parameter] = None):
    """Validate if a function abides by Cyclopts's rules.

    Raises
    ------
    ValueError
        Function has naming or parameter/signature inconsistencies.
    """
    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        _ = get_origin_and_validate(iparam.annotation)
        type_, cparam = get_hint_parameter(iparam.annotation, default_parameter=default_parameter)
        if cparam.parse is False and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")
        if get_origin(type_) is tuple:
            if ... in get_args(type_):
                raise ValueError("Cannot use a variable-length tuple.")


def get_names(parameter: inspect.Parameter, default_parameter: Optional[Parameter] = None) -> List[str]:
    """Derive the CLI name for an ``inspect.Parameter``."""
    _, param = get_hint_parameter(parameter.annotation, default_parameter=default_parameter)
    if param.name:
        names = list(param.name)
    else:
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL):
            # Name is only used for help-string
            names = [parameter.name.upper()]
        else:
            names = ["--" + parameter.name.replace("_", "-")]

    return names


def get_hint_parameter(type_: Type, default_parameter: Optional[Parameter] = None) -> Tuple[Type, Parameter]:
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
    else:
        cyclopts_parameters = []

    cyclopts_parameter = Parameter.combine(default_parameter, *cyclopts_parameters)
    return resolve(type_), cyclopts_parameter
