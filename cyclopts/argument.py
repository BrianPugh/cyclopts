import inspect
import itertools
from contextlib import suppress
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    get_args,
    get_origin,
)

from attrs import define, field, frozen

from cyclopts._convert import (
    AnnotatedType,
    NoneType,
    is_attrs,
    is_dataclass,
    is_namedtuple,
    is_pydantic,
    is_typeddict,
    resolve,
    resolve_optional,
    token_count,
)
from cyclopts.exceptions import MixedArgumentError, RepeatArgumentError
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.utils import ParameterDict, is_union

_PARAMETER_EMPTY_HELP = Parameter(help="")

# parameter subkeys should not inherit these parameter values from their parent.
_PARAMETER_SUBKEY_BLOCKER = Parameter(
    name=None,
    converter=None,
    validator=None,
    negative=None,
    help=None,
    required=None,
    accepts_keys=None,
)


def _iparam_get_hint(iparam):
    hint = iparam.annotation
    if hint is inspect.Parameter.empty or resolve(hint) is Any:
        hint = str if iparam.default in (inspect.Parameter.empty, None) else type(iparam.default)
    hint = resolve_optional(hint)
    return hint


@frozen
class Token:
    """
    Purely a dataclass containing factual book-keeping for a user input.
    """

    # Value like "--foo" or `--foo.bar.baz` that indicated token; ``None`` when positional.
    # Could also be something like "tool.project.foo" if `source=="config"`
    # or could be `TOOL_PROJECT_FOO` if coming from an `source=="env"`
    # **This should be pretty unadulterated from the user's input.**
    # Used ONLY for error message purposes.
    keyword: Optional[str]  # TODO: rename to "key"

    # Empty string when a flag. The parsed token value (unadulterated)
    # See ``Token.implicit_value``
    value: str

    # Where the token came from; used for error message purposes.
    # Cyclopts specially uses "cli" for cli-parsed tokens.
    source: str

    index: int = field(default=0, kw_only=True)

    # Only used for Arguments that take arbitrary keys.
    keys: Tuple[str, ...] = field(default=(), kw_only=True)

    implicit_value: Any = field(default=None, kw_only=True)


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

    # List of tokens parsed from various sources
    # If tokens is empty, then no tokens have been parsed for this argument.
    tokens: List[Token] = field(factory=list)

    # Multiple ``Argument`` may be associated with a single iparam.
    # However, each ``Argument`` must have a unique iparam/keys combo
    iparam: inspect.Parameter = field(default=None)

    # Fully resolved Parameter
    # Resolved parameter should have a fully resolved Parameter.name
    cparam: Parameter = field(factory=Parameter)

    # The type for this leaf; may be different from ``iparam.annotation``
    # because this could be a subkey of iparam.
    # This hint MUST be unannotated.
    hint: Any

    # Associated positional index for iparam.
    index: Optional[int] = field(default=None)

    # **Python** Keys into iparam that lead to this leaf.
    # Note: that self.cparam.name and self.keys can naively disagree!
    # For example, a cparam.name=="--foo.bar.baz" could be aliased to "--fizz".
    # "keys" may be an empty tuple.
    # This should be populated based on type-hints, not ``Parameter.name``
    keys: Tuple[str, ...] = field(default=())

    _accepts_keywords: bool = field(default=False, init=False, repr=False)

    _default: Any = field(default=None, init=False, repr=False)
    _lookup: dict = field(factory=dict, init=False, repr=False)

    def __attrs_post_init__(self):
        # By definition, self.hint is Not AnnotatedType
        hint = resolve(self.hint)
        hints = get_args(hint) if is_union(hint) else (hint,)

        if self.cparam.accepts_keys is False:  # ``None`` means to infer.
            return

        for hint in hints:
            # This could be annotated...
            origin = get_origin(hint)
            # TODO: need to resolve Annotation and handle cyclopts.Parameters; or do we?
            hint_origin = {hint, origin}

            # Classes that ALWAYS takes keywords (accepts_keys=None)
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
                self._accepts_keywords = True
                self._lookup.update(hint.__annotations__)

            if self.cparam.accepts_keys is None:
                continue
            # Only explicit ``self.cparam.accepts_keys == True`` from here on

            # Classes that MAY take keywords (accepts_keys=True)
            # They must be explicitly specified ``accepts_keys=True`` because otherwise
            # providing a single positional argument is what we want.
            if is_dataclass(hint):
                self._accepts_keywords = True
                self._lookup.update({k: v.type for k, v in hint.__dataclass_fields__.items()})
            elif is_namedtuple(hint):
                # collections.namedtuple does not have type hints, assume "str" for everything.
                self._accepts_keywords = True
                self._lookup.update({field: hint.__annotations__.get(field, str) for field in hint._fields})
            elif is_attrs(hint):
                self._accepts_keywords = True
                self._lookup.update({a.alias: a.type for a in hint.__attrs_attrs__})
            elif is_pydantic(hint):
                self._accepts_keywords = True
                self._lookup.update({k: v.annotation for k, v in hint.model_fields.items()})
            else:
                self._accepts_keywords = True
                for i, iparam in enumerate(inspect.signature(hint.__init__).parameters.values()):
                    if i == 0 and iparam.name == "self":
                        continue
                    if iparam.kind is iparam.VAR_KEYWORD:
                        self._default = iparam.annotation
                    else:
                        self._lookup[iparam.name] = iparam.annotation

    @property
    def accepts_arbitrary_keywords(self) -> bool:
        args = get_args(self.hint) if is_union(self.hint) else (self.hint,)
        return any(dict in (arg, get_origin(arg)) for arg in args)

    def type_hint_for_key(self, key: str):
        try:
            return self._lookup[key]
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
    ) -> Tuple[Tuple[str, ...], Any]:
        """Match a name search-term, or a positional integer index.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
        Any
            Implicit value.
        """
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
    ) -> Tuple[Tuple[str, ...], Any]:
        """Find the matching Argument for a token keyword identifier.

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
            for name in self.cparam.get_negatives(self.hint):
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

    def _match_index(self, index: int) -> Tuple[Tuple[str, ...], Any]:
        if self.index is None or self.iparam in (self.iparam.KEYWORD_ONLY, self.iparam.VAR_KEYWORD):
            raise ValueError
        elif self.iparam.kind is self.iparam.VAR_POSITIONAL:
            if index < self.index:
                raise ValueError
        elif index != self.index:
            raise ValueError
        return (), None

    def append(self, token: Token):
        if (
            any((x.keys, x.index) == (token.keys, token.index) for x in self.tokens)
            and not self.token_count(token.keys)[1]
        ):
            raise RepeatArgumentError(parameter=self.iparam)
        if self.tokens:
            if bool(token.keys) ^ any(x.keys for x in self.tokens):
                raise MixedArgumentError(parameter=self.iparam)
        self.tokens.append(token)

    def values(self) -> Iterator[str]:
        for token in self.tokens:
            yield token.value

    def convert(self):
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
                raise MixedArgumentError(parameter=self.iparam)

        if positional:
            return self.cparam.converter(self.hint, tuple(positional))
        elif keyword:
            return self.cparam.converter(self.hint, keyword)
        else:
            raise NotImplementedError

    def validate(self, value):
        assert isinstance(self.cparam.validator, tuple)
        for validator in self.cparam.validator:
            validator(self.hint, value)

    def convert_and_validate(self):
        val = self.convert()
        self.validate(val)
        return val

    def token_count(self, keys: Tuple[str, ...] = ()):
        if len(keys) > 1:
            hint = self._default
        elif len(keys) == 1:
            hint = self.type_hint_for_key(keys[0])
        else:
            hint = self.hint
        tokens_per_element, consume_all = token_count(hint)
        consume_all |= self.iparam.kind is self.iparam.VAR_POSITIONAL  # TODO: is this necessary?
        return tokens_per_element, consume_all

    @property
    def negatives(self):
        return self.cparam.get_negatives(self.hint)

    @property
    def names(self) -> Tuple[str, ...]:
        assert isinstance(self.cparam.name, tuple)
        return tuple(itertools.chain(self.cparam.name, self.negatives))

    def env_var_split(self, value: str, delimiter: Optional[str] = None) -> List[str]:
        return self.cparam.env_var_split(self.hint, value, delimiter=delimiter)


class ArgumentCollection(list):
    """Provides easy lookups/pattern matching."""

    def match(
        self,
        term: Union[str, int],
        *,
        transform: Optional[Callable[[str], str]] = None,
        delimiter: str = ".",
    ) -> Tuple[Argument, Tuple[str, ...], Any]:
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

    def populated(self, iparam: Optional[inspect.Parameter] = None) -> Iterator[Argument]:
        for argument in self:
            if not argument.tokens:
                continue
            if argument.iparam != iparam:
                continue
            yield argument

    def convert(self) -> ParameterDict:
        out = ParameterDict()
        for argument in self:
            if not argument.tokens:
                continue
            node = out
            keys_to_leaf = (argument.iparam,) + argument.keys
            for key in keys_to_leaf[:-1]:
                node = node.setdefault(key, {})
            node[keys_to_leaf[-1]] = argument.convert_and_validate()

        return out

    @property
    def names(self):
        return (name for argument in self for name in argument.names)

    @classmethod
    def _from_type(
        cls,
        iparam: inspect.Parameter,
        hint,
        keys: Tuple[str, ...],
        *default_parameters,
        group_lookup: Dict[str, Group],
        group_arguments: Group,
        group_parameters: Group,
        parse_docstring: bool = True,
        positional_index: Optional[int] = None,
    ):
        assert hint is not NoneType
        out = cls()

        if not keys:  # root hint annotation
            if iparam.kind is iparam.VAR_KEYWORD:
                hint = Dict[str, hint]
            elif iparam.kind is iparam.VAR_POSITIONAL:
                hint = Tuple[hint, ...]

        if hint is inspect.Parameter.empty:
            breakpoint()
        hint = resolve_optional(hint)
        if type(hint) is AnnotatedType:
            annotations = hint.__metadata__  # pyright: ignore
            hint = get_args(hint)[0]
            cyclopts_parameters_no_group = [x for x in annotations if isinstance(x, Parameter)]
        else:
            cyclopts_parameters_no_group = []

        if group_lookup:
            cyclopts_parameters = []
            for cparam in cyclopts_parameters_no_group:
                for group in cparam.group:  # pyright:ignore
                    if isinstance(group, str):
                        group = group_lookup[group]
                    cyclopts_parameters.append(group.default_parameter)
                cyclopts_parameters.append(cparam)
        else:
            cyclopts_parameters = cyclopts_parameters_no_group

        upstream_parameter = Parameter.combine(*default_parameters)
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
                        immediate_parameter.name or tuple(cparam.name_transform(k) for k in keys[-1:]),  # pyright: ignore
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
                    if cparam.name:
                        # TODO: Probably something like `--existing.[KEYWORD]`
                        breakpoint()
                    else:
                        cparam = Parameter.combine(cparam, Parameter(name=("--[KEYWORD]",)))
                else:
                    # cparam.name_transform cannot be None due to:
                    #     attrs.converters.default_if_none(default_name_transform)
                    assert cparam.name_transform is not None
                    cparam = Parameter.combine(cparam, Parameter(name=["--" + cparam.name_transform(iparam.name)]))

        candidate_argument = Argument(iparam=iparam, cparam=cparam, keys=keys, hint=hint, index=positional_index)
        if candidate_argument.accepts_arbitrary_keywords:
            # Argument that accepts keywords that's also a leaf.
            out.append(candidate_argument)
        if candidate_argument._accepts_keywords:
            # Argument that accepts keywords that's NOT a leaf.
            docstring_lookup = {}
            if parse_docstring:
                docstring_lookup = _extract_docstring_help(candidate_argument.hint)

            for field_name, field_hint in candidate_argument._lookup.items():
                out.extend(
                    cls._from_type(
                        iparam,
                        field_hint,
                        keys + (field_name,),
                        docstring_lookup.get(field_name, _PARAMETER_EMPTY_HELP),
                        cparam,
                        group_lookup=group_lookup,
                        group_arguments=group_arguments,
                        group_parameters=group_parameters,
                        parse_docstring=parse_docstring,
                        # Purposely DONT pass along positional_index.
                        # We don't want to populate subkeys with positional arguments.
                    )
                )
        else:
            # Typical argument.
            out.append(candidate_argument)
        return out

    @classmethod
    def from_iparam(
        cls,
        iparam: inspect.Parameter,
        *default_parameters: Optional[Parameter],
        group_lookup: Optional[Dict[str, Group]] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        positional_index: Optional[int] = None,
    ):
        # The responsibility of this function is to extract out the root type
        # and annotation. The rest of the functionality goes into _from_type.
        if group_lookup is None:
            group_lookup = {}
        if group_arguments is None:
            group_arguments = Group.create_default_arguments()
        if group_parameters is None:
            group_parameters = Group.create_default_parameters()

        hint = _iparam_get_hint(iparam)

        return cls._from_type(
            iparam,
            hint,
            (),
            *default_parameters,
            _PARAMETER_EMPTY_HELP,
            Parameter(required=iparam.default is iparam.empty),
            group_lookup=group_lookup,
            group_arguments=group_arguments,
            group_parameters=group_parameters,
            positional_index=positional_index,
        )

    @classmethod
    def from_callable(
        cls,
        func: Callable,
        *default_parameters: Optional[Parameter],
        group_lookup: Optional[Dict[str, Group]] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        parse_docstring: bool = True,
    ):
        import cyclopts.utils

        if group_lookup is None:
            group_lookup = {group.name: group for group in _resolve_groups_3(func)}

        docstring_lookup = _extract_docstring_help(func) if parse_docstring else {}

        out = cls()
        for i, iparam in enumerate(cyclopts.utils.signature(func).parameters.values()):
            out.extend(
                cls.from_iparam(
                    iparam,
                    _PARAMETER_EMPTY_HELP,
                    *default_parameters,
                    docstring_lookup.get(iparam.name),
                    group_lookup=group_lookup,
                    group_arguments=group_arguments,
                    group_parameters=group_parameters,
                    positional_index=i,
                )
            )
        return out

    @property
    def var_keyword(self) -> Optional[Argument]:
        for argument in self:
            if argument.iparam.kind == argument.iparam.VAR_KEYWORD:
                return argument
        return None

    @property
    def iparams(self):
        out = ParameterDict()  # Repurposing ParameterDict as a Set.
        for argument in self:
            out[argument.iparam] = None
        return out.keys()


def _resolve_groups_3(func: Callable) -> List[Group]:
    resolved_groups = []

    for argument in ArgumentCollection.from_callable(func, group_lookup={}, parse_docstring=False):
        for group in argument.cparam.group:  # pyright: ignore
            if isinstance(group, str):
                try:
                    next(x for x in resolved_groups if x.name == group)
                except StopIteration:
                    resolved_groups.append(Group(group))
            elif isinstance(group, Group):
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
            else:
                raise TypeError
    return resolved_groups


def _extract_docstring_help(f: Callable) -> Dict[str, Parameter]:
    from docstring_parser import parse as docstring_parse

    return {dparam.arg_name: Parameter(help=dparam.description) for dparam in docstring_parse(f.__doc__ or "").params}


def _resolve_parameter_name(*argss: Tuple[str, ...]) -> Tuple[str, ...]:
    """
    args will only ever be >1 if parsing a subkey.
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
