import inspect
import itertools
from contextlib import suppress
from functools import cached_property
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

from attr.converters import default_if_none
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
from cyclopts.exceptions import RepeatArgumentError
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.utils import Sentinel, is_union


class NOT_CONVERTED(Sentinel):  # noqa: N801
    pass


_PARAMETER_EMPTY_HELP = Parameter(help="")


def _accepts_keywords(hint) -> bool:
    # TODO: revisit this; do we want "magical" behavior?
    # MUST agree with ArgumentCollection._from_type
    origin = get_origin(hint)
    if is_union(origin):
        return any(_accepts_keywords(x) for x in get_args(hint))
    return (
        dict in (hint, origin)
        or is_typeddict(hint)
        or is_dataclass(hint)
        or is_namedtuple(hint)
        or is_attrs(hint)
        or is_pydantic(hint)
    )


@frozen
class Token:
    """
    Purely a dataclass containing factual book-keeping for a user input.
    """

    # Value like "--foo" or `--foo.bar.baz` that indicated token; ``None`` when positional.
    # Could also be something like "tool.project.foo" if `source=="config"`
    # or could be `TOOL_PROJECT_FOO` if coming from an `source=="env"`
    # **This should be pretty unadulterated from the user's input.**
    keyword: Optional[str]  # TODO: rename to "key"

    # Empty string when a flag. The parsed token value (unadulterated)
    token: str  # TODO: rename to "value"

    # Where the token came from; used for --help purposes.
    # Cyclopts specially uses "cli" for cli-parsed tokens.
    source: str

    index: int = 0


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

    accepts_keywords: bool = field(default=False, init=False)
    _default: Any = field(default=None, init=False)
    _lookup: dict = field(factory=dict, init=False)

    def __attrs_post_init__(self):
        # By definition, self.hint is Not AnnotatedType
        hint = resolve(self.hint)
        hints = get_args(hint) if is_union(hint) else (hint,)

        if self.cparam.accepts_keys is False:
            return

        for hint in hints:
            # This could be annotated...
            origin = get_origin(hint)
            # TODO: need to resolve Annotation and handle cyclopts.Parameters; or do we?
            hint_origin = {hint, origin}

            # Classes that ALWAYS takes keywords (accepts_keys=None)
            if dict in hint_origin:
                self.accepts_keywords = True
                key_type, val_type = str, str
                args = get_args(hint)
                with suppress(IndexError):
                    key_type = args[0]
                    val_type = args[1]
                if key_type is not str:
                    raise TypeError('Dictionary type annotations must have "str" keys.')
                self._default = val_type
            elif is_typeddict(hint):
                self.accepts_keywords = True
                self._lookup.update(hint.__annotations__)

            if self.cparam.accepts_keys is None:
                continue

            # Classes that MAY take keywords (accepts_keys=True)
            if is_dataclass(hint):
                self.accepts_keywords = True
                self._lookup.update({k: v.type for k, v in hint.__dataclass_fields__.items()})
            elif is_namedtuple(hint):
                # collections.namedtuple does not have type hints, assume "str" for everything.
                self.accepts_keywords = True
                self._lookup.update({field: hint.__annotations__.get(field, str) for field in hint._fields})
            elif is_attrs(hint):
                self.accepts_keywords = True
                self._lookup.update({a.alias: a.type for a in hint.__attrs_attrs__})
            elif is_pydantic(hint):
                self.accepts_keywords = True
                self._lookup.update({k: v.annotation for k, v in hint.model_fields.items()})
            else:
                self.accepts_keywords = True
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

    @property
    def accepts_multiple_arguments(self) -> bool:
        return self.token_count()[1]

    def type_hint_for_key(self, key: str):
        try:
            return self._lookup[key]
        except KeyError:
            if self._default is None:
                raise
            return self._default

    def match(self, term: Union[str, int]) -> Tuple[Tuple[str, ...], Any]:
        """Match a name search-term, or a positional integer index.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
            Otherwise, should be the same as argument.keys
        Any
            Implicit value.
        """
        return self._match_index(term) if isinstance(term, int) else self._match_name(term)

    def _match_name(self, token: str) -> Tuple[Tuple[str, ...], Any]:
        """Find the matching Argument for a token keyword identifier.

        Parameter
        ---------
        token: str
            Something like "--foo"

        Raises
        ------
        ValueError
            If no match found.

        Returns
        -------
        Tuple[str, ...]
            Leftover keys after matching to this argument.
            Used if this argument accepts_arbitrary_keywords.
            Otherwise, should be the same as argument.keys
        Any
            Implicit value.
        """
        if self.iparam.kind is self.iparam.VAR_KEYWORD:
            # TODO: apply cparam.name_transform to keys here?
            return tuple(token.lstrip("-").split(".")), None

        assert self.cparam.name
        for name in self.cparam.name:
            if name.startswith(token):
                trailing = token[len(token) :]
                implicit_value = True if self.hint is bool else None
                if trailing:
                    if trailing[0] == ".":
                        trailing = token[1:]
                        break
                    # Otherwise, it's not an actual match.
                else:
                    # exact match
                    return (), implicit_value
        else:
            # No positive-name matches found.
            for name in self.cparam.get_negatives(self.hint):
                if name.startswith(token):
                    trailing = token[len(token) :]
                    implicit_value = (get_origin(self.hint) or self.hint)()
                    if trailing:
                        if trailing[0] == ".":
                            trailing = token[1:]
                            break
                        # Otherwise, it's not an actual match.
                    else:
                        # exact match
                        return (), implicit_value
            else:
                # No negative-name matches found.
                raise ValueError

        # trailing is period-delimited subkeys like ``bar.baz``

        if not self.accepts_arbitrary_keywords:
            # Still not an actual match.
            raise ValueError

        # TODO: apply cparam.name_transform to keys here?
        return tuple(trailing.split(".")), implicit_value

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
        if self.tokens and not self.accepts_multiple_arguments:
            raise RepeatArgumentError(parameter=self.iparam)
        self.tokens.append(token)

    def values(self) -> Iterator[str]:
        for token in self.tokens:
            yield token.token

    def convert(self):
        return self.cparam.converter(self.hint, tuple(self.values()))

    def validate(self, value):
        # TODO
        raise NotImplementedError

    def token_count(self, keys: Tuple[str, ...] = ()):
        if keys:
            raise NotImplementedError
        else:
            tokens_per_element, consume_all = token_count(self.hint)
            consume_all |= self.iparam.kind is self.iparam.VAR_POSITIONAL
            return tokens_per_element, consume_all

    @property
    def negatives(self):
        return self.cparam.get_negatives(self.hint)

    @property
    def names(self) -> Tuple[str, ...]:
        assert isinstance(self.cparam.name, tuple)
        return tuple(itertools.chain(self.cparam.name, self.negatives))


