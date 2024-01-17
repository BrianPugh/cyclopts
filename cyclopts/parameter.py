import inspect
from typing import Any, Callable, Iterable, Optional, Tuple, Type, Union, cast, get_args, get_origin

import attrs
from attrs import field, frozen

from cyclopts._convert import (
    AnnotatedType,
    convert,
    get_origin_and_validate,
    optional_to_tuple_converter,
    resolve,
    resolve_optional,
    to_tuple_converter,
)
from cyclopts.group import Group
from cyclopts.utils import record_init


def _double_hyphen_validator(instance, attribute, values):
    if not values:
        return

    for value in values:
        if value is not None and not value.startswith("--"):
            raise ValueError(f'{attribute.alias} value must start with "--".')


def _negative_converter(default: Tuple[str, ...]):
    def converter(value) -> Tuple[str, ...]:
        if value is None:
            return default
        else:
            return to_tuple_converter(value)

    return converter


@record_init("_provided_args")
@frozen
class Parameter:
    """Cyclopts configuration for individual function parameters."""

    # All documentation has been moved to ``docs/api.rst`` for greater control with attrs.

    # This can ONLY ever be a Tuple[str, ...]
    name: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=lambda x: cast(Tuple[str, ...], to_tuple_converter(x)),
    )

    converter: Callable = field(default=None, converter=attrs.converters.default_if_none(convert))

    # This can ONLY ever be a Tuple[Callable, ...]
    validator: Union[None, Callable, Iterable[Callable]] = field(
        default=(),
        converter=lambda x: cast(Tuple[Callable, ...], to_tuple_converter(x)),
    )

    # This can ONLY ever be a Tuple[str, ...]
    negative: Union[None, str, Iterable[str]] = field(default=None, converter=optional_to_tuple_converter)

    # This can ONLY ever be a Tuple[Union[Group, str], ...]
    group: Union[None, Group, str, Iterable[Union[Group, str]]] = field(
        default=None, converter=to_tuple_converter, hash=False
    )

    parse: bool = field(default=None, converter=attrs.converters.default_if_none(True))

    _show: Optional[bool] = field(default=None, alias="show")

    show_default: Optional[bool] = field(default=None)

    show_choices: bool = field(default=None, converter=attrs.converters.default_if_none(True))

    help: Optional[str] = field(default=None)

    show_env_var: bool = field(default=None, converter=attrs.converters.default_if_none(True))

    # This can ONLY ever be a Tuple[str, ...]
    env_var: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=lambda x: cast(Tuple[str, ...], to_tuple_converter(x)),
    )

    negative_bool: Tuple[str, ...] = field(
        default=None,
        converter=_negative_converter(("--no-",)),
        validator=_double_hyphen_validator,
    )

    negative_iterable: Tuple[str, ...] = field(
        default=None,
        converter=_negative_converter(("--empty-",)),
        validator=_double_hyphen_validator,
    )

    required: Optional[bool] = field(default=None)

    allow_leading_hyphen: bool = field(default=False)

    # Populated by the record_attrs_init_args decorator.
    _provided_args: Tuple[str] = field(default=(), init=False, eq=False)

    @property
    def show(self):
        return self._show if self._show is not None else self.parse

    def get_negatives(self, type_, *names: str) -> Tuple[str, ...]:
        type_ = get_origin(type_) or type_

        if self.negative is not None:
            return self.negative  # pyright: ignore
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
        """Returns a new Parameter with values of ``parameters``.

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

        This is different than just :class:`Parameter` because the default
        values will be recorded and override all upstream parameter values.
        """
        return cls(
            **{a.alias: a.default for a in cls.__attrs_attrs__ if a.init}  # pyright: ignore[reportGeneralTypeIssues]
        )


def validate_command(f: Callable):
    """Validate if a function abides by Cyclopts's rules.

    Raises
    ------
    ValueError
        Function has naming or parameter/signature inconsistencies.
    """
    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        get_origin_and_validate(iparam.annotation)
        type_, cparam = get_hint_parameter(iparam)
        if not cparam.parse and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")


def get_hint_parameter(
    type_: Union[Type, inspect.Parameter], *default_parameters: Optional[Parameter]
) -> Tuple[Type, Parameter]:
    """Get the type hint and Cyclopts :class:`Parameter` from a type-hint.

    If a ``cyclopts.Parameter`` is not found, a default Parameter is returned.
    """
    cyclopts_parameters = []

    if isinstance(type_, inspect.Parameter):
        annotation = type_.annotation

        if annotation is inspect.Parameter.empty or resolve(annotation) is Any:
            if type_.default in (inspect.Parameter.empty, None):
                annotation = str
            else:
                return get_hint_parameter(type(type_.default), *default_parameters)
    else:
        annotation = type_

        if annotation is inspect.Parameter.empty:
            annotation = str

    annotation = resolve_optional(annotation)

    if type(annotation) is AnnotatedType:
        annotations = annotation.__metadata__  # pyright: ignore[reportGeneralTypeIssues]
        annotation = get_args(annotation)[0]
        cyclopts_parameters = [x for x in annotations if isinstance(x, Parameter)]
    annotation = resolve(annotation)

    cparam = Parameter.combine(*default_parameters, *cyclopts_parameters)
    return annotation, cparam
