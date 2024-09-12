import inspect
import itertools
import sys
from collections.abc import Iterator
from contextlib import suppress
from functools import partial
from inspect import isclass
from typing import Any, Callable, NamedTuple, Optional, Union, get_args, get_origin

from attrs import define, field

from cyclopts._convert import (
    convert,
    resolve,
    resolve_annotated,
    resolve_optional,
    token_count,
)
from cyclopts.exceptions import (
    CoercionError,
    MissingArgumentError,
    MixedArgumentError,
    RepeatArgumentError,
    ValidationError,
)
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.token import Token
from cyclopts.utils import AnnotatedType, NoneType, ParameterDict, Sentinel, is_union

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required
else:
    from typing import NotRequired, Required

_IS_PYTHON_3_8 = sys.version_info[:2] == (3, 8)
_PARAMETER_EMPTY_HELP = Parameter(help="")

# parameter subkeys should not inherit these parameter values from their parent.
_PARAMETER_SUBKEY_BLOCKER = Parameter(
    name=None,
    converter=None,  # pyright: ignore
    validator=None,
    negative=None,
    # Do NOT include help here; handled elsewhere due to docstring parsing.
    accepts_keys=None,
)


class _FieldInfo(NamedTuple):
    hint: Any
    required: bool
    kw_only: bool = True


def _iparam_get_hint(iparam):
    hint = iparam.annotation
    if hint is inspect.Parameter.empty or resolve(hint) is Any:
        hint = str if iparam.default is inspect.Parameter.empty or iparam.default is None else type(iparam.default)
    hint = resolve_optional(hint)
    return hint


def _typed_dict_field_info(typeddict) -> dict[str, _FieldInfo]:
    # The ``__required_keys__`` and ``__optional_keys__`` attributes of TypedDict are kind of broken in <cp3.11.
    out = {}
    # Don't use get_type_hints because it resolves Annotated automatically.
    for name, annotation in typeddict.__annotations__.items():
        origin = get_origin(resolve_annotated(annotation))
        if origin is Required:
            required = True
        elif origin is NotRequired:
            required = False
        elif typeddict.__total__:  # Fields are REQUIRED by default.
            required = True
        else:  # Fields are OPTIONAL by default
            required = False
        out[name] = _FieldInfo(annotation, required)
    return out


def _generic_class_field_info(f) -> dict[str, _FieldInfo]:
    signature = inspect.signature(f.__init__)
    out = {}
    for name, iparam in signature.parameters.items():
        if iparam.name == "self" or iparam.kind is iparam.VAR_KEYWORD or iparam.kind is iparam.VAR_POSITIONAL:
            continue
        kw_only = iparam.kind == iparam.KEYWORD_ONLY
        required = iparam.default == iparam.empty
        out[name] = _FieldInfo(iparam.annotation, required, kw_only=kw_only)
    return out


def _pydantic_field_info(model) -> dict[str, _FieldInfo]:
    out = {}
    for k, v in model.model_fields.items():
        out[k] = _FieldInfo(v.annotation, v.is_required(), kw_only=v.kw_only)
    return out


def _missing_keys_factory(get_field_info: Callable[[Any], dict[str, _FieldInfo]]):
    def inner(argument: "Argument", data: dict) -> set[str]:
        field_info = get_field_info(argument.hint)
        required = {k for k, v in field_info.items() if v.required}
        return set(required) - set(data)

    return inner


def is_pydantic(hint) -> bool:
    return hasattr(hint, "__pydantic_core_schema__")


def is_dataclass(hint) -> bool:
    return hasattr(hint, "__dataclass_fields__")


def is_namedtuple(hint) -> bool:
    return isclass(hint) and issubclass(hint, tuple) and hasattr(hint, "_fields")


def is_attrs(hint) -> bool:
    return hasattr(hint, "__attrs_attrs__")


