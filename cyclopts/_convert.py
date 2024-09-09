import collections.abc
import inspect
import sys
from collections.abc import Sequence
from contextlib import suppress
from enum import Enum
from functools import partial
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Optional,
    Union,
    get_args,
    get_origin,
)

from cyclopts.exceptions import CoercionError
from cyclopts.utils import AnnotatedType, NoneType, default_name_transform, is_union

if sys.version_info >= (3, 12):
    from typing import TypeAliasType  # pragma: no cover
else:
    TypeAliasType = None  # pragma: no cover

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required  # pragma: no cover
else:
    from typing import NotRequired, Required  # pragma: no cover

if TYPE_CHECKING:
    from cyclopts.argument import Token


_implicit_iterable_type_mapping: dict[type, type] = {
    list: list[str],
    set: set[str],
    tuple: tuple[str, ...],
    dict: dict[str, str],
}

_iterable_types = {list, set}

NestedCliArgs = dict[str, Union[Sequence[str], "NestedCliArgs"]]


def _bool(s: str) -> bool:
    s = s.lower()
    if s in {"no", "n", "0", "false", "f"}:
        return False
    elif s in {"yes", "y", "1", "true", "t"}:
        return True
    else:
        # Cyclopts is a little bit conservative when coercing strings into boolean.
        raise CoercionError(target_type=bool)


def _int(s: str) -> int:
    s = s.lower()
    if s.startswith("0x"):
        return int(s, 16)
    elif s.startswith("0b"):
        return int(s, 2)
    else:
        # Casting to a float first allows for things like "30.0"
        return int(round(float(s)))


def _bytes(s: str) -> bytes:
    return bytes(s, encoding="utf8")


def _bytearray(s: str) -> bytearray:
    return bytearray(_bytes(s))


# For types that need more logic than just invoking their type
_converters = {
    bool: _bool,
    int: _int,
    bytes: _bytes,
    bytearray: _bytearray,
}


def _first_argument_type(hint):
    try:
        signature = inspect.signature(hint.__init__)
    except AttributeError:
        raise ValueError from None
    for iparam in signature.parameters.values():
        if iparam.name == "self":
            continue
        return str if iparam.annotation is iparam.empty else iparam.annotation
    raise ValueError


def _convert_tuple(
    type_: type[Any],
    *tokens: "Token",
    converter: Optional[Callable[[type, str], Any]],
    name_transform: Callable[[str], str],
) -> tuple:
    convert = partial(_convert, converter=converter, name_transform=name_transform)
    inner_types = tuple(x for x in get_args(type_) if x is not ...)
    inner_token_count, consume_all = token_count(type_)
    if consume_all:
        # variable-length tuple (list-like)
        remainder = len(tokens) % inner_token_count
        if remainder:
            raise CoercionError(
                msg=f"Incorrect number of arguments: expected multiple of {inner_token_count} but got {len(tokens)}."
            )
        if len(inner_types) == 1:
            inner_type = inner_types[0]
        elif len(inner_types) == 0:
            inner_type = str
        else:
            raise ValueError("A tuple must have 0 or 1 inner-types.")

        if inner_token_count == 1:
            out = tuple(convert(inner_type, x) for x in tokens)
        else:
            out = tuple(
                convert(inner_type, tokens[i : i + inner_token_count]) for i in range(0, len(tokens), inner_token_count)
            )
        return out
    else:
        # Fixed-length tuple
        if inner_token_count != len(tokens):
            raise CoercionError(
                msg=f"Incorrect number of arguments: expected {inner_token_count} but got {len(tokens)}."
            )
        args_per_convert = [token_count(x)[0] for x in inner_types]
        it = iter(tokens)
        batched = [[next(it) for _ in range(size)] for size in args_per_convert]
        batched = [elem[0] if len(elem) == 1 else elem for elem in batched]
        out = tuple(convert(inner_type, arg) for inner_type, arg in zip(inner_types, batched))
    return out


