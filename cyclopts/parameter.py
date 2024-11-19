import inspect
from collections.abc import Iterable
from functools import partial
from typing import Any, Callable, List, Optional, Sequence, Tuple, Union, cast, get_args, get_origin

import attrs
from attrs import field, frozen

import cyclopts._env_var
import cyclopts.utils
from cyclopts._convert import ITERABLE_TYPES, convert
from cyclopts.annotations import is_annotated, is_union, resolve_optional
from cyclopts.group import Group
from cyclopts.utils import (
    default_name_transform,
    optional_to_tuple_converter,
    record_init,
    to_tuple_converter,
)

ITERATIVE_BOOL_IMPLICIT_VALUE = frozenset(
    {
        Iterable[bool],
        Sequence[bool],
        List[bool],
        list[bool],
        Tuple[bool, ...],
        tuple[bool, ...],
    }
)


_NEGATIVE_FLAG_TYPES = frozenset([bool, *ITERABLE_TYPES, *ITERATIVE_BOOL_IMPLICIT_VALUE])


def _not_hyphen_validator(instance, attribute, values):
    for value in values:
        if value is not None and value.startswith("-"):
            raise ValueError(f'{attribute.alias} value must NOT start with "-".')


def _negative_converter(default: tuple[str, ...]):
    def converter(value) -> tuple[str, ...]:
        if value is None:
            return default
        else:
            return to_tuple_converter(value)

    return converter


@record_init("_provided_args")
@frozen
class Parameter:
    """Cyclopts configuration for individual function parameters with :obj:`~typing.Annotated`.

    Example usage:

    .. code-block:: python

        from cyclopts import app, Parameter
        from typing import Annotated

        app = App()


        @app.default
        def main(foo: Annotated[int, Parameter(name="bar")]):
            print(foo)


        app()

    .. code-block:: console

        $ my-script 100
        100

        $ my-script --bar 100
        100
    """

    # All attribute docstrings has been moved to ``docs/api.rst`` for greater control with attrs.

    # This can ONLY ever be a Tuple[str, ...]
    # Usually starts with "--" or "-"
    name: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=lambda x: cast(tuple[str, ...], to_tuple_converter(x)),
    )

    _converter: Callable = field(default=None, alias="converter")

    # This can ONLY ever be a Tuple[Callable, ...]
    validator: Union[None, Callable, Iterable[Callable]] = field(
        default=(),
        converter=lambda x: cast(tuple[Callable, ...], to_tuple_converter(x)),
    )

    # This can ONLY ever be ``None`` or ``Tuple[str, ...]``
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
        converter=lambda x: cast(tuple[str, ...], to_tuple_converter(x)),
    )

    env_var_split: Callable = cyclopts._env_var.env_var_split

    # This can ONLY ever be a Tuple[str, ...]
    negative_bool: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=_negative_converter(("no-",)),
        validator=_not_hyphen_validator,
    )

    # This can ONLY ever be a Tuple[str, ...]
    negative_iterable: Union[None, str, Iterable[str]] = field(
        default=None,
        converter=_negative_converter(("empty-",)),
        validator=_not_hyphen_validator,
    )

    required: Optional[bool] = field(default=None)

    allow_leading_hyphen: bool = field(default=False)

    _name_transform: Optional[Callable[[str], str]] = field(
        alias="name_transform",
        default=None,
        kw_only=True,
    )

    # Should not get inherited
    accepts_keys: Optional[bool] = field(default=None)

    # Should not get inherited
    consume_multiple: bool = field(default=None, converter=attrs.converters.default_if_none(False))

    # Populated by the record_attrs_init_args decorator.
    _provided_args: tuple[str] = field(factory=tuple, init=False, eq=False)

    @property
    def show(self) -> bool:
        return self._show if self._show is not None else self.parse

    @property
    def converter(self):
        return self._converter if self._converter else partial(convert, name_transform=self.name_transform)

    @property
    def name_transform(self):
        return self._name_transform if self._name_transform else default_name_transform

    def get_negatives(self, type_) -> tuple[str, ...]:
        if is_union(type_):
            type_ = next(x for x in get_args(type_) if x is not None)

        origin = get_origin(type_)

        if type_ not in _NEGATIVE_FLAG_TYPES:
            if origin:
                if origin not in _NEGATIVE_FLAG_TYPES:
                    return ()
            else:
                return ()

        out, user_negatives = [], []
        if self.negative:
            for negative in self.negative:
                (out if negative.startswith("-") else user_negatives).append(negative)

            if not user_negatives:
                return tuple(out)

        assert isinstance(self.name, tuple)
        for name in self.name:
            if not name.startswith("--"):  # Only provide negation for option-like long flags.
                continue
            name = name[2:]
            name_components = name.split(".")

            if type_ is bool or type_ in ITERATIVE_BOOL_IMPLICIT_VALUE:
                negative_prefixes = self.negative_bool
            else:
                negative_prefixes = self.negative_iterable
            name_prefix = ".".join(name_components[:-1])
            if name_prefix:
                name_prefix += "."
            assert isinstance(negative_prefixes, tuple)
            if self.negative is None:
                for negative_prefix in negative_prefixes:
                    out.append(f"--{name_prefix}{negative_prefix}{name_components[-1]}")
            else:
                for negative in user_negatives:
                    out.append(f"--{name_prefix}{negative}")
        return tuple(out)

    def __repr__(self):
        """Only shows non-default values."""
        content = ", ".join(
            [
                f"{a.alias}={getattr(self, a.name)!r}"
                for a in self.__attrs_attrs__  # pyright: ignore[reportAttributeAccessIssue]
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
            for a in parameter.__attrs_attrs__:  # pyright: ignore[reportAttributeAccessIssue]
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
            **{a.alias: a.default for a in cls.__attrs_attrs__ if a.init}  # pyright: ignore[reportAttributeAccessIssue]
        )

    @classmethod
    def from_annotation(cls, type_: Any, *default_parameters: Optional["Parameter"]) -> "Parameter":
        """Resolve the immediate Parameter from a type hint."""
        cyclopts_parameters = []
        if type_ is not inspect.Parameter.empty:
            type_ = resolve_optional(type_)

            if is_annotated(type_):
                annotations = type_.__metadata__  # pyright: ignore[reportGeneralTypeIssues]
                cyclopts_parameters = [x for x in annotations if isinstance(x, Parameter)]

        return cls.combine(*default_parameters, *cyclopts_parameters)


def validate_command(f: Callable):
    """Validate if a function abides by Cyclopts's rules.

    Raises
    ------
    ValueError
        Function has naming or parameter/signature inconsistencies.
    """
    signature = cyclopts.utils.signature(f)
    for iparam in signature.parameters.values():
        get_origin(iparam.annotation)
        cparam = Parameter.from_annotation(iparam.annotation)
        if not cparam.parse and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")
