import inspect
import itertools
import sys
from contextlib import suppress
from functools import partial
from typing import Any, Callable, Literal, Optional, Sequence, Union, get_args, get_origin

from attrs import define, field

from cyclopts._convert import (
    ITERABLE_TYPES,
    convert,
    token_count,
)
from cyclopts.annotations import (
    contains_hint,
    is_attrs,
    is_dataclass,
    is_namedtuple,
    is_nonetype,
    is_pydantic,
    is_typeddict,
    is_union,
    resolve,
    resolve_annotated,
    resolve_optional,
)
from cyclopts.exceptions import (
    CoercionError,
    CycloptsError,
    MissingArgumentError,
    MixedArgumentError,
    RepeatArgumentError,
    ValidationError,
)
from cyclopts.field_info import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    FieldInfo,
    _attrs_field_infos,
    _generic_class_field_infos,
    _pydantic_field_infos,
    _typed_dict_field_infos,
    get_field_infos,
    signature_parameters,
)
from cyclopts.group import Group
from cyclopts.parameter import ITERATIVE_BOOL_IMPLICIT_VALUE, Parameter, get_parameters
from cyclopts.token import Token
from cyclopts.utils import UNSET, grouper, is_builtin

# parameter subkeys should not inherit these parameter values from their parent.
_PARAMETER_SUBKEY_BLOCKER = Parameter(
    name=None,
    converter=None,  # pyright: ignore
    validator=None,
    accepts_keys=None,
    consume_multiple=None,
    env_var=None,
)

