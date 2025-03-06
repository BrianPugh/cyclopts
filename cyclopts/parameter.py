import inspect
from collections.abc import Iterable
from copy import deepcopy
from functools import partial
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

import attrs
from attrs import define, field

import cyclopts._env_var
import cyclopts.utils
from cyclopts._convert import ITERABLE_TYPES, convert
from cyclopts.annotations import is_annotated, is_union, resolve_optional
from cyclopts.group import Group
from cyclopts.token import Token
from cyclopts.utils import (
    default_name_transform,
    frozen,
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


T = TypeVar("T")

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


# TODO: Breaking change; all fields after ``name`` should be ``kw_only=True``.
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

    _converter: Optional[Callable[[Any, Sequence[Token]], Any]] = field(default=None, alias="converter")

    # This can ONLY ever be a Tuple[Callable, ...]
    validator: Union[None, Callable[[Any, Any], Any], Iterable[Callable[[Any, Any], Any]]] = field(
        default=(),
        converter=lambda x: cast(tuple[Callable[[Any, Any], Any], ...], to_tuple_converter(x)),
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

    json_dict: Optional[bool] = field(default=None, kw_only=True)

    json_list: Optional[bool] = field(default=None, kw_only=True)

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
        """Returns a new Parameter with combined values of all provided ``parameters``.

        Parameters
        ----------
        `*parameters`: Optional[Parameter]
             Parameters who's attributes override ``self`` attributes.
             Ordered from least-to-highest attribute priority.
        """
        kwargs = {}
        filtered = [x for x in parameters if x is not None]
        # In the common case of 0/1 parameters to combine, we can avoid
        # instantiating a new Parameter object.
        if len(filtered) == 1:
            return filtered[0]
        elif not filtered:
            return EMPTY_PARAMETER

        for parameter in filtered:
            for alias in parameter._provided_args:
                kwargs[alias] = getattr(parameter, _parameter_alias_to_name[alias])

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
    def from_annotation(cls, type_: Any, *default_parameters: Optional["Parameter"]) -> tuple[Any, "Parameter"]:
        """Resolve the immediate Parameter from a type hint."""
        if type_ is inspect.Parameter.empty:
            if default_parameters:
                return type_, cls.combine(*default_parameters)
            else:
                return type_, EMPTY_PARAMETER
        else:
            type_, parameters = get_parameters(type_)
            return type_, cls.combine(*default_parameters, *parameters)

    def __call__(self, obj: T) -> T:
        """Decorator interface for annotating a function/class with a :class:`Parameter`.

        Most commonly used for directly configuring a class:

        .. code-block:: python

            @Parameter(...)
            class Foo: ...
        """
        if not hasattr(obj, "__cyclopts__"):
            obj.__cyclopts__ = CycloptsConfig(obj=obj)  # pyright: ignore[reportAttributeAccessIssue]
        elif obj.__cyclopts__.obj != obj:  # pyright: ignore[reportAttributeAccessIssue]
            # Create a copy so that children class Parameter decorators don't impact the parent.
            obj.__cyclopts__ = deepcopy(obj.__cyclopts__)  # pyright: ignore[reportAttributeAccessIssue]
        obj.__cyclopts__.parameters.append(self)  # pyright: ignore[reportAttributeAccessIssue]
        return obj


_parameter_alias_to_name = {
    p.alias: p.name
    for p in Parameter.__attrs_attrs__  # pyright: ignore[reportAttributeAccessIssue]
    if p.init
}

EMPTY_PARAMETER = Parameter()


def validate_command(f: Callable):
    """Validate if a function abides by Cyclopts's rules.

    Raises
    ------
    ValueError
        Function has naming or parameter/signature inconsistencies.
    """
    if (f.__module__ or "").startswith("cyclopts"):  # Speed optimization.
        return
    signature = cyclopts.utils.signature(f)
    for iparam in signature.parameters.values():
        # Speed optimization: if an object is not annotated, then there's nothing
        # to validate. Checking if there's an annotation is significantly faster
        # than instantiating a cyclopts.Parameter object.
        if not is_annotated(iparam.annotation):
            continue
        _, cparam = Parameter.from_annotation(iparam.annotation)
        if not cparam.parse and iparam.kind is not iparam.KEYWORD_ONLY:
            raise ValueError("Parameter.parse=False must be used with a KEYWORD_ONLY function parameter.")


def get_parameters(hint: T) -> tuple[T, list[Parameter]]:
    """At root level, checks for cyclopts.Parameter annotations.

    Includes checking the ``__cyclopts__`` attribute.

    Returns
    -------
    hint
        Annotation hint with :obj:`Annotated` and :obj:`Optional` resolved.
    list[Parameter]
        List of parameters discovered.
    """
    parameters = []
    hint = resolve_optional(hint)
    if cyclopts_config := getattr(hint, "__cyclopts__", None):
        parameters.extend(cyclopts_config.parameters)
    if is_annotated(hint):
        inner = get_args(hint)
        hint = inner[0]
        parameters.extend(x for x in inner[1:] if isinstance(x, Parameter))

    return hint, parameters


@define
class CycloptsConfig:
    """
    Intended for storing additional data to a ``__cyclopts__`` attribute via decoration.
    """

    obj: Any = None
    parameters: list[Parameter] = field(factory=list, init=False)