class ArgumentCollection(list):
    """Provides easy lookups/pattern matching."""

    def match(self, term: Union[str, int]) -> Tuple[Argument, Tuple[str, ...], Any]:
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
                match_keys, implicit_value = argument.match(term)
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
        hint = resolve_optional(hint)
        if type(hint) is AnnotatedType:
            annotations = hint.__metadata__  # pyright: ignore
            hint = get_args(hint)[0]
            cyclopts_parameters_no_group = [x for x in annotations if isinstance(x, Parameter)]
        else:
            cyclopts_parameters_no_group = []

        if not keys:
            if iparam.kind is iparam.VAR_KEYWORD:
                hint = Dict[str, hint]
            elif iparam.kind is iparam.VAR_POSITIONAL:
                hint = Tuple[hint, ...]

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

        cparam = Parameter.combine(upstream_parameter, immediate_parameter)

        # Derive default parameter name (if necessary).
        if keys:
            cparam = Parameter.combine(
                cparam,
                Parameter(
                    name=_resolve_parameter_name(
                        upstream_parameter.name,  # pyright: ignore
                        immediate_parameter.name or tuple(cparam.name_transform(k) for k in keys[-1:]),  # pyright: ignore
                    )
                ),
            )
        elif not cparam.name:
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
            out.append(candidate_argument)
        if candidate_argument.accepts_keywords:
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
                        # Purposely DONT pass along posiitonal_index.
                        # We don't want to populate subkeys with positional arguments.
                    )
                )
        else:
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

        hint = iparam.annotation

        if hint is inspect.Parameter.empty:
            hint = str if iparam.default in (inspect.Parameter.empty, None) else type(iparam.default)

        hint = resolve_optional(hint)

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