def _convert(
    type_,
    token: Union["Token", Sequence["Token"]],
    *,
    converter: Optional[Callable[[type, str], Any]],
    name_transform: Callable[[str], str],
):
    """Inner recursive conversion function for public ``convert``.

    Parameters
    ----------
    converter: Callable
    name_transform: Callable
    """
    convert = partial(_convert, converter=converter, name_transform=name_transform)
    convert_tuple = partial(_convert_tuple, converter=converter, name_transform=name_transform)
    origin_type = get_origin(type_)
    inner_types = [resolve(x) for x in get_args(type_)]

    if type_ in _implicit_iterable_type_mapping:
        return convert(_implicit_iterable_type_mapping[type_], token)

    if origin_type in (collections.abc.Iterable, collections.abc.Sequence):
        assert len(inner_types) == 1
        return convert(list[inner_types[0]], token)  # pyright: ignore[reportGeneralTypeIssues]
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        return convert(type_.__value__, token)
    elif is_union(origin_type):
        for t in inner_types:
            if t is NoneType:
                continue
            try:
                return convert(t, token)
            except Exception:
                pass
        else:
            if isinstance(token, Sequence):
                raise ValueError  # noqa: TRY004
            raise CoercionError(token=token, target_type=type_)
    elif origin_type is Literal:
        # Try coercing the token into each allowed Literal value (left-to-right).
        last_coercion_error = None
        for choice in get_args(type_):
            try:
                res = convert(type(choice), token)
            except CoercionError as e:
                last_coercion_error = e
                continue
            except Exception:
                continue
            if res == choice:
                return res
        else:
            if last_coercion_error:
                last_coercion_error.target_type = type_
                raise last_coercion_error
            else:
                raise CoercionError(token=token[0] if isinstance(token, Sequence) else token, target_type=type_)
    elif origin_type in _iterable_types:  # NOT including tuple
        count, _ = token_count(inner_types[0])
        if not isinstance(token, Sequence):
            raise ValueError
        if count > 1:
            gen = zip(*[iter(token)] * count)
        else:
            gen = token
        return origin_type(convert(inner_types[0], e) for e in gen)  # pyright: ignore[reportOptionalCall]
    elif origin_type is tuple:
        from cyclopts.argument import Token

        if isinstance(token, Token):
            # E.g. Tuple[str] (Annotation: tuple containing a single string)
            return convert_tuple(type_, token, converter=converter)
        else:
            return convert_tuple(type_, *token, converter=converter)
    elif isclass(type_) and issubclass(type_, Enum):
        if isinstance(token, Sequence):
            raise ValueError

        if converter is None:
            element_transformed = name_transform(token.value)
            for member in type_:
                if name_transform(member.name) == element_transformed:
                    return member
            raise CoercionError(token=token, target_type=type_)
        else:
            return converter(type_, token.value)
    else:
        # The actual casting/converting of the underlying type is performed here.
        if isinstance(token, Sequence):
            raise ValueError
        try:
            if converter is None:
                inner_value = token.value
                with suppress(ValueError):
                    first_argument_type = _first_argument_type(type_)
                    if first_argument_type is not str:
                        # Prevents infinite recursion
                        inner_value = convert(first_argument_type, token)
                return _converters.get(type_, type_)(inner_value)
            else:
                return converter(type_, token.value)
        except CoercionError as e:
            if e.target_type is None:
                e.target_type = type_
            if e.token is None:
                e.token = token
            raise
        except ValueError:
            raise CoercionError(token=token, target_type=type_) from None


def resolve(type_: Any) -> type:
    """Perform all simplifying resolutions."""
    if type_ is inspect.Parameter.empty:
        return str

    type_prev = None
    while type_ != type_prev:
        type_prev = type_
        type_ = resolve_annotated(type_)
        type_ = resolve_optional(type_)
        type_ = resolve_required(type_)
    return type_


def resolve_optional(type_: Any) -> type:
    """Only resolves Union's of None + one other type (i.e. Optional)."""
    # Python will automatically flatten out nested unions when possible.
    # So we don't need to loop over resolution.

    if not is_union(get_origin(type_)):
        return type_

    non_none_types = [t for t in get_args(type_) if t is not NoneType]
    if not non_none_types:  # pragma: no cover
        # This should never happen; python simplifies:
        #    ``Union[None, None] -> NoneType``
        raise ValueError("Union type cannot be all NoneType")
    elif len(non_none_types) == 1:
        type_ = non_none_types[0]
    elif len(non_none_types) > 1:
        return Union[tuple(resolve_optional(x) for x in non_none_types)]  # pyright: ignore
    else:
        raise NotImplementedError

    return type_


def resolve_annotated(type_: Any) -> type:
    if type(type_) is AnnotatedType:
        type_ = get_args(type_)[0]
    return type_


def resolve_required(type_: Any) -> type:
    if get_origin(type_) in (Required, NotRequired):
        type_ = get_args(type_)[0]
    return type_


