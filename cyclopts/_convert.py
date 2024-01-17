import collections.abc
import inspect
import sys
from enum import Enum
from functools import partial
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from cyclopts.utils import is_iterable

if sys.version_info < (3, 9):
    from typing_extensions import Annotated  # pragma: no cover
else:
    from typing import Annotated  # pragma: no cover

_union_types = set()
_union_types.add(Union)
if sys.version_info >= (3, 10):
    from types import UnionType

    _union_types.add(UnionType)

from cyclopts.exceptions import CoercionError

if TYPE_CHECKING:
    from cyclopts.parameter import Parameter

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


def _convert(type_, element, converter=None):
    pconvert = partial(_convert, converter=converter)
    origin_type = get_origin(type_)
    inner_types = [resolve(x) for x in get_args(type_)]

    if type_ in _implicit_iterable_type_mapping:
        return pconvert(_implicit_iterable_type_mapping[type_], element)

    if origin_type is collections.abc.Iterable:
        assert len(inner_types) == 1
        return pconvert(List[inner_types[0]], element)  # pyright: ignore[reportGeneralTypeIssues]
    elif origin_type in _union_types:
        for t in inner_types:
            if t is NoneType:
                continue
            try:
                return pconvert(t, element)
            except Exception:
                pass
        else:
            raise CoercionError(input_value=element, target_type=type_)
    elif origin_type is Literal:
        for choice in get_args(type_):
            try:
                res = pconvert(type(choice), (element))
            except Exception:
                continue
            if res == choice:
                return res
        else:
            raise CoercionError(input_value=element, target_type=type_)
    elif origin_type in _iterable_types:  # NOT including tuple
        count, _ = token_count(inner_types[0])
        if count > 1:
            gen = zip(*[iter(element)] * count)
        else:
            gen = element
        return origin_type(pconvert(inner_types[0], e) for e in gen)  # pyright: ignore[reportOptionalCall]
    elif origin_type is tuple:
        return tuple(pconvert(t, e) for t, e in zip(inner_types, element))
    elif isclass(type_) and issubclass(type_, Enum):
        if converter is None:
            element_lower = element.lower().replace("-", "_")
            for member in type_:
                if member.name.lower().strip("_") == element_lower:
                    return member
            raise CoercionError(input_value=element, target_type=type_)
        else:
            return converter(type_, element)
    else:
        # The actual casting/converting of the underlying type is performed here.
        try:
            if converter is None:
                return _converters.get(type_, type_)(element)
            else:
                return converter(type_, element)
        except ValueError:
            raise CoercionError(input_value=element, target_type=type_) from None


_unsupported_target_types = {dict}


def get_origin_and_validate(type_: Type):
    origin_type = get_origin(type_)
    if origin_type is None:
        if type_ in _unsupported_target_types:
            raise TypeError(f"Unsupported Type: {type_}")
    else:
        if origin_type in _unsupported_target_types:
            raise TypeError(f"Unsupported Type: {type_}")
    return origin_type


def resolve(type_: Type) -> Type:
    """Perform all simplifying resolutions."""
    if type_ is inspect.Parameter.empty:
        return str

    type_prev = None
    while type_ != type_prev:
        type_prev = type_
        type_ = resolve_annotated(type_)
        type_ = resolve_optional(type_)
    return type_


def resolve_optional(type_: Type) -> Type:
    """Only resolves Union's of None + one other type (i.e. Optional)."""
    # Python will automatically flatten out nested unions when possible.
    # So we don't need to loop over resolution.

    if get_origin(type_) not in _union_types:
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


def resolve_annotated(type_: Type) -> Type:
    if type(type_) is AnnotatedType:
        type_ = get_args(type_)[0]
    return type_


def convert(type_: Type[Any], *args: str, converter: Optional[Callable] = None):
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
    converter: Optional[Callable]

        An optional function to convert tokens to the inner-most types.
        The converter should have signature:

        .. code-block:: python

            def converter(type_: type, value: str) -> Any:
                ...

        This allows to use the :func:`convert` function to handle the the difficult task
        of traversing lists/tuples/unions/etc, while leaving the final conversion logic to
        the caller.

    Returns
    -------
    Any
        Coerced version of input ``*args``.
    """
    if type_ is inspect.Parameter.empty:
        type_ = str

    type_ = resolve(type_)

    if type_ is Any:
        type_ = str

    origin_type = get_origin_and_validate(type_)

    if origin_type is tuple:
        inner_types = tuple(x for x in get_args(type_) if x is not ...)
        inner_token_count, consume_all = token_count(type_)
        if consume_all:
            # variable-length tuple (list-like)
            remainder = len(args) % inner_token_count
            if remainder:
                raise CoercionError(
                    msg=f"Incorrect number of arguments: expected multiple of {inner_token_count} but got {len(args)}."
                )
            if len(inner_types) == 1:
                inner_type = inner_types[0]
            elif len(inner_types) == 0:
                inner_type = str
            else:
                raise ValueError("A tuple must have 0 or 1 inner-types.")

            if inner_token_count == 1:
                out = tuple(_convert(inner_type, x, converter=converter) for x in args)
            else:
                out = tuple(
                    _convert(inner_type, args[i : i + inner_token_count], converter=converter)
                    for i in range(0, len(args), inner_token_count)
                )
            return out
        else:
            # Fixed-length tuple
            if inner_token_count != len(args):
                raise CoercionError(
                    msg=f"Incorrect number of arguments: expected {inner_token_count} but got {len(args)}."
                )
            args_per_convert = [token_count(x)[0] for x in inner_types]
            it = iter(args)
            batched = [[next(it) for _ in range(size)] for size in args_per_convert]
            batched = [elem[0] if len(elem) == 1 else elem for elem in batched]
            out = tuple(_convert(inner_type, arg, converter=converter) for inner_type, arg in zip(inner_types, batched))
        return out
    elif (origin_type or type_) in _iterable_types or origin_type is collections.abc.Iterable:
        return _convert(type_, args, converter=converter)
    elif len(args) == 1:
        return _convert(type_, args[0], converter=converter)
    else:
        return [_convert(type_, item, converter=converter) for item in args]


def token_count(type_: Union[Type[Any], inspect.Parameter]) -> Tuple[int, bool]:
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
    from cyclopts.parameter import get_hint_parameter

    annotation = get_hint_parameter(type_)[0]

    annotation = resolve(annotation)
    origin_type = get_origin_and_validate(annotation)

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


def to_tuple_converter(value: Union[None, Any, Iterable[Any]]) -> Tuple[Any, ...]:
    """Convert a single element or an iterable of elements into a tuple.

    Intended to be used in an ``attrs.Field``. If ``None`` is provided, returns an empty tuple.
    If a single element is provided, returns a tuple containing just that element.
    If an iterable is provided, converts it into a tuple.

    Parameters
    ----------
    value: Optional[Union[Any, Iterable[Any]]]
        An element, an iterable of elements, or None.

    Returns
    -------
    Tuple[Any, ...]: A tuple containing the elements.
    """
    if value is None:
        return ()
    elif is_iterable(value):
        return tuple(value)
    else:
        return (value,)


def to_list_converter(value: Union[None, Any, Iterable[Any]]) -> List[Any]:
    return list(to_tuple_converter(value))


def optional_to_tuple_converter(value: Union[None, Any, Iterable[Any]]) -> Optional[Tuple[Any, ...]]:
    """Convert a string or Iterable or None into an Iterable or None.

    Intended to be used in an ``attrs.Field``.
    """
    if value is None:
        return None

    if not value:
        return ()

    return to_tuple_converter(value)
