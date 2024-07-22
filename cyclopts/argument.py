import inspect
from contextlib import suppress
from enum import Enum
from functools import cached_property, partial
from typing import (
    Any,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    get_args,
    get_origin,
)

from attr import setters
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
)
from cyclopts.parameter import Parameter
from cyclopts.utils import Sentinel, is_union


class NOT_CONVERTED(Sentinel):  # noqa: N801
    pass


def _accepts_keywords(hint) -> bool:
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
    This class should be purely a dataclass containing factual book-keeping for a user input.
    """

    # Value like "--foo" or `--foo.bar.baz` that indicated token; ``None`` when positional.
    # Could also be something like "tool.project.foo" if `source=="config"`
    # or could be `TOOL_PROJECT_FOO` if coming from an `source=="env"`
    # **This should be pretty unadulterated from the user's input.**
    keyword: Optional[str]

    # ``None`` when a flag. The parsed token value (unadulterated)
    token: Optional[str]

    # Where the token came from; used for --help purposes.
    # Cyclopts specially uses "cli" for cli-parsed tokens.
    source: str

    # When multiple tokens are given for a single keyword (tuple).
    # If ``keyword`` is ``None`` (positional), then this is the position index.
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
    iparam: inspect.Parameter

    # Fully resolved Parameter
    # Resolved parameter should have a fully resolved Parameter.name
    cparam: "Parameter"

    # The type for this leaf; may be different from ``iparam.annotation``
    # because this could be a subkey of iparam.
    # This hint MUST be unannotated.
    hint: Any

    # **Python** Keys into iparam that lead to this leaf.
    # Note: that self.cparam.name and self.keys can naively disagree!
    # For example, a cparam.name=="--foo.bar.baz" could be aliased to "--fizz".
    # "keys" may be an empty tuple.
    # This should be populated based on type-hints, not ``Parameter.name``
    keys: Tuple[str, ...]

    accepts_keywords: bool = field(default=False, init=False)
    _default: Any = field(default=None, init=False)
    _lookup: dict = field(factory=dict, init=False)

    def __attrs_post_init__(self):
        # By definition, self.hint is Not AnnotatedType
        hints = get_args(self.hint) if is_union(self.hint) else (self.hint,)

        if self.cparam.accepts_keys is False:
            return

        for hint in hints:
            # This could be annotated...
            origin = get_origin(hint)
            # TODO: need to resolve Annotation and handle cyclopts.Parameters
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
                raise NotImplementedError

    @cached_property
    def accepts_arbitrary_keywords(self):
        args = get_args(self.hint) if is_union(self.hint) else (self.hint,)
        return any(dict in (arg, get_origin(arg)) for arg in args)

    def type_hint_for_key(self, key: str):
        try:
            return self._lookup[key]
        except KeyError:
            if self._default is None:
                raise
            return self._default

    def match(self, token: str) -> Tuple[str, ...]:
        """
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
            Keys into this Argument
        """
        assert self.cparam.name
        for name in self.cparam.name:
            if name.startswith(token):
                trailing = token[len(token) :]
                if trailing:
                    if trailing[0] == ".":
                        trailing = token[1:]
                        break
                    # Otherwise, it's not an actual match.
                else:
                    # exact match
                    return ()
        else:
            # No matches found.
            raise ValueError

        # trailing is period-delimited subkeys like ``bar.baz``

        if not self.accepts_arbitrary_keywords:
            # Still not an actual match.
            raise ValueError

        # TODO: apply cparam.name_transform to keys here?
        return tuple(trailing.split("."))

    def append(self, token: Token):
        self.tokens.append(token)

    def convert(self):
        # TODO
        # Converts all the tokens into a final output.
        # should use the self.cparam.converter
        raise NotImplementedError

    def validate(self, value):
        # TODO
        raise NotImplementedError

    def token_count(self) -> int:
        # TODO
        raise NotImplementedError


class ArgumentCollection(list):
    """Provides easy lookups/pattern matching."""

    def match(self, token: str) -> Tuple[Argument, Tuple[str, ...]]:
        """Maps keyword CLI arguments to their :class:`Argument`.

        Parameters
        ----------
        token: str
            Something like "--foo" or "-f" or "--foo.bar.baz".
        """
        # TODO: it MIGHT be unnecessary to search entire list for best match.
        best_match_argument, best_match_keys = None, None
        for argument in self:
            try:
                match_keys = argument.match(token)
            except ValueError:
                continue
            if best_match_keys is None or len(match_keys) < len(best_match_keys):
                best_match_keys = match_keys
                best_match_argument = argument

        if best_match_argument is None or best_match_keys is None:
            raise ValueError(f"No Argument matches {token!r}")

        return best_match_argument, best_match_keys

    @classmethod
    def _from_type(
        cls,
        iparam: inspect.Parameter,
        hint,
        keys: Tuple[str, ...],
        *default_parameters,
    ):
        # Does NOT perform group resolution; assumes that's handled in default_parameters.

        assert hint is not NoneType
        hint = resolve_optional(hint)
        if type(hint) is AnnotatedType:
            annotations = hint.__metadata__  # pyright: ignore
            hint = get_args(hint)[0]
            cyclopts_parameters = [x for x in annotations if isinstance(x, Parameter)]
        else:
            cyclopts_parameters = []

        out = cls()
        cparam = Parameter.combine(*default_parameters, *cyclopts_parameters)
        if not cparam.parse:
            return out
        candidate_argument = Argument(iparam=iparam, cparam=cparam, keys=keys, hint=hint)
        if candidate_argument.accepts_arbitrary_keywords:
            out.append(candidate_argument)
        if candidate_argument.accepts_keywords:
            for field_name, field_hint in candidate_argument._lookup.items():
                out.extend(cls._from_type(iparam, field_hint, keys + (field_name,), cparam))
        else:
            out.append(candidate_argument)
        return out

    @classmethod
    def from_iparam(cls, iparam: inspect.Parameter, *default_parameters: Optional[Parameter]):
        # The responsibility of this function is to extract out the root type
        # and annotation. The rest of the functionality goes into _from_type.
        # Does NOT perform group resolution; assumes that's handled in default_parameters.
        hint = iparam.annotation

        if hint is inspect.Parameter.empty:
            hint = str if iparam.default in (inspect.Parameter.empty, None) else type(iparam.default)

        hint = resolve_optional(hint)
        return cls._from_type(iparam, hint, (), *default_parameters)

    @classmethod
    def from_callable(cls, func, *default_parameters: Optional[Parameter]):
        # Does NOT perform group resolution; assumes that's handled in default_parameters.
        out = cls()
        for iparam in inspect.signature(func).parameters.values():
            out.extend(cls.from_iparam(iparam, *default_parameters))
        return out