def is_typeddict(hint) -> bool:
    """Determine if a type annotation is a TypedDict.

    This is surprisingly hard! Modified from Beartype's implementation:

        https://github.com/beartype/beartype/blob/main/beartype/_util/hint/pep/proposal/utilpep589.py
    """
    hint = resolve(hint)
    if is_union(get_origin(hint)):
        return any(is_typeddict(x) for x in get_args(hint))

    if not (isinstance(hint, type) and issubclass(hint, dict)):
        return False

    return (
        # This "dict" subclass defines these "TypedDict" attributes *AND*...
        hasattr(hint, "__annotations__")
        and hasattr(hint, "__total__")
        and
        # Either...
        (
            # The active Python interpreter targets exactly Python 3.8 and
            # thus fails to unconditionally define the remaining attributes
            # *OR*...
            _IS_PYTHON_3_8
            or
            # The active Python interpreter targets any other Python version
            # and thus unconditionally defines the remaining attributes.
            (hasattr(hint, "__required_keys__") and hasattr(hint, "__optional_keys__"))
        )
    )


def _identity_converter(type_, element):
    return element


class ArgumentCollection(list):
    """Provides easy lookups/pattern matching."""

    def __init__(self, *args, groups: Optional[list[Group]] = None):
        super().__init__(*args)
        self.groups = [] if groups is None else groups

    def copy(self) -> "ArgumentCollection":
        return type(self)(self)

    def match(
        self,
        term: Union[str, int],
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> tuple["Argument", tuple[str, ...], Any]:
        """Maps keyword CLI arguments to their :class:`Argument`.

        Parameters
        ----------
        token: str
            Something like "--foo" or "-f" or "--foo.bar.baz" or an integer index.

        Returns
        -------
        Argument
            Matched :class:`Argument`.
        Tuple[str, ...]
            Python keys into Argument. Non-empty iff Argument accepts keys.
        Any
            Implicit value (if a flag). :obj:`None` otherwise.
        """
        best_match_argument, best_match_keys, best_implicit_value = None, None, None
        for argument in self:
            try:
                match_keys, implicit_value = argument.match(term, transform=transform, delimiter=delimiter)
            except ValueError:
                continue
            if best_match_keys is None or len(match_keys) < len(best_match_keys):
                best_match_keys = match_keys
                best_match_argument = argument
                best_implicit_value = implicit_value
            if not match_keys:  # Perfect match
                break

        if best_match_argument is None or best_match_keys is None:
            raise ValueError(f"No Argument matches {term!r}")

        return best_match_argument, best_match_keys, best_implicit_value

    def _set_marks(self, val: bool):
        for argument in self:
            argument._marked = val

    def convert(self):
        self._set_marks(False)
        for argument in sorted(self, key=lambda x: x.keys):
            if argument._marked:
                continue
            argument.convert_and_validate()

    @property
    def names(self):
        return (name for argument in self for name in argument.names)

    @classmethod
    def _from_type(
        cls,
        iparam: inspect.Parameter,
        hint,
        keys: tuple[str, ...],
        *default_parameters,
        group_lookup: dict[str, Group],
        group_arguments: Group,
        group_parameters: Group,
        parse_docstring: bool = True,
        positional_index: Optional[int] = None,
        _resolve_groups: bool = True,
    ):
        assert hint is not NoneType
        out = cls(groups=list(group_lookup.values()))

        cyclopts_parameters_no_group = []

        hint = resolve_optional(hint)
        if type(hint) is AnnotatedType:
            annotations = hint.__metadata__  # pyright: ignore
            hint = get_args(hint)[0]
            cyclopts_parameters_no_group.extend(x for x in annotations if isinstance(x, Parameter))

        if not keys:  # root hint annotation
            if iparam.kind is iparam.VAR_KEYWORD:
                hint = dict[str, hint]
            elif iparam.kind is iparam.VAR_POSITIONAL:
                hint = tuple[hint, ...]

        if _resolve_groups:
            cyclopts_parameters = []
            for cparam in cyclopts_parameters_no_group:
                resolved_groups = []
                for group in cparam.group:  # pyright:ignore
                    if isinstance(group, str):
                        group = group_lookup[group]
                    resolved_groups.append(group)
                    cyclopts_parameters.append(group.default_parameter)
                cyclopts_parameters.append(cparam)
                if resolved_groups:
                    cyclopts_parameters.append(Parameter(group=resolved_groups))
        else:
            cyclopts_parameters = cyclopts_parameters_no_group

        upstream_parameter = Parameter.combine(
            (
                Parameter(group=group_arguments)
                if iparam.kind in (iparam.POSITIONAL_ONLY, iparam.VAR_POSITIONAL)
                else Parameter(group=group_parameters)
            ),
            *default_parameters,
        )
        immediate_parameter = Parameter.combine(*cyclopts_parameters)

        if not immediate_parameter.parse:
            return out

        if keys:
            cparam = Parameter.combine(
                upstream_parameter,
                _PARAMETER_SUBKEY_BLOCKER,
                immediate_parameter,
            )
            cparam = Parameter.combine(
                cparam,
                Parameter(
                    name=_resolve_parameter_name(
                        upstream_parameter.name,  # pyright: ignore
                        immediate_parameter.name or (cparam.name_transform(keys[-1]),),  # pyright: ignore
                    )
                ),
            )
        else:
            cparam = Parameter.combine(
                upstream_parameter,
                immediate_parameter,
            )
            if not cparam.name:
                # This is directly on iparam; derive default name from it.
                if iparam.kind in (iparam.POSITIONAL_ONLY, iparam.VAR_POSITIONAL):
                    # Name is only used for help-string
                    cparam = Parameter.combine(cparam, Parameter(name=(iparam.name.upper(),)))
                elif iparam.kind is iparam.VAR_KEYWORD:
                    cparam = Parameter.combine(cparam, Parameter(name=("--[KEYWORD]",)))
                else:
                    # cparam.name_transform cannot be None due to:
                    #     attrs.converters.default_if_none(default_name_transform)
                    assert cparam.name_transform is not None
                    cparam = Parameter.combine(cparam, Parameter(name=["--" + cparam.name_transform(iparam.name)]))

        if iparam.kind in (iparam.KEYWORD_ONLY, iparam.VAR_KEYWORD):
            positional_index = None

        argument = Argument(iparam=iparam, cparam=cparam, keys=keys, hint=hint)
        if argument._assignable and positional_index is not None:
            argument.index = positional_index
            positional_index += 1

        out.append(argument)
        if argument._accepts_keywords:
            docstring_lookup = _extract_docstring_help(argument.hint) if parse_docstring else {}
            for field_name, field_info in argument._lookup.items():
                if field_info.kw_only:
                    positional_index = None

                subkey_argument_collection = cls._from_type(
                    iparam,
                    field_info.hint,
                    keys + (field_name,),
                    cparam,
                    Parameter(required=bool(cparam.required) & field_info.required),
                    docstring_lookup.get(field_name, _PARAMETER_EMPTY_HELP),
                    group_lookup=group_lookup,
                    group_arguments=group_arguments,
                    group_parameters=group_parameters,
                    parse_docstring=parse_docstring,
                    positional_index=positional_index,
                    _resolve_groups=_resolve_groups,
                )
                if subkey_argument_collection:
                    argument.children.append(subkey_argument_collection[0])
                    out.extend(subkey_argument_collection)

                    if positional_index is not None:
                        positional_index = subkey_argument_collection._max_index
                        if positional_index is not None:
                            positional_index += 1

        return out

    @classmethod
    def from_iparam(
        cls,
        iparam: inspect.Parameter,
        *default_parameters: Optional[Parameter],
        group_lookup: Optional[dict[str, Group]] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        positional_index: Optional[int] = None,
        parse_docstring: bool = True,
        _resolve_groups: bool = True,
    ):
        # The responsibility of this function is to extract out the root type
        # and annotation. The rest of the functionality goes into _from_type.
        if group_lookup is None:
            group_lookup = {}
        if group_arguments is None:
            group_arguments = Group.create_default_arguments()
        if group_parameters is None:
            group_parameters = Group.create_default_parameters()
        group_lookup[group_arguments.name] = group_arguments
        group_lookup[group_parameters.name] = group_parameters

        hint = _iparam_get_hint(iparam)

        return cls._from_type(
            iparam,
            hint,
            (),
            _PARAMETER_EMPTY_HELP,
            Parameter(
                required=iparam.default is iparam.empty
                and iparam.kind != iparam.VAR_KEYWORD
                and iparam.kind != iparam.VAR_POSITIONAL
            ),
            *default_parameters,
            group_lookup=group_lookup,
            group_arguments=group_arguments,
            group_parameters=group_parameters,
            positional_index=positional_index,
            parse_docstring=parse_docstring,
            _resolve_groups=_resolve_groups,
        )

    @classmethod
    def from_callable(
        cls,
        func: Callable,
        *default_parameters: Optional[Parameter],
        group_lookup: Optional[dict[str, Group]] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        parse_docstring: bool = True,
        _resolve_groups: bool = True,
    ):
        import cyclopts.utils

        if group_arguments is None:
            group_arguments = Group.create_default_arguments()
        if group_parameters is None:
            group_parameters = Group.create_default_parameters()

        if _resolve_groups:
            group_lookup = {
                group.name: group
                for group in _resolve_groups_from_callable(
                    func,
                    *default_parameters,
                    group_arguments=group_arguments,
                    group_parameters=group_parameters,
                )
            }

        docstring_lookup = _extract_docstring_help(func) if parse_docstring else {}
        out = cls()
        positional_index = 0
        for iparam in cyclopts.utils.signature(func).parameters.values():
            iparam_argument_collection = cls.from_iparam(
                iparam,
                _PARAMETER_EMPTY_HELP,
                *default_parameters,
                docstring_lookup.get(iparam.name),
                group_lookup=group_lookup,
                group_arguments=group_arguments,
                group_parameters=group_parameters,
                positional_index=positional_index,
                parse_docstring=parse_docstring,
                _resolve_groups=_resolve_groups,
            )
            if positional_index is not None:
                positional_index = iparam_argument_collection._max_index
                if positional_index is not None:
                    positional_index += 1
            out.extend(iparam_argument_collection)

        out.groups = []
        for argument in out:
            for group in argument.cparam.group:
                if group not in out.groups:
                    out.groups.append(group)
        return out

    @property
    def root_arguments(self):
        for argument in self:
            if not argument.keys:
                yield argument

    @property
    def _max_index(self) -> Optional[int]:
        return max((x.index for x in self if x.index is not None), default=None)

    def iparam_to_value(self) -> ParameterDict:
        """Mapping iparam to converted values.

        Assumes that ``self.convert`` has already been called.
        """
        out = ParameterDict()
        for argument in self.root_arguments:
            if argument.value is not argument.UNSET:
                out[argument.iparam] = argument.value
        return out

    def filter_by(
        self,
        *,
        group: Optional[Group] = None,
        kind=None,
        has_tokens: Optional[bool] = None,
        has_tree_tokens: Optional[bool] = None,
        keys_prefix: Optional[tuple[str, ...]] = None,
        show: Optional[bool] = None,
        value_set: Optional[bool] = None,
    ) -> "ArgumentCollection":
        """Filter the ArgumentCollection by something.

        All non-``None`` arguments will be applied.

        Parameter
        ---------
        group: Optional[Group]
        kind: Optional[inspect._ParameterKind]
            The ``kind`` of ``inspect.Parameter``.
        has_tokens: Optional[bool]
            Has parsed tokens.
        has_tree_tokens: Optional[bool]
            Argument and/or it's children have parsed tokens.
        show: Optional[bool]
            The Argument is intended to be show on the help page.
        value_set: Optional[bool]
            The converted value is set.
        """
        ac = self.copy()
        cls = type(self)

        if group is not None:
            ac = cls(x for x in ac if group in x.cparam.group)
        if kind is not None:
            ac = cls(x for x in ac if x.iparam.kind == kind)
        if has_tokens is not None:
            ac = cls(x for x in ac if not (bool(x.tokens) ^ bool(has_tokens)))
        if has_tree_tokens is not None:
            ac = cls(x for x in ac if not (bool(x.tokens) ^ bool(has_tree_tokens)))
        if keys_prefix is not None:
            ac = cls(x for x in ac if x.keys[: len(keys_prefix)] == keys_prefix)
        if show is not None:
            ac = cls(x for x in ac if not (x.cparam.show ^ bool(show)))
        if value_set is not None:
            ac = cls(x for x in ac if ((x.value is x.UNSET) ^ bool(value_set)))

        return ac


@define(kw_only=True)
class Argument:
    """Tracks the lifespan of a parsed argument.

    An argument is defined as:

        * the finest unit that can have a Parameter assigned to it.
        * a leaf in the iparam/key tree.
        * anything that would have its own entry in the --help page.
        * If a type hint has a ``dict`` in it, it's a leaf.
        * Individual tuple elements do NOT get their own Argument.

    e.g.

    ... code-block:: python

        def foo(bar: Annotated[int, Parameter(help="bar's help")]):
            ...

    ... code-block:: python

        from attrs import define

        @define
        class Foo:
            bar: Annotated[int, Parameter(help="bar's help")]  # This gets an Argument
            baz: Annotated[int, Parameter(help="baz's help")]  # This gets an Argument

        def foo(fizz: Annotated[Foo, Parameter(help="bar's help")]):  # This gets an Argument
            ...

    """

    class UNSET(Sentinel):
        """No data was provided to derive a python value from.

        Or, :meth:`Argument.convert` has not yet been called.
        """

    # List of tokens parsed from various sources
    # If tokens is empty, then no tokens have been parsed for this argument.
    tokens: list[Token] = field(factory=list)

    # Multiple ``Argument`` may be associated with a single iparam.
    # However, each ``Argument`` must have a unique iparam/keys combo
    iparam: inspect.Parameter = field(default=None)

    # Fully resolved Parameter
    # Resolved parameter should have a fully resolved Parameter.name
    cparam: Parameter = field(factory=Parameter)

    # The type for this leaf; may be different from ``iparam.annotation``
    # because this could be a subkey of iparam.
    hint: Any = field(default=str, converter=resolve)

    # Associated positional index for iparam.
    index: Optional[int] = field(default=None)

    # **Python** Keys into iparam that lead to this leaf.
    # Note: that self.cparam.name and self.keys can naively disagree!
    # For example, a cparam.name=="--foo.bar.baz" could be aliased to "--fizz".
    # "keys" may be an empty tuple.
    # This should be populated based on type-hints, not ``Parameter.name``
    keys: tuple[str, ...] = field(default=())

    # Converted value; may be stale.
    _value: Any = field(alias="value", default=UNSET)

    _accepts_keywords: bool = field(default=False, init=False, repr=False)

    _default: Any = field(default=None, init=False, repr=False)
    _lookup: dict[str, _FieldInfo] = field(factory=dict, init=False, repr=False)

    # Can assign values directly to this argument
    # If _assignable is ``False``, it's a non-visible node used only for the conversion process.
    _assignable: bool = field(default=False, init=False, repr=False)
    children: "ArgumentCollection" = field(factory=ArgumentCollection, init=False, repr=False)
    _marked_converted: bool = field(default=False, init=False, repr=False)  # for mark & sweep algos
    _mark_converted_override: bool = field(default=False, init=False, repr=False)

    # Validator to be called based on builtin type support.
    _missing_keys_checker: Optional[Callable] = field(default=None, init=False, repr=False)

    _internal_converter: Optional[Callable] = field(default=None, init=False, repr=False)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if self._marked:
            self._mark_converted_override = True
        self._marked = True
        self._value = val

    @property
    def _marked(self):
        """If ``True``, then this node in the tree has already been converted and ``value`` has been populated."""
        return self._marked_converted | self._mark_converted_override

    @_marked.setter
    def _marked(self, value: bool):
        self._marked_converted = value

    def __attrs_post_init__(self):
        # By definition, self.hint is Not AnnotatedType
        hint = resolve(self.hint)
        hints = get_args(hint) if is_union(hint) else (hint,)

        if self.cparam.accepts_keys is False:  # ``None`` means to infer.
            self._assignable = True
            return

        for hint in hints:
            # accepts_keys is either ``None`` or ``True`` here

            # This could be annotated...
            origin = get_origin(hint)
            # TODO: need to resolve Annotation and handle cyclopts.Parameters; or do we?
            hint_origin = {hint, origin}

            # Classes that ALWAYS takes keywords (accepts_keys=None)
            if dict in hint_origin:
                self._assignable = True
                self._accepts_keywords = True
                key_type, val_type = str, str
                args = get_args(hint)
                with suppress(IndexError):
                    key_type = args[0]
                    val_type = args[1]
                if key_type is not str:
                    raise TypeError('Dictionary type annotations must have "str" keys.')
                self._default = val_type
            elif is_typeddict(hint):
                self._missing_keys_checker = _missing_keys_factory(_typed_dict_field_info)
                self._accepts_keywords = True
                self._lookup.update(_typed_dict_field_info(hint))
            elif is_dataclass(hint):  # Typical usecase of a dataclass will have more than 1 field.
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_info)
                self._accepts_keywords = True
                self._lookup.update(_generic_class_field_info(hint))
            elif is_namedtuple(hint):
                # collections.namedtuple does not have type hints, assume "str" for everything.
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_info)
                self._accepts_keywords = True
                if not hasattr(hint, "__annotations__"):
                    raise ValueError("Cyclopts cannot handle collections.namedtuple in python <3.10.")
                self._lookup.update(
                    {
                        name: _FieldInfo(hint.__annotations__.get(name, str), name in hint._field_defaults, False)
                        for name in hint._fields
                    }
                )
            elif is_attrs(hint):
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_info)
                self._accepts_keywords = True
                self._lookup.update(_generic_class_field_info(hint))
            elif is_pydantic(hint):
                self._missing_keys_checker = _missing_keys_factory(_pydantic_field_info)
                self._accepts_keywords = True
                # pydantic's __init__ signature doesn't accurately reflect its requirements.
                # so we cannot use _generic_class_required_optional(...)
                self._lookup.update(_pydantic_field_info(hint))
            elif self.cparam.accepts_keys is None:
                # Typical builtin hint
                self._assignable = True
                continue

            if self.cparam.accepts_keys is None:
                continue
            # Only explicit ``self.cparam.accepts_keys == True`` from here on

            # Classes that MAY take keywords (accepts_keys=True)
            # They must be explicitly specified ``accepts_keys=True`` because otherwise
            # providing a single positional argument is what we want.
            self._accepts_keywords = True
            self._missing_keys_checker = _missing_keys_factory(_generic_class_field_info)
            for i, iparam in enumerate(inspect.signature(hint.__init__).parameters.values()):
                if i == 0 and iparam.name == "self":
                    continue
                if iparam.kind is iparam.VAR_KEYWORD:
                    self._default = iparam.annotation
                else:
                    self._lookup[iparam.name] = _FieldInfo(
                        iparam.annotation,
                        iparam.default is iparam.empty
                        and iparam.kind != iparam.VAR_KEYWORD
                        and iparam.kind != iparam.VAR_POSITIONAL,
                    )

    @property
    def accepts_arbitrary_keywords(self) -> bool:
        if not self._assignable:
            return False
        args = get_args(self.hint) if is_union(self.hint) else (self.hint,)
        return any(dict in (arg, get_origin(arg)) for arg in args)

    def type_hint_for_key(self, key: str):
        try:
            return self._lookup[key].hint
        except KeyError:
            if self._default is None:
                raise
            return self._default

    def match(
        self,
        term: Union[str, int],
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> tuple[tuple[str, ...], Any]:
        """Match a name search-term, or a positional integer index.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
        Any
            Implicit value.
        """
        if not self._assignable:
            raise ValueError
        return (
            self._match_index(term)
            if isinstance(term, int)
            else self._match_name(term, transform=transform, delimiter=delimiter)
        )

    def _match_name(
        self,
        term: str,
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> tuple[tuple[str, ...], Any]:
        """Check how well this argument matches a token keyword identifier.

        Parameter
        ---------
        term: str
            Something like "--foo"
        transform: Callable
            Function that converts the cyclopts Parameter name(s) into
            something that should be compared against ``term``.

        Raises
        ------
        ValueError
            If no match found.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
        Any
            Implicit value.
        """
        if self.iparam.kind is self.iparam.VAR_KEYWORD:
            # TODO: apply cparam.name_transform to keys here?
            return tuple(term.lstrip("-").split(delimiter)), None

        assert self.cparam.name
        for name in self.cparam.name:
            if transform:
                name = transform(name)
            if term.startswith(name):
                trailing = term[len(name) :]
                implicit_value = True if self.hint is bool else None
                if trailing:
                    if trailing[0] == delimiter:
                        trailing = trailing[1:]
                        break
                    # Otherwise, it's not an actual match.
                else:
                    # exact match
                    return (), implicit_value
        else:
            # No positive-name matches found.
            for name in self.negatives:
                if transform:
                    name = transform(name)
                if term.startswith(name):
                    trailing = term[len(name) :]
                    implicit_value = (get_origin(self.hint) or self.hint)()
                    if trailing:
                        if trailing[0] == delimiter:
                            trailing = trailing[1:]
                            break
                        # Otherwise, it's not an actual match.
                    else:
                        # exact match
                        return (), implicit_value
            else:
                # No negative-name matches found.
                raise ValueError

        if not self.accepts_arbitrary_keywords:
            # Still not an actual match.
            raise ValueError

        # TODO: apply cparam.name_transform to keys here?
        return tuple(trailing.split(delimiter)), implicit_value

    def _match_index(self, index: int) -> tuple[tuple[str, ...], Any]:
        if self.index is None or self.iparam in (self.iparam.KEYWORD_ONLY, self.iparam.VAR_KEYWORD):
            raise ValueError
        elif self.iparam.kind is self.iparam.VAR_POSITIONAL:
            if index < self.index:
                raise ValueError
        elif index != self.index:
            raise ValueError
        return (), None

    def append(self, token: Token):
        if not self._assignable:
            raise ValueError
        if (
            any((x.keys, x.index) == (token.keys, token.index) for x in self.tokens)
            and not self.token_count(token.keys)[1]
        ):
            raise RepeatArgumentError(token=token)
        if self.tokens:
            if bool(token.keys) ^ any(x.keys for x in self.tokens):
                raise MixedArgumentError(argument=self)
        self.tokens.append(token)

    def values(self) -> Iterator[str]:
        for token in self.tokens:
            yield token.value

    @property
    def n_tree_tokens(self) -> int:
        return len(self.tokens) + sum(child.n_tree_tokens for child in self.children)

    def _convert(self, converter=None):
        if converter is None:
            converter = self.cparam.converter
        if self._assignable:
            positional, keyword = [], {}
            for token in self.tokens:
                if token.implicit_value is not None:
                    assert len(self.tokens) == 1
                    return token.implicit_value

                if token.keys:
                    lookup = keyword
                    for key in token.keys[:-1]:
                        lookup = lookup.setdefault(key, {})
                    lookup.setdefault(token.keys[-1], []).append(token.value)
                else:
                    positional.append(token.value)

                if positional and keyword:
                    # This should never happen due to checks in ``Argument.append``
                    raise MixedArgumentError(argument=self)

            if positional:
                if self.iparam and self.iparam.kind is self.iparam.VAR_POSITIONAL:
                    # Apply converter to individual values
                    out = tuple(converter(get_args(self.hint)[0], (value,)) for value in positional)
                else:
                    out = converter(self.hint, tuple(positional))
            elif keyword:
                if self.iparam and self.iparam.kind is self.iparam.VAR_KEYWORD and not self.keys:
                    # Apply converter to individual values
                    out = {key: converter(get_args(self.hint)[1], value) for key, value in keyword.items()}
                else:
                    out = converter(self.hint, keyword)
            elif self.cparam.required:
                raise MissingArgumentError(argument=self)
            else:  # no tokens
                return self.UNSET
        else:  # A dictionary-like structure.
            data = {}
            if is_pydantic(self.hint):
                # Don't convert any subkeys, let pydantic handle them.
                converter = partial(convert, converter=_identity_converter, name_transform=self.cparam.name_transform)
            for child in self.children:
                assert len(child.keys) == (len(self.keys) + 1)
                if child.n_tree_tokens:
                    data[child.keys[-1]] = child.convert_and_validate(converter=converter)

            if self._missing_keys_checker and (self.cparam.required or data):
                if missing_keys := self._missing_keys_checker(self, data):
                    # Report the first missing argument.
                    missing_key = sorted(missing_keys)[0]
                    missing_argument = self.children.filter_by(
                        keys_prefix=self.keys + (missing_key,),
                    )[0]
                    raise MissingArgumentError(argument=missing_argument)

            if data:
                out = self.hint(**data)
            elif self.cparam.required:
                raise MissingArgumentError(argument=self)
            else:
                out = self.UNSET

        return out

    def convert(self, converter=None):
        if not self._marked:
            try:
                self.value = self._convert(converter=converter)
            except CoercionError as e:
                if e.argument is None:
                    e.argument = self
                raise
        return self.value

    def validate(self, value):
        assert isinstance(self.cparam.validator, tuple)

        try:
            if not self.keys and self.iparam and self.iparam.kind is self.iparam.VAR_KEYWORD:
                hint = get_args(self.hint)[1]
                for validator in self.cparam.validator:
                    for val in value.values():
                        validator(hint, val)
            elif self.iparam and self.iparam.kind is self.iparam.VAR_POSITIONAL:
                hint = get_args(self.hint)[0]
                for validator in self.cparam.validator:
                    for val in value:
                        validator(hint, val)
            else:
                for validator in self.cparam.validator:
                    validator(self.hint, value)
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(value=e.args[0] if e.args else "", argument=self) from e

    def convert_and_validate(self, converter=None):
        val = self.convert(converter=converter)
        if val is not self.UNSET:
            self.validate(val)
        return val

    def token_count(self, keys: tuple[str, ...] = ()):
        if len(keys) > 1:
            hint = self._default
        elif len(keys) == 1:
            hint = self.type_hint_for_key(keys[0])
        else:
            hint = self.hint
        tokens_per_element, consume_all = token_count(hint)
        return tokens_per_element, consume_all

    @property
    def negatives(self):
        return self.cparam.get_negatives(self.hint)

    @property
    def name(self) -> str:
        return self.names[0]

    @property
    def names(self) -> tuple[str, ...]:
        assert isinstance(self.cparam.name, tuple)
        return tuple(itertools.chain(self.cparam.name, self.negatives))

    def env_var_split(self, value: str, delimiter: Optional[str] = None) -> list[str]:
        return self.cparam.env_var_split(self.hint, value, delimiter=delimiter)

    @property
    def show(self) -> bool:
        return self._assignable and self.cparam.show


def _resolve_groups_from_callable(
    func: Callable,
    *default_parameters: Optional[Parameter],
    group_arguments: Optional[Group] = None,
    group_parameters: Optional[Group] = None,
) -> list[Group]:
    argument_collection = ArgumentCollection.from_callable(
        func,
        *default_parameters,
        group_arguments=group_arguments,
        group_parameters=group_parameters,
        parse_docstring=False,
        _resolve_groups=False,
    )

    resolved_groups = []
    if group_arguments is not None:
        resolved_groups.append(group_arguments)
    if group_parameters is not None:
        resolved_groups.append(group_parameters)

    for argument in argument_collection:
        for group in argument.cparam.group:  # pyright: ignore
            if not isinstance(group, Group):
                continue

            # Ensure a different, but same-named group doesn't already exist
            if any(group is not x and x.name == group.name for x in resolved_groups):
                raise ValueError("Cannot register 2 distinct Group objects with same name.")

            if group.default_parameter is not None and group.default_parameter.group:
                # This shouldn't be possible due to ``Group`` internal checks.
                raise ValueError("Group.default_parameter cannot have a specified group.")  # pragma: no cover

            try:
                next(x for x in resolved_groups if x.name == group.name)
            except StopIteration:
                resolved_groups.append(group)

    for argument in argument_collection:
        for group in argument.cparam.group:  # pyright: ignore
            if not isinstance(group, str):
                continue
            try:
                next(x for x in resolved_groups if x.name == group)
            except StopIteration:
                resolved_groups.append(Group(group))

    return resolved_groups


def _extract_docstring_help(f: Callable) -> dict[str, Parameter]:
    from docstring_parser import parse_from_object

    try:
        return {dparam.arg_name: Parameter(help=dparam.description) for dparam in parse_from_object(f).params}
    except TypeError:
        # Type hints like ``dict[str, str]`` trigger this.
        return {}


def _resolve_parameter_name(*argss: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve parameter names by combining and formatting multiple tuples of strings.

    Parameters
    ----------
    *argss
        Each tuple represents a group of parameter name components.

    Returns
    -------
    tuple[str, ...]
        A tuple of resolved parameter names.
    """
    if len(argss) == 0:
        return ()
    elif len(argss) == 1:
        return argss[0]

    # Combine the first 2, and do a recursive call.
    out = []
    for a1 in argss[0]:
        if a1.endswith("*"):
            a1 = a1[:-1]
        elif not a1.startswith("-"):
            continue

        if not a1:
            a1 = "--"
        elif not a1.endswith("."):
            a1 += "."

        for a2 in argss[1]:
            if a2.startswith("-"):
                out.append(a2)
            else:
                out.append(a1 + a2)

    return _resolve_parameter_name(tuple(out), *argss[2:])
