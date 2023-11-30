import collections.abc
import inspect
from enum import Enum
from inspect import isclass
from typing import Any, List, Literal, Set, Tuple, Type, Union, get_args, get_origin

from typing_extensions import Annotated

from cyclopts.exceptions import CoercionError

# from types import NoneType is available >=3.10
NoneType = type(None)
AnnotatedType = type(Annotated[int, 0])

_implicit_iterable_type_mapping = {
    list: List[str],
    set: Set[str],
}

_iterable_types = {list, set}


def _bool(s: str) -> bool:
    s = s.lower()
    if s in {"no", "n", "0", "false", "f"}:
        return False
    elif s in {"yes", "y", "1", "true", "t"}:
        return True
    else:
        raise CoercionError(target_type=bool, input_value=s)


def _int(s: str) -> int:
    s = s.lower()
    if s.startswith("0x"):
        return int(s, 16)
    elif s.startswith("0b"):
        return int(s, 2)
    else:
        return int(s, 0)


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


def _convert(type_, element):
    origin_type = get_origin(type_)
    inner_types = get_args(type_)

    if type_ in _implicit_iterable_type_mapping:
        return _convert(_implicit_iterable_type_mapping[type_], element)
    elif origin_type is collections.abc.Iterable:
        assert len(inner_types) == 1
        return _convert(List[inner_types[0]], element)  # pyright: ignore[reportGeneralTypeIssues]

    elif origin_type is Union:
        for t in inner_types:
            if t is NoneType:
                continue
            try:
                return _convert(t, element)
            except Exception:
                pass
        else:
            raise CoercionError(input_value=element, target_type=type_)
    elif origin_type is Literal:
        for choice in get_args(type_):
            try:
                res = _convert(type(choice), (element))
            except Exception:
                continue
            if res == choice:
                return res
        else:
            raise CoercionError(input_value=element, target_type=type_)
    elif isclass(type_) and issubclass(type_, Enum):
        element_lower = element.lower().replace("-", "_")
        for member in type_:
            if member.name.lower().strip("_") == element_lower:
                return member
        raise CoercionError(input_value=element, target_type=type_)
    elif origin_type in _iterable_types:
        count, _ = token_count(inner_types[0])
        if count > 1:
            gen = zip(*[iter(element)] * count)
        else:
            gen = element
        return origin_type(_convert(inner_types[0], e) for e in gen)  # pyright: ignore[reportOptionalCall]
    elif origin_type is tuple:
        return tuple(_convert(t, e) for t, e in zip(inner_types, element))
    else:
        try:
            return _converters.get(type_, type_)(element)
        except ValueError:
            raise CoercionError(input_value=element, target_type=type_) from None


_unsupported_target_types = {dict}


def get_origin_and_validate(type_: Type):
    origin_type = get_origin(type_)
    if type_ in _unsupported_target_types:
        raise TypeError(f"Unsupported Type: {type_}")
    if origin_type in _unsupported_target_types:
        raise TypeError(f"Unsupported Type: {origin_type}")
    if type_ is tuple:
        raise TypeError("Tuple type hints must contain inner hints.")
    return origin_type


def resolve(type_: Type) -> Type:
    """Perform all simplifying resolutions."""
    type_prev = None
    while type_ != type_prev:
        type_prev = type_
        type_ = resolve_annotated(type_)
        type_ = resolve_union(type_)
    return type_


def resolve_union(type_: Type) -> Type:
    """Only resolves Union's of None + one other type (i.e. Optional)."""
    while get_origin(type_) is Union:
        non_none_types = [t for t in get_args(type_) if t is not NoneType]
        if not non_none_types:
            # This should never happen; python simplifies:
            #    ``Union[None, None] -> NoneType``
            raise ValueError("Union type cannot be all NoneType")
        elif len(non_none_types) == 1:
            type_ = non_none_types[0]
        elif len(non_none_types) > 1:
            return Union[tuple(resolve_union(x) for x in non_none_types)]  # pyright: ignore
    return type_


def resolve_annotated(type_: Type) -> Type:
    if type(type_) is AnnotatedType:
        type_ = get_args(type_)[0]
    return type_


def coerce(type_: Type, *args: str):
    """Coerce variables into a specified type.

    Internally used to coercing string CLI tokens into python builtin types.
    Externally, may be useful in a custom converter.
    See Cyclopt's automatic coercion rules :doc:`/rules`.

    If ``type_`` **is not** iterable, then each element of ``*args`` will be converted independently.
    If there is more than one element, then the return type will be a ``Tuple[type_, ...]``.
    If there is a single element, then the return type will be ``type_``.

    If ``type_`` **is** iterable, then all elements of ``*args`` will be collated.

    Parameters
    ----------
    type_: Type
        A type hint/annotation to coerce ``*args`` into.
    `*args`: str
        String tokens to coerce.

    Returns
    -------
    Any
        Coerced version of input ``*args``.
    """
    if type_ is inspect.Parameter.empty:
        type_ = str

    type_ = resolve_annotated(type_)

    if type_ is Any:
        type_ = str

    origin_type = get_origin_and_validate(type_)

    if origin_type is tuple:
        inner_types = get_args(type_)
        if len(inner_types) != len(args):
            raise ValueError(
                f"Number of arguments does not match the tuple structure: expected {len(inner_types)} but got {len(args)}"
            )
        return tuple(_convert(inner_type, arg) for inner_type, arg in zip(inner_types, args))
    elif (origin_type or type_) in _iterable_types or origin_type is collections.abc.Iterable:
        return _convert(type_, args)
    elif len(args) == 1:
        return _convert(type_, args[0])
    else:
        return [_convert(type_, item) for item in args]


def token_count(type_: Type) -> Tuple[int, bool]:
    """The number of tokens after a keyword the parameter should consume.

    Returns
    -------
    int
        Number of tokens that constitute a single element.
    bool
        If this is ``True`` and positional, consume all remaining tokens.
    """
    from cyclopts.parameter import get_hint_parameter

    if type_ is inspect.Parameter.empty:
        return 1, False

    type_, param = get_hint_parameter(type_)
    if param.token_count is not None:
        return abs(param.token_count), param.token_count < 0

    type_ = resolve_annotated(type_)
    origin_type = get_origin_and_validate(type_)

    if origin_type is tuple:
        return len(get_args(type_)), False
    elif (origin_type or type_) is bool:
        return 0, False
    elif type_ in _iterable_types or (origin_type in _iterable_types and len(get_args(type_)) == 0):
        return 1, True
    elif (origin_type in _iterable_types or origin_type is collections.abc.Iterable) and len(get_args(type_)):
        return token_count(get_args(type_)[0])[0], True
    else:
        return 1, False