def convert(
    type_: Any,
    tokens: Union[Sequence[str], Sequence["Token"], NestedCliArgs],
    converter: Optional[Callable[[type, str], Any]] = None,
    name_transform: Optional[Callable[[str], str]] = None,
):
    """Coerce variables into a specified type.

    Internally used to coercing string CLI tokens into python builtin types.
    Externally, may be useful in a custom converter.
    See Cyclopt's automatic coercion rules :doc:`/rules`.

    If ``type_`` **is not** iterable, then each element of ``tokens`` will be converted independently.
    If there is more than one element, then the return type will be a ``Tuple[type_, ...]``.
    If there is a single element, then the return type will be ``type_``.

    If ``type_`` **is** iterable, then all elements of ``tokens`` will be collated.

    Parameters
    ----------
    type_: Type
        A type hint/annotation to coerce ``*args`` into.
    tokens: Union[Sequence[str], NestedCliArgs]
        String tokens to coerce.
        Generally, either a list of strings, or a dictionary of list of strings (recursive).
        Each leaf in the dictionary tree should be a list of strings.
    converter: Optional[Callable[[Type, str], Any]]
        An optional function to convert tokens to the inner-most types.
        The converter should have signature:

        .. code-block:: python

            def converter(type_: type, value: str) -> Any:
                "Perform conversion of string token."

        This allows to use the :func:`convert` function to handle the the difficult task
        of traversing lists/tuples/unions/etc, while leaving the final conversion logic to
        the caller.
    name_transform: Optional[Callable[[str], str]]
        Currently only used for ``Enum`` type hints.
        A function that transforms enum names and CLI values into a normalized format.

        The function should have signature:

        .. code-block:: python

            def name_transform(s: str) -> str:
                "Perform name transform."

        where the returned value is the name to be used on the CLI.

        If ``None``, defaults to ``cyclopts.default_name_transform``.

    Returns
    -------
    Any
        Coerced version of input ``*args``.
    """
    from cyclopts.argument import Token

    if not tokens:
        raise ValueError

    if not isinstance(tokens, dict) and isinstance(tokens[0], str):
        tokens = tuple(Token(value=str(x)) for x in tokens)

    if name_transform is None:
        name_transform = default_name_transform

    convert_priv = partial(_convert, converter=converter, name_transform=name_transform)
    convert_tuple = partial(_convert_tuple, converter=converter, name_transform=name_transform)
    type_ = resolve(type_)

    if type_ is Any:
        type_ = str

    type_ = _implicit_iterable_type_mapping.get(type_, type_)

    origin_type = get_origin(type_)
    maybe_origin_type = origin_type or type_

    if origin_type is tuple:
        return convert_tuple(type_, *tokens)  # pyright: ignore
    elif maybe_origin_type in _iterable_types or origin_type is collections.abc.Iterable:
        return convert_priv(type_, tokens)  # pyright: ignore
    elif maybe_origin_type is dict:
        if not isinstance(tokens, dict):
            raise ValueError  # Programming error
        try:
            value_type = get_args(type_)[1]
        except IndexError:
            value_type = str
        dict_converted = {
            k: convert(value_type, v, converter=converter, name_transform=name_transform) for k, v in tokens.items()
        }
        return _converters.get(maybe_origin_type, maybe_origin_type)(**dict_converted)  # pyright: ignore
    elif isinstance(tokens, dict):
        raise ValueError(f"Dictionary of tokens provided for unknown {type_!r}.")  # Programming error
    else:
        if len(tokens) == 1:
            return convert_priv(type_, tokens[0])  # pyright: ignore
        else:
            return [convert_priv(type_, item) for item in tokens]  # pyright:ignore


def token_count(type_: Any) -> tuple[int, bool]:
    """The number of tokens after a keyword the parameter should consume.

    Parameters
    ----------
    type_: Type
        A type hint/annotation to infer token_count from if not explicitly specified.

    Returns
    -------
    int
        Number of tokens to consume.
    bool
        If this is ``True`` and positional, consume all remaining tokens.
        The returned number of tokens constitutes a single element of the iterable-to-be-parsed.
    """
    annotation = resolve(type_)
    origin_type = get_origin(annotation)

    if (origin_type or annotation) is tuple:
        args = get_args(annotation)
        if args:
            return sum(token_count(x)[0] for x in args if x is not ...), ... in args
        else:
            return 1, True
    elif (origin_type or annotation) is bool:
        return 0, False
    elif annotation in _iterable_types or (origin_type in _iterable_types and len(get_args(annotation)) == 0):
        return 1, True
    elif (origin_type in _iterable_types or origin_type is collections.abc.Iterable) and len(get_args(annotation)):
        return token_count(get_args(annotation)[0])[0], True
    else:
        return 1, False
