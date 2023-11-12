from enum import Enum
from inspect import isclass
from typing import Literal, Union, get_args, get_origin

from typing_extensions import Annotated

from cyclopts.exceptions import CoercionError

# from types import NoneType is available >=3.10
NoneType = type(None)


def _bool(s: Union[str, bool]) -> bool:
    if isinstance(s, bool):
        return s

    s = s.lower()
    if s in {"no", "n", "0", "false", "f"}:
        return False
    return True


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
    if isinstance(type_, (list, tuple, set)):
        return type_(_convert(type_[0], e) for e in element)  # pyright: ignore[reportGeneralTypeIssues]
    elif origin_type is Union:
        return _convert(resolve_union(type_), element)
    elif origin_type is Literal:
        for choice in get_args(type_):
            try:
                res = _convert(type(choice), (element))
            except Exception:
                continue
            if res == choice:
                return res
        else:
            raise CoercionError(f"Error converting '{element}' to {type_}")
    elif isclass(type_) and issubclass(type_, Enum):
        element_lower = element.lower()
        for member in type_:
            if member.name.lower() == element_lower:
                return member
        raise CoercionError(f"Error converting '{element}' to {type_}")
    elif origin_type in [list, set]:
        return origin_type(_convert(inner_types[0], e) for e in element)
    elif origin_type is tuple:
        return tuple(_convert(t, e) for t, e in zip(inner_types, element))
    else:
        try:
            return _converters.get(type_, type_)(element)
        except ValueError as e:
            raise CoercionError(f"Error converting '{element}' to {type_}") from e


_unsupported_target_types = {dict}


def _get_origin_and_validate(type_):
    origin_type = get_origin(type_)
    if type_ in _unsupported_target_types:
        raise TypeError(f"Unsupported Type: {type_}")
    if origin_type in _unsupported_target_types:
        raise TypeError(f"Unsupported Type: {origin_type}")
    if type_ is tuple:
        raise TypeError("Tuple type hints must contain inner hints.")
    return origin_type


def resolve_union(type_):
    while get_origin(type_) is Union:
        non_none_types = [t for t in get_args(type_) if t is not NoneType]
        if not non_none_types:
            raise ValueError("Union type cannot be all NoneType")
        type_ = non_none_types[0]
    return type_


def resolve_annotated(type_):
    while get_origin(type_) is Annotated:
        type_ = get_args(type_)[0]
    return type_


def coerce(type_, *args):
    type_ = resolve_annotated(type_)
    type_ = resolve_union(type_)
    origin_type = _get_origin_and_validate(type_)

    if origin_type is tuple:
        inner_types = get_args(type_)
        if len(inner_types) != len(args):
            raise ValueError(
                f"Number of arguments does not match the tuple structure: expected {len(inner_types)} but got {len(args)}"
            )
        return tuple(_convert(inner_type, arg) for inner_type, arg in zip(inner_types, args))
    elif origin_type in [list, set]:
        return _convert(type_, args)
    elif len(args) == 1:
        return _convert(type_, args[0])
    else:
        return [_convert(type_, item) for item in args]


def token_count(type_: type) -> int:
    """The number of tokens after a keyword the parameter should consume.

    Returns ``-1`` if all remaining tokens should be consumed.
    """
    type_ = resolve_annotated(type_)
    origin_type = _get_origin_and_validate(type_)

    if origin_type is tuple:
        return len(get_args(type_))
    elif (origin_type or type_) is bool:
        return 0
    elif (origin_type or type_) in (list, set):
        return -1
    else:
        return 1
