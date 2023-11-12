from collections.abc import Iterable
from enum import Enum, auto
from inspect import isclass
from pathlib import Path
from typing import List, Literal, Set, Tuple, Union, get_args, get_origin

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
        return _convert(_resolve_union(type_), element)
    elif origin_type is Literal:
        for choice in get_args(type_):
            try:
                res = _convert(type(choice), (element))
            except Exception:
                continue
            if res == choice:
                return res
        else:
            raise ValueError(f"Error converting '{element}' to {type_}")
    elif isclass(type_) and issubclass(type_, Enum):
        element_lower = element.lower()
        for member in type_:
            if member.name.lower() == element_lower:
                return member
        raise ValueError(f"Error converting '{element}' to {type_}")
    elif origin_type in [list, set]:
        return origin_type(_convert(inner_types[0], e) for e in element)
    elif origin_type is tuple:
        return tuple(_convert(t, e) for t, e in zip(inner_types, element))
    else:
        try:
            return _converters.get(type_, type_)(element)
        except ValueError as e:
            raise ValueError(f"Error converting '{element}' to {type_}") from e


_unsupported_target_types = {dict}


def _get_origin_and_validate(type_):
    origin_type = get_origin(type_)
    if type_ in _unsupported_target_types:
        raise ValueError(f"Unsupported Type: {type_}")
    if origin_type in _unsupported_target_types:
        raise ValueError(f"Unsupported Type: {origin_type}")
    if type_ is tuple:
        raise ValueError("Tuple type hints must contain inner hints.")
    return origin_type


def _resolve_union(type_):
    while get_origin(type_) is Union:
        non_none_types = [t for t in get_args(type_) if t is not NoneType]
        if not non_none_types:
            raise ValueError("Union type cannot be all NoneType")
        type_ = non_none_types[0]
    return type_


def coerce(target_type, *args):
    origin_target_type = _get_origin_and_validate(target_type)

    if origin_target_type is tuple:
        inner_types = get_args(target_type)
        if len(inner_types) != len(args):
            raise ValueError(
                f"Number of arguments does not match the tuple structure: expected {len(inner_types)} but got {len(args)}"
            )
        return tuple(_convert(inner_type, arg) for inner_type, arg in zip(inner_types, args))
    elif origin_target_type in [list, set]:
        return _convert(target_type, args)
    elif origin_target_type is Union:
        target_type = _resolve_union(target_type)
        return [_convert(target_type, item) for item in args]
    elif len(args) == 1:
        return _convert(target_type, args[0])
    else:
        return [_convert(target_type, item) for item in args]


def token_count(type_) -> int:
    """The number of tokens after a keyword the parameter should consume."""
    origin_type = _get_origin_and_validate(type_)
    if origin_type is tuple:
        return len(get_args(type_))
    elif origin_type is bool or type_ is bool:
        return 0
    else:
        return 1


# Example Usage
assert 0 == token_count(bool)
assert 1 == token_count(int)
assert 1 == token_count(Union[None, int])
assert 1 == token_count(List[int])
assert 3 == token_count(Tuple[int, int, int])

# Example Usage
assert {1, 2, 3} == coerce(Set[Union[int, str]], "1", "2", "3")
assert "foo" == coerce(Literal["foo", "bar", 3], "foo")
assert "bar" == coerce(Literal["foo", "bar", 3], "bar")
assert 3 == coerce(Literal["foo", "bar", 3], "3")
assert 1 == coerce(int, "1")

assert [123, 456] == coerce(int, "123", "456")
assert [123, 456] == coerce(List[int], "123", "456")
assert {123, 456} == coerce(Set[int], "123", "456")
assert {"123", "456"} == coerce(Set[str], "123", "456")
assert {123, 456} == coerce(Set[Union[int, str]], "123", "456")
assert Path("foo") == coerce(Path, "foo")
assert True is coerce(bool, "true")
assert False is coerce(bool, "false")


def assert_tuple(expected, actual):
    assert type(actual) == tuple
    assert len(expected) == len(actual)
    for e, a in zip(expected, actual):
        assert type(e) == type(a)
        assert e == a


assert_tuple((1, 2.0), coerce(Tuple[int, Union[None, float, int]], "1", "2"))


class SoftwareEnvironment(Enum):
    DEV = auto()
    STAGING = auto()
    PROD = auto()


assert SoftwareEnvironment.STAGING == coerce(SoftwareEnvironment, "staging")
