import inspect
import sys
from inspect import isclass
from typing import Annotated, Any, Optional, Union, get_args, get_origin

import attrs

_IS_PYTHON_3_8 = sys.version_info[:2] == (3, 8)
_union_types = set()
_union_types.add(Union)

if sys.version_info >= (3, 10):  # pragma: no cover
    from types import UnionType

    _union_types.add(UnionType)

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import NotRequired, Required
else:  # pragma: no cover
    from typing import NotRequired, Required

# from types import NoneType is available >=3.10
NoneType = type(None)
AnnotatedType = type(Annotated[int, 0])


def is_nonetype(hint):
    return hint is NoneType


def is_union(type_: Optional[type]) -> bool:
    return type_ in _union_types or get_origin(type_) in _union_types


def is_pydantic(hint) -> bool:
    return hasattr(hint, "__pydantic_core_schema__")


def is_dataclass(hint) -> bool:
    return hasattr(hint, "__dataclass_fields__")


def is_namedtuple(hint) -> bool:
    return isclass(hint) and issubclass(hint, tuple) and hasattr(hint, "_fields")


def is_attrs(hint) -> bool:
    return attrs.has(hint)


def is_annotated(hint) -> bool:
    return type(hint) is AnnotatedType


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
        type_ = resolve_new_type(type_)
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


def resolve_new_type(type_: Any) -> type:
    try:
        return resolve_new_type(type_.__supertype__)
    except AttributeError:
        return type_


def get_hint_name(hint) -> str:
    if isinstance(hint, str):
        return hint
    if is_nonetype(hint):
        return "None"
    if hint is Any:
        return "Any"
    if is_union(hint):
        return "|".join(get_hint_name(arg) for arg in get_args(hint))
    if origin := get_origin(hint):
        out = get_hint_name(origin)
        if args := get_args(hint):
            out += "[" + ", ".join(get_hint_name(arg) for arg in args) + "]"
        return out
    if hasattr(hint, "__name__"):
        return hint.__name__
    if getattr(hint, "_name", None) is not None:
        return hint._name
    return str(hint)