_kind_parent_child_reassignment = {
    (POSITIONAL_OR_KEYWORD, POSITIONAL_OR_KEYWORD): POSITIONAL_OR_KEYWORD,
    (POSITIONAL_OR_KEYWORD, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY): KEYWORD_ONLY,
    (POSITIONAL_OR_KEYWORD, VAR_POSITIONAL): VAR_POSITIONAL,
    (POSITIONAL_OR_KEYWORD, VAR_KEYWORD): VAR_KEYWORD,
    (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD): POSITIONAL_ONLY,
    (POSITIONAL_ONLY, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (POSITIONAL_ONLY, KEYWORD_ONLY): None,
    (POSITIONAL_ONLY, VAR_POSITIONAL): VAR_POSITIONAL,
    (POSITIONAL_ONLY, VAR_KEYWORD): None,
    (KEYWORD_ONLY, POSITIONAL_OR_KEYWORD): KEYWORD_ONLY,
    (KEYWORD_ONLY, POSITIONAL_ONLY): None,
    (KEYWORD_ONLY, KEYWORD_ONLY): KEYWORD_ONLY,
    (KEYWORD_ONLY, VAR_POSITIONAL): None,
    (KEYWORD_ONLY, VAR_KEYWORD): VAR_KEYWORD,
    (VAR_POSITIONAL, POSITIONAL_OR_KEYWORD): POSITIONAL_ONLY,
    (VAR_POSITIONAL, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (VAR_POSITIONAL, KEYWORD_ONLY): None,
    (VAR_POSITIONAL, VAR_POSITIONAL): VAR_POSITIONAL,
    (VAR_POSITIONAL, VAR_KEYWORD): None,
    (VAR_KEYWORD, POSITIONAL_OR_KEYWORD): KEYWORD_ONLY,
    (VAR_KEYWORD, POSITIONAL_ONLY): None,
    (VAR_KEYWORD, KEYWORD_ONLY): KEYWORD_ONLY,
    (VAR_KEYWORD, VAR_POSITIONAL): None,
    (VAR_KEYWORD, VAR_KEYWORD): VAR_KEYWORD,
}


def _startswith(string, prefix):
    def normalize(s):
        return s.replace("_", "-")

    return normalize(string).startswith(normalize(prefix))


def _missing_keys_factory(get_field_info: Callable[[Any], dict[str, FieldInfo]]):
    def inner(argument: "Argument", data: dict[str, Any]) -> list[str]:
        provided_keys = set(data)
        field_info = get_field_info(argument.hint)
        return [k for k, v in field_info.items() if (v.required and k not in provided_keys)]

    return inner


def _identity_converter(type_, token):
    return token


def _get_annotated_discriminator(annotation):
    for meta in get_args(annotation)[1:]:
        try:
            return meta.discriminator
        except AttributeError:
            pass
    return None


class ArgumentCollection(list["Argument"]):
    """A list-like container for :class:`Argument`."""

    def __init__(self, *args):
        super().__init__(*args)

    def copy(self) -> "ArgumentCollection":
        """Returns a shallow copy of the :class:`ArgumentCollection`."""
        return type(self)(self)

    def match(
        self,
        term: Union[str, int],
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> tuple["Argument", tuple[str, ...], Any]:
        """Matches CLI keyword or index to their :class:`Argument`.

        Parameters
        ----------
        term: str | int
            One of:

            * :obj:`str` keyword like ``"--foo"`` or ``"-f"`` or ``"--foo.bar.baz"``.

            * :obj:`int` global positional index.

        Raises
        ------
        ValueError
            If the provided ``term`` doesn't match.

        Returns
        -------
        Argument
            Matched :class:`Argument`.
        Tuple[str, ...]
            Python keys into Argument. Non-empty iff Argument accepts keys.
        Any
            Implicit value (if a flag). :obj:`~.UNSET` otherwise.
        """
        best_match_argument, best_match_keys, best_implicit_value = None, None, UNSET
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

    def _convert(self):
        """Convert and validate all elements."""
        self._set_marks(False)
        for argument in sorted(self, key=lambda x: x.keys):
            if argument._marked:
                continue
            argument.convert_and_validate()

    @classmethod
    def _from_type(
        cls,
        field_info: FieldInfo,
        keys: tuple[str, ...],
        *default_parameters: Optional[Parameter],
        group_lookup: dict[str, Group],
        group_arguments: Group,
        group_parameters: Group,
        parse_docstring: bool = True,
        docstring_lookup: Optional[dict[tuple[str, ...], Parameter]] = None,
        positional_index: Optional[int] = None,
        _resolve_groups: bool = True,
    ):
        out = cls()  # groups=list(group_lookup.values()))

        if docstring_lookup is None:
            docstring_lookup = {}

        cyclopts_parameters_no_group = []

        hint = field_info.hint
        hint, hint_parameters = get_parameters(hint)
        cyclopts_parameters_no_group.extend(hint_parameters)

        if not keys:  # root hint annotation
            if field_info.kind is field_info.VAR_KEYWORD:
                hint = dict[str, hint]
            elif field_info.kind is field_info.VAR_POSITIONAL:
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
                if field_info.kind in (field_info.POSITIONAL_ONLY, field_info.VAR_POSITIONAL)
                else Parameter(group=group_parameters)
            ),
            *default_parameters,
        )
        immediate_parameter = Parameter.combine(*cyclopts_parameters)

        # We do NOT want to skip parse=False arguments here.
        # This makes it easier to assemble ignored arguments downstream.

        # resolve/derive the parameter name
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
                        (immediate_parameter.name or tuple(cparam.name_transform(x) for x in field_info.names))
                        + cparam.alias,  # pyright: ignore
                    )
                ),
            )
        else:
            # This is directly on iparam
            cparam = Parameter.combine(
                upstream_parameter,
                immediate_parameter,
            )
            assert isinstance(cparam.alias, tuple)
            if cparam.name:
                if field_info.is_keyword:
                    assert isinstance(cparam.name, tuple)
                    cparam = Parameter.combine(
                        cparam, Parameter(name=_resolve_parameter_name(cparam.name + cparam.alias))
                    )
            else:
                if field_info.kind in (field_info.POSITIONAL_ONLY, field_info.VAR_POSITIONAL):
                    # Name is only used for help-string
                    cparam = Parameter.combine(cparam, Parameter(name=(name.upper() for name in field_info.names)))
                elif field_info.kind is field_info.VAR_KEYWORD:
                    cparam = Parameter.combine(cparam, Parameter(name=("--[KEYWORD]",)))
                else:
                    # cparam.name_transform cannot be None due to:
                    #     attrs.converters.default_if_none(default_name_transform)
                    assert cparam.name_transform is not None
                    cparam = Parameter.combine(
                        cparam,
                        Parameter(
                            name=tuple("--" + cparam.name_transform(name) for name in field_info.names)
                            + _resolve_parameter_name(cparam.alias)
                        ),
                    )

        if field_info.is_keyword_only:
            positional_index = None

        argument = Argument(field_info=field_info, parameter=cparam, keys=keys, hint=hint)
        if not argument._accepts_keywords and positional_index is not None:
            argument.index = positional_index
            positional_index += 1

        out.append(argument)
        if argument._accepts_keywords:
            hint_docstring_lookup = _extract_docstring_help(argument.hint) if parse_docstring else {}
            hint_docstring_lookup.update(docstring_lookup)

            for sub_field_name, sub_field_info in argument._lookup.items():
                updated_kind = _kind_parent_child_reassignment[(argument.field_info.kind, sub_field_info.kind)]  # pyright: ignore
                if updated_kind is None:
                    continue

                sub_field_info.kind = updated_kind

                if sub_field_info.is_keyword_only:
                    positional_index = None

                subkey_docstring_lookup = {
                    k[1:]: v for k, v in hint_docstring_lookup.items() if k[0] == sub_field_name and len(k) > 1
                }

                subkey_argument_collection = cls._from_type(
                    sub_field_info,
                    keys + (sub_field_name,),
                    cparam,
                    (
                        Parameter(help=sub_field_info.help)
                        if sub_field_info.help
                        else hint_docstring_lookup.get((sub_field_name,))
                    ),
                    Parameter(required=argument.required & sub_field_info.required),
                    group_lookup=group_lookup,
                    group_arguments=group_arguments,
                    group_parameters=group_parameters,
                    parse_docstring=parse_docstring,
                    docstring_lookup=subkey_docstring_lookup,
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
    def _from_callable(
        cls,
        func: Callable,
        *default_parameters: Optional[Parameter],
        group_lookup: Optional[dict[str, Group]] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        parse_docstring: bool = True,
        _resolve_groups: bool = True,
    ):
        out = cls()

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
        else:
            group_lookup = {}

        docstring_lookup = _extract_docstring_help(func) if parse_docstring else {}
        positional_index = 0
        for field_info in signature_parameters(func).values():
            if parse_docstring:
                subkey_docstring_lookup = {
                    k[1:]: v for k, v in docstring_lookup.items() if k[0] == field_info.name and len(k) > 1
                }
            else:
                subkey_docstring_lookup = None
            iparam_argument_collection = cls._from_type(
                field_info,
                (),
                *default_parameters,
                Parameter(help=field_info.help) if field_info.help else docstring_lookup.get((field_info.name,)),
                group_lookup=group_lookup,
                group_arguments=group_arguments,
                group_parameters=group_parameters,
                positional_index=positional_index,
                parse_docstring=parse_docstring,
                docstring_lookup=subkey_docstring_lookup,
                _resolve_groups=_resolve_groups,
            )
            if positional_index is not None:
                positional_index = iparam_argument_collection._max_index
                if positional_index is not None:
                    positional_index += 1
            out.extend(iparam_argument_collection)

        return out

    @property
    def groups(self):
        groups = []
        for argument in self:
            assert isinstance(argument.parameter.group, tuple)
            for group in argument.parameter.group:
                if group not in groups:
                    groups.append(group)
        return groups

    @property
    def _root_arguments(self):
        for argument in self:
            if not argument.keys:
                yield argument

    @property
    def _max_index(self) -> Optional[int]:
        return max((x.index for x in self if x.index is not None), default=None)

    def filter_by(
        self,
        *,
        group: Optional[Group] = None,
        has_tokens: Optional[bool] = None,
        has_tree_tokens: Optional[bool] = None,
        keys_prefix: Optional[tuple[str, ...]] = None,
        kind: Optional[inspect._ParameterKind] = None,
        parse: Optional[bool] = None,
        show: Optional[bool] = None,
        value_set: Optional[bool] = None,
    ) -> "ArgumentCollection":
        """Filter the :class:`ArgumentCollection`.

        All non-:obj:`None` filters will be applied.

        Parameters
        ----------
        group: Optional[Group]
            The :class:`.Group` the arguments should be in.
        has_tokens: Optional[bool]
            Immediately has tokens (not including children).
        has_tree_tokens: Optional[bool]
            Argument and/or it's children have parsed tokens.
        kind: Optional[inspect._ParameterKind]
            The :attr:`~inspect.Parameter.kind` of the argument.
        parse: Optional[bool]
            If the argument is intended to be parsed or not.
        show: Optional[bool]
            The Argument is intended to be show on the help page.
        value_set: Optional[bool]
            The converted value is set.
        """
        ac = self.copy()
        cls = type(self)

        if group is not None:
            ac = cls(x for x in ac if group in x.parameter.group)  # pyright: ignore
        if kind is not None:
            ac = cls(x for x in ac if x.field_info.kind == kind)
        if has_tokens is not None:
            ac = cls(x for x in ac if not (bool(x.tokens) ^ bool(has_tokens)))
        if has_tree_tokens is not None:
            ac = cls(x for x in ac if not (bool(x.tokens) ^ bool(has_tree_tokens)))
        if keys_prefix is not None:
            ac = cls(x for x in ac if x.keys[: len(keys_prefix)] == keys_prefix)
        if show is not None:
            ac = cls(x for x in ac if not (x.show ^ bool(show)))
        if value_set is not None:
            ac = cls(x for x in ac if ((x.value is UNSET) ^ bool(value_set)))
        if parse is not None:
            ac = cls(x for x in ac if not (x.parameter.parse ^ parse))

        return ac


@define(kw_only=True)
class Argument:
    """Encapsulates functionality and additional contextual information for parsing a parameter.

    An argument is defined as anything that would have its own entry in the help page.
    """

    tokens: list[Token] = field(factory=list)
    """
    List of :class:`.Token` parsed from various sources.
    Do not directly mutate; see :meth:`append`.
    """

    field_info: FieldInfo = field(factory=FieldInfo)
    """
    Additional information about the parameter from surrounding python syntax.
    """

    parameter: Parameter = field(factory=Parameter)  # pyright: ignore
    """
    Fully resolved user-provided :class:`.Parameter`.
    """

    hint: Any = field(default=str, converter=resolve)
    """
    The type hint for this argument; may be different from :attr:`.FieldInfo.annotation`.
    """

    index: Optional[int] = field(default=None)
    """
    Associated python positional index for argument.
    If ``None``, then cannot be assigned positionally.
    """

    keys: tuple[str, ...] = field(default=())
    """
    **Python** keys that lead to this leaf.

    ``self.parameter.name`` and ``self.keys`` can naively disagree!
    For example, a ``self.parameter.name="--foo.bar.baz"`` could be aliased to "--fizz".
    The resulting ``self.keys`` would be ``("bar", "baz")``.

    This is populated based on type-hints and class-structure, not ``Parameter.name``.

    .. code-block:: python

        from cyclopts import App, Parameter
        from dataclasses import dataclass
        from typing import Annotated

        app = App()


        @dataclass
        class User:
            id: int
            name: Annotated[str, Parameter(name="--fullname")]


        @app.default
        def main(user: User):
            pass


        for argument in app.assemble_argument_collection():
            print(f"name: {argument.name:16} hint: {str(argument.hint):16} keys: {str(argument.keys)}")

    .. code-block:: bash

        $ my-script
        name: --user.id        hint: <class 'int'>    keys: ('id',)
        name: --fullname       hint: <class 'str'>    keys: ('name',)
    """

    # Converted value; may be stale.
    _value: Any = field(alias="value", default=UNSET)
    """
    Converted value from last :meth:`convert` call.
    This value may be stale if fields have changed since last :meth:`convert` call.
    :class:`.UNSET` if :meth:`convert` has not yet been called with tokens.
    """

    _accepts_keywords: bool = field(default=False, init=False, repr=False)

    _default: Any = field(default=None, init=False, repr=False)
    _lookup: dict[str, FieldInfo] = field(factory=dict, init=False, repr=False)

    children: "ArgumentCollection" = field(factory=ArgumentCollection, init=False, repr=False)
    """
    Collection of other :class:`Argument` that eventually culminate into the python variable represented by :attr:`field_info`.
    """

    _marked_converted: bool = field(default=False, init=False, repr=False)  # for mark & sweep algos
    _mark_converted_override: bool = field(default=False, init=False, repr=False)

    # Validator to be called based on builtin type support.
    _missing_keys_checker: Optional[Callable] = field(default=None, init=False, repr=False)

    _internal_converter: Optional[Callable] = field(default=None, init=False, repr=False)

    def __attrs_post_init__(self):
        # By definition, self.hint is Not AnnotatedType
        hint = resolve(self.hint)
        hints = get_args(hint) if is_union(hint) else (hint,)

        if not self.parameter.parse:
            return

        if self.parameter.accepts_keys is False:  # ``None`` means to infer.
            return

        for hint in hints:
            # ``self.parameter.accepts_keys`` is either ``None`` or ``True`` here
            origin = get_origin(hint)
            hint_origin = {hint, origin}

            # Classes that ALWAYS takes keywords (accepts_keys=None)
            field_infos = get_field_infos(hint)
            if dict in hint_origin:
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
                self._missing_keys_checker = _missing_keys_factory(_typed_dict_field_infos)
                self._accepts_keywords = True
                self._update_lookup(field_infos)
            elif is_dataclass(hint):  # Typical usecase of a dataclass will have more than 1 field.
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_infos)
                self._accepts_keywords = True
                self._update_lookup(field_infos)
            elif is_namedtuple(hint):
                # collections.namedtuple does not have type hints, assume "str" for everything.
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_infos)
                self._accepts_keywords = True
                if not hasattr(hint, "__annotations__"):
                    raise ValueError("Cyclopts cannot handle collections.namedtuple in python <3.10.")
                self._update_lookup(field_infos)
            elif is_attrs(hint):
                self._missing_keys_checker = _missing_keys_factory(_attrs_field_infos)
                self._accepts_keywords = True
                self._update_lookup(field_infos)
            elif is_pydantic(hint):
                self._missing_keys_checker = _missing_keys_factory(_pydantic_field_infos)
                self._accepts_keywords = True
                # pydantic's __init__ signature doesn't accurately reflect its requirements.
                # so we cannot use _generic_class_required_optional(...)
                self._update_lookup(field_infos)
            elif not is_builtin(hint) and field_infos:
                # Some classic user class.
                self._missing_keys_checker = _missing_keys_factory(_generic_class_field_infos)
                self._accepts_keywords = True
                self._update_lookup(field_infos)
            elif self.parameter.accepts_keys is None:
                # Typical builtin hint
                continue

            if self.parameter.accepts_keys is None:
                continue
            # Only explicit ``self.parameter.accepts_keys == True`` from here on

            # Classes that MAY take keywords (accepts_keys=True)
            # They must be explicitly specified ``accepts_keys=True`` because otherwise
            # providing a single positional argument is what we want.
            self._accepts_keywords = True
            self._missing_keys_checker = _missing_keys_factory(_generic_class_field_infos)
            for i, field_info in enumerate(signature_parameters(hint.__init__).values()):
                if i == 0 and field_info.name == "self":
                    continue
                if field_info.kind is field_info.VAR_KEYWORD:
                    self._default = field_info.annotation
                else:
                    self._update_lookup({field_info.name: field_info})

    def _update_lookup(self, field_infos: dict[str, FieldInfo]):
        discriminator = _get_annotated_discriminator(self.field_info.annotation)

        for key, field_info in field_infos.items():
            if existing_field_info := self._lookup.get(key):
                if existing_field_info == field_info:
                    pass
                elif discriminator and discriminator in field_info.names and discriminator in existing_field_info.names:
                    existing_field_info.annotation = Literal[existing_field_info.annotation, field_info.annotation]  # pyright: ignore
                    existing_field_info.default = FieldInfo.empty
                else:
                    raise NotImplementedError
            else:
                self._lookup[key] = field_info

    @property
    def value(self):
        """Converted value from last :meth:`convert` call.

        This value may be stale if fields have changed since last :meth:`convert` call.
        :class:`.UNSET` if :meth:`convert` has not yet been called with tokens.
        """
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

    @property
    def _accepts_arbitrary_keywords(self) -> bool:
        args = get_args(self.hint) if is_union(self.hint) else (self.hint,)
        return any(dict in (arg, get_origin(arg)) for arg in args)

    @property
    def show_default(self) -> Union[bool, Callable[[Any], str]]:
        """Show the default value on the help page."""
        if self.required:  # By definition, a required parameter cannot have a default.
            return False
        elif self.parameter.show_default is None:
            # Showing a default ``None`` value is typically not helpful to the end-user.
            return self.field_info.default not in (None, self.field_info.empty)
        elif (self.field_info.default is self.field_info.empty) or not self.parameter.show_default:
            return False
        else:
            return self.parameter.show_default

    @property
    def _use_pydantic_type_adapter(self) -> bool:
        return bool(
            is_pydantic(self.hint)
            or (
                is_union(self.hint)
                and (
                    any(is_pydantic(x) for x in get_args(self.hint))
                    or _get_annotated_discriminator(self.field_info.annotation)
                )
            )
        )

    def _type_hint_for_key(self, key: str):
        try:
            return self._lookup[key].annotation
        except KeyError:
            if self._default is None:
                raise
            return self._default

    def _should_attempt_json_dict(self, tokens: Optional[Sequence[Union[Token, str]]] = None) -> bool:
        """When parsing, should attempt to parse the token(s) as json dict data."""
        if tokens is None:
            tokens = self.tokens
        if not tokens:
            return False
        if not self._accepts_keywords:
            return False
        value = tokens[0].value if isinstance(tokens[0], Token) else tokens[0]
        if not value.strip().startswith("{"):
            return False
        if self.parameter.json_dict is not None:
            return self.parameter.json_dict
        if contains_hint(self.field_info.annotation, str):
            return False
        return True

    def _should_attempt_json_list(
        self, tokens: Union[Sequence[Union[Token, str]], Token, str, None] = None, keys: tuple[str, ...] = ()
    ) -> bool:
        """When parsing, should attempt to parse the token(s) as json list data."""
        if tokens is None:
            tokens = self.tokens
        if not tokens:
            return False
        _, consume_all = self.token_count(keys)
        if not consume_all:
            return False
        if isinstance(tokens, Token):
            value = tokens.value
        elif isinstance(tokens, str):
            value = tokens
        else:
            value = tokens[0].value if isinstance(tokens[0], Token) else tokens[0]
        if not value.strip().startswith("["):
            return False
        if self.parameter.json_list is not None:
            return self.parameter.json_list
        for arg in get_args(self.field_info.annotation) or (str,):
            if contains_hint(arg, str):
                return False
        return True

    def match(
        self,
        term: Union[str, int],
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> tuple[tuple[str, ...], Any]:
        """Match a name search-term, or a positional integer index.

        Raises
        ------
        ValueError
            If no match is found.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
        Any
            Implicit value.
            :obj:`~.UNSET` if no implicit value is applicable.
        """
        if not self.parameter.parse:
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

        Parameters
        ----------
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
        if self.field_info.kind is self.field_info.VAR_KEYWORD:
            return tuple(term.lstrip("-").split(delimiter)), UNSET

        trailing = term
        implicit_value = UNSET

        assert self.parameter.name
        for name in self.parameter.name:
            if transform:
                name = transform(name)
            if _startswith(term, name):
                trailing = term[len(name) :]
                implicit_value = True if self.hint is bool or self.hint in ITERATIVE_BOOL_IMPLICIT_VALUE else UNSET
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
            hint = resolve_annotated(self.field_info.annotation)
            if is_union(hint):
                hints = get_args(hint)
            else:
                hints = (hint,)
            for hint in hints:
                hint = resolve_annotated(hint)
                double_break = False
                for name in self.parameter.get_negatives(hint):
                    if transform:
                        name = transform(name)
                    if term.startswith(name):
                        trailing = term[len(name) :]
                        if hint in ITERATIVE_BOOL_IMPLICIT_VALUE:
                            implicit_value = False
                        elif is_nonetype(hint) or hint is None:
                            implicit_value = None
                        else:
                            hint = resolve_optional(hint)
                            implicit_value = (get_origin(hint) or hint)()  # pyright: ignore[reportAbstractUsage]
                        if trailing:
                            if trailing[0] == delimiter:
                                trailing = trailing[1:]
                                double_break = True
                                break
                            # Otherwise, it's not an actual match.
                        else:
                            # exact match
                            return (), implicit_value
                if double_break:
                    break
            else:
                # No negative-name matches found.
                raise ValueError

        if not self._accepts_arbitrary_keywords:
            # Still not an actual match.
            raise ValueError

        return tuple(trailing.split(delimiter)), implicit_value

    def _match_index(self, index: int) -> tuple[tuple[str, ...], Any]:
        if self.index is None:
            raise ValueError
        elif self.field_info.kind is self.field_info.VAR_POSITIONAL:
            if index < self.index:
                raise ValueError
        elif index != self.index:
            raise ValueError
        return (), UNSET

    def append(self, token: Token):
        """Safely add a :class:`Token`."""
        if not self.parameter.parse:
            raise ValueError

        if any(x.address == token.address for x in self.tokens):
            _, consume_all = self.token_count(token.keys)
            if not consume_all:
                raise RepeatArgumentError(token=token)

        if self.tokens:
            if bool(token.keys) ^ any(x.keys for x in self.tokens):
                raise MixedArgumentError(argument=self)
        self.tokens.append(token)

    @property
    def has_tokens(self) -> bool:
        """This argument, or a child argument, has at least 1 parsed token."""  # noqa: D404
        return bool(self.tokens) or any(x.has_tokens for x in self.children)

    @property
    def children_recursive(self) -> "ArgumentCollection":
        out = ArgumentCollection()
        for child in self.children:
            out.append(child)
            out.extend(child.children_recursive)
        return out

    def _convert_pydantic(self):
        if self.has_tokens:
            import pydantic

            unstructured_data = self._json()
            try:
                # This inherently also invokes pydantic validators
                return pydantic.TypeAdapter(self.field_info.annotation).validate_python(unstructured_data)
            except pydantic.ValidationError as e:
                self._handle_pydantic_validation_error(e)
        else:
            return UNSET

    def _convert(self, converter: Optional[Callable] = None):
        if self.parameter.converter:
            converter = self.parameter.converter
        elif converter is None:
            converter = partial(convert, name_transform=self.parameter.name_transform)

        def safe_converter(hint, tokens):
            if isinstance(tokens, dict):
                try:
                    return converter(hint, tokens)  # pyright: ignore
                except (AssertionError, ValueError, TypeError) as e:
                    raise CoercionError(msg=e.args[0] if e.args else None, argument=self, target_type=hint) from e
            else:
                try:
                    return converter(hint, tokens)  # pyright: ignore
                except (AssertionError, ValueError, TypeError) as e:
                    token = tokens[0] if len(tokens) == 1 else None
                    raise CoercionError(
                        msg=e.args[0] if e.args else None, argument=self, target_type=hint, token=token
                    ) from e

        if not self.parameter.parse:
            out = UNSET
        elif not self.children:
            positional: list[Token] = []
            keyword = {}

            def expand_tokens(tokens):
                for token in tokens:
                    if self._should_attempt_json_list(token):
                        import json

                        try:
                            parsed_json = json.loads(token.value)
                        except json.JSONDecodeError as e:
                            raise CoercionError(token=token, target_type=self.hint) from e

                        if not isinstance(parsed_json, list):
                            raise CoercionError(token=token, target_type=self.hint)

                        for element in parsed_json:
                            if element is None:
                                yield token.evolve(value="", implicit_value=element)
                            else:
                                yield token.evolve(value=str(element))
                    else:
                        yield token

            expanded_tokens = list(expand_tokens(self.tokens))
            for token in expanded_tokens:
                if token.implicit_value is not UNSET and isinstance(
                    token.implicit_value, get_origin(self.hint) or self.hint
                ):
                    assert len(expanded_tokens) == 1
                    return token.implicit_value

                if token.keys:
                    lookup = keyword
                    for key in token.keys[:-1]:
                        lookup = lookup.setdefault(key, {})
                    lookup.setdefault(token.keys[-1], []).append(token)
                else:
                    positional.append(token)

                if positional and keyword:  # pragma: no cover
                    # This should never happen due to checks in ``Argument.append``
                    raise MixedArgumentError(argument=self)

            if positional:
                if self.field_info and self.field_info.kind is self.field_info.VAR_POSITIONAL:
                    # Apply converter to individual values
                    hint = get_args(self.hint)[0]
                    tokens_per_element, _ = self.token_count()
                    out = tuple(safe_converter(hint, values) for values in grouper(positional, tokens_per_element))
                else:
                    out = safe_converter(self.hint, tuple(positional))
            elif keyword:
                if self.field_info and self.field_info.kind is self.field_info.VAR_KEYWORD and not self.keys:
                    # Apply converter to individual values
                    out = {key: safe_converter(get_args(self.hint)[1], value) for key, value in keyword.items()}
                else:
                    out = safe_converter(self.hint, keyword)
            elif self.required:
                raise MissingArgumentError(argument=self)
            else:  # no tokens
                return UNSET
        else:  # A dictionary-like structure.
            data = {}

            if self._should_attempt_json_dict():
                # Dict-like structures may have incoming json data from an environment variable.
                # Pass these values along as Tokens to children.
                import json

                from cyclopts.config._common import update_argument_collection

                while self.tokens:
                    token = self.tokens.pop(0)
                    try:
                        parsed_json = json.loads(token.value)
                    except json.JSONDecodeError as e:
                        raise CoercionError(token=token, target_type=self.hint) from e
                    update_argument_collection(
                        {self.name.lstrip("-"): parsed_json},
                        token.source,
                        self.children_recursive,
                        root_keys=(),
                        allow_unknown=False,
                    )

            if self._use_pydantic_type_adapter:
                return self._convert_pydantic()

            for child in self.children:
                assert len(child.keys) == (len(self.keys) + 1)
                if child.has_tokens:  # Either the child directly has tokens, or a nested child has tokens.
                    data[child.keys[-1]] = child.convert_and_validate(converter=converter)
                elif child.required:
                    # Check if the required fields are already populated.
                    obj = data
                    for k in child.keys:
                        try:
                            obj = obj[k]
                        except Exception:
                            raise MissingArgumentError(argument=child) from None
                    child._marked = True

            self._run_missing_keys_checker(data)

            if data:
                out = self.hint(**data)
            elif self.required:
                # This should NEVER happen: empty data to a required dict field.
                raise MissingArgumentError(argument=self)  # pragma: no cover
            else:
                out = UNSET

        return out

    def convert(self, converter: Optional[Callable] = None):
        """Converts :attr:`tokens` into :attr:`value`.

        Parameters
        ----------
        converter: Optional[Callable]
            Converter function to use. Overrides ``self.parameter.converter``

        Returns
        -------
        Any
            The converted data. Same as :attr:`value`.
        """
        if not self._marked:
            try:
                self.value = self._convert(converter=converter)
            except CoercionError as e:
                if e.argument is None:
                    e.argument = self
                if e.target_type is None:
                    e.target_type = self.hint
                raise
            except CycloptsError as e:
                if e.argument is None:
                    e.argument = self
                raise

        return self.value

    def validate(self, value):
        """Validates provided value.

        Parameters
        ----------
        value:
            Value to validate.

        Returns
        -------
        Any
            The converted data. Same as :attr:`value`.
        """
        assert isinstance(self.parameter.validator, tuple)

        if "pydantic" in sys.modules:
            import pydantic

            pydantic_version = tuple(int(x) for x in pydantic.__version__.split("."))
            if pydantic_version < (2,):
                # Cyclopts does NOT support/use pydantic v1.
                pydantic = None
        else:
            pydantic = None

        def validate_pydantic(hint, val):
            if not pydantic:
                return
            if self._use_pydantic_type_adapter:
                # Pydantic already called the validators
                return

            try:
                pydantic.TypeAdapter(hint).validate_python(val)
            except pydantic.ValidationError as e:
                self._handle_pydantic_validation_error(e)
            except pydantic.PydanticUserError:
                # Pydantic couldn't generate a schema for this type hint.
                pass

        try:
            if not self.keys and self.field_info and self.field_info.kind is self.field_info.VAR_KEYWORD:
                hint = get_args(self.hint)[1]
                for validator in self.parameter.validator:
                    for val in value.values():
                        validator(hint, val)
                validate_pydantic(dict[str, self.field_info.annotation], value)
            elif self.field_info and self.field_info.kind is self.field_info.VAR_POSITIONAL:
                hint = get_args(self.hint)[0]
                for validator in self.parameter.validator:
                    for val in value:
                        validator(hint, val)
                validate_pydantic(tuple[self.field_info.annotation, ...], value)
            else:
                for validator in self.parameter.validator:
                    validator(self.hint, value)
                validate_pydantic(self.field_info.annotation, value)
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(exception_message=e.args[0] if e.args else "", argument=self) from e

    def convert_and_validate(self, converter: Optional[Callable] = None):
        """Converts and validates :attr:`tokens` into :attr:`value`.

        Parameters
        ----------
        converter: Optional[Callable]
            Converter function to use. Overrides ``self.parameter.converter``

        Returns
        -------
        Any
            The converted data. Same as :attr:`value`.
        """
        val = self.convert(converter=converter)
        if val is not UNSET:
            self.validate(val)
        elif self.field_info.default is not FieldInfo.empty:
            self.validate(self.field_info.default)
        return val

    def token_count(self, keys: tuple[str, ...] = ()):
        """The number of string tokens this argument consumes.

        Parameters
        ----------
        keys: tuple[str, ...]
            The **python** keys into this argument.
            If provided, returns the number of string tokens that specific
            data type within the argument consumes.

        Returns
        -------
        int
            Number of string tokens to create 1 element.
        consume_all: bool
            :obj:`True` if this data type is iterable.
        """
        if len(keys) > 1:
            hint = self._default
        elif len(keys) == 1:
            hint = self._type_hint_for_key(keys[0])
        else:
            hint = self.hint
        tokens_per_element, consume_all = token_count(hint)
        return tokens_per_element, consume_all

    @property
    def negatives(self):
        """Negative flags from :meth:`.Parameter.get_negatives`."""
        return self.parameter.get_negatives(resolve_annotated(self.field_info.annotation))

    @property
    def name(self) -> str:
        """The **first** provided name this argument goes by."""
        return self.names[0]

    @property
    def names(self) -> tuple[str, ...]:
        """Names the argument goes by (both positive and negative)."""
        assert isinstance(self.parameter.name, tuple)
        return tuple(itertools.chain(self.parameter.name, self.negatives))

    def env_var_split(self, value: str, delimiter: Optional[str] = None) -> list[str]:
        """Split a given value with :meth:`.Parameter.env_var_split`."""
        return self.parameter.env_var_split(self.hint, value, delimiter=delimiter)

    @property
    def show(self) -> bool:
        """Show this argument on the help page.

        If an argument has child arguments, don't show it on the help-page.
        """
        return not self.children and self.parameter.show

    @property
    def required(self) -> bool:
        """Whether or not this argument requires a user-provided value."""
        if self.parameter.required is None:
            return self.field_info.required
        else:
            return self.parameter.required

    def _json(self) -> dict:
        """Convert argument to be json-like for pydantic.

        All values will be str/list/dict.
        """
        out = {}
        if self._accepts_keywords:
            for token in self.tokens:
                node = out
                for key in token.keys[:-1]:
                    node = node.setdefault(key, {})
                node[token.keys[-1]] = token.value if token.implicit_value is UNSET else token.implicit_value
        for child in self.children:
            child._marked = True
            if not child.has_tokens:
                continue
            keys = child.keys[len(self.keys) :]
            if child._accepts_keywords:
                result = child._json()
                if result:
                    out[keys[0]] = result
            elif (get_origin(child.hint) or child.hint) in ITERABLE_TYPES:
                out.setdefault(keys[-1], []).extend([token.value for token in child.tokens])
            else:
                token = child.tokens[0]
                out[keys[0]] = token.value if token.implicit_value is UNSET else token.implicit_value
        return out

    def _run_missing_keys_checker(self, data):
        if not self._missing_keys_checker or (not self.required and not data):
            return
        if not (missing_keys := self._missing_keys_checker(self, data)):
            return
        # Report the first missing argument.
        missing_key = missing_keys[0]
        keys = self.keys + (missing_key,)
        missing_arguments = self.children.filter_by(keys_prefix=keys)
        if missing_arguments:
            raise MissingArgumentError(argument=missing_arguments[0])
        else:
            missing_description = self.field_info.names[0] + "->" + "->".join(keys)
            raise ValueError(
                f'Required field "{missing_description}" is not accessible by Cyclopts; possibly due to conflicting POSITIONAL/KEYWORD requirements.'
            )

    def _handle_pydantic_validation_error(self, exc):
        import pydantic

        error = exc.errors()[0]
        if error["type"] == "missing":
            missing_argument = self.children_recursive.filter_by(keys_prefix=self.keys + error["loc"])[0]
            raise MissingArgumentError(argument=missing_argument) from exc
        elif isinstance(exc, pydantic.ValidationError):
            raise ValidationError(exception_message=str(exc), argument=self) from exc
        else:
            raise exc


def _resolve_groups_from_callable(
    func: Callable[..., Any],
    *default_parameters: Optional[Parameter],
    group_arguments: Optional[Group] = None,
    group_parameters: Optional[Group] = None,
) -> list[Group]:
    argument_collection = ArgumentCollection._from_callable(
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

    # Iteration 1: Collect all explicitly instantiated groups
    for argument in argument_collection:
        for group in argument.parameter.group:  # pyright: ignore
            if not isinstance(group, Group):
                continue

            # Ensure a different, but same-named group doesn't already exist
            if any(group != x and x._name == group._name for x in resolved_groups):
                raise ValueError("Cannot register 2 distinct Group objects with same name.")

            if group.default_parameter is not None and group.default_parameter.group:
                # This shouldn't be possible due to ``Group`` internal checks.
                raise ValueError("Group.default_parameter cannot have a specified group.")  # pragma: no cover

            # Add the group to resolved_groups if it hasn't been added yet.
            try:
                next(x for x in resolved_groups if x._name == group._name)
            except StopIteration:
                resolved_groups.append(group)

    # Iteration 2: Create all implicitly defined Group from strings.
    for argument in argument_collection:
        for group in argument.parameter.group:  # pyright: ignore
            if not isinstance(group, str):
                continue
            try:
                next(x for x in resolved_groups if x.name == group)
            except StopIteration:
                resolved_groups.append(Group(group))

    return resolved_groups


def _extract_docstring_help(f: Callable) -> dict[tuple[str, ...], Parameter]:
    from docstring_parser import parse_from_object

    # Handle functools.partial
    with suppress(AttributeError):
        f = f.func  # pyright: ignore[reportFunctionMemberAccess]

    try:
        return {
            tuple(dparam.arg_name.split(".")): Parameter(help=dparam.description)
            for dparam in parse_from_object(f).params
        }
    except TypeError:
        # Type hints like ``dict[str, str]`` trigger this.
        return {}


def _resolve_parameter_name_helper(elem):
    if elem.endswith("*"):
        elem = elem[:-1].rstrip(".")
    if elem and not elem.startswith("-"):
        elem = "--" + elem
    return elem


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
    argss = tuple(x for x in argss if x)

    if len(argss) == 0:
        return ()
    elif len(argss) == 1:
        return tuple("*" if x == "*" else _resolve_parameter_name_helper(x) for x in argss[0])

    # Combine the first 2, and do a recursive call.
    out = []
    for a1 in argss[0]:
        a1 = _resolve_parameter_name_helper(a1)
        for a2 in argss[1]:
            if a2.startswith("-") or not a1:
                out.append(a2)
            else:
                out.append(a1 + "." + a2)

    return _resolve_parameter_name(tuple(out), *argss[2:])
