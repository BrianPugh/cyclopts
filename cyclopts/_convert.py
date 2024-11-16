import collections.abc
import sys
from collections.abc import Sequence
from enum import Enum
from functools import partial
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Literal,
    Optional,
    Union,
    get_args,
    get_origin,
)

from cyclopts.annotations import is_annotated, is_nonetype, is_union, resolve
from cyclopts.exceptions import CoercionError, ValidationError
from cyclopts.field_info import get_field_infos
from cyclopts.utils import default_name_transform, grouper, is_builtin

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None

if TYPE_CHECKING:
    from cyclopts.argument import Token


_implicit_iterable_type_mapping: dict[type, type] = {
    Iterable: list[str],
    Sequence: list[str],
    frozenset: frozenset[str],
    list: list[str],
    set: set[str],
    tuple: tuple[str, ...],
}

ITERABLE_TYPES = {
    Iterable,
    Sequence,
    frozenset,
    list,
    set,
    tuple,
}

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
    elif s.startswith("0o"):
        return int(s, 8)
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
_converters: dict[Any, Callable] = {
    bool: _bool,
    int: _int,
    bytes: _bytes,
    bytearray: _bytearray,
}


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

        return tuple(
            convert(inner_type, chunk[0] if inner_token_count == 1 else chunk)
            for chunk in grouper(tokens, inner_token_count)
        )
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
    converter: Optional[Callable[[Any, str], Any]],
    name_transform: Callable[[str], str],
):
    """Inner recursive conversion function for public ``convert``.

    Parameters
    ----------
    converter: Callable
    name_transform: Callable
    """
    from cyclopts.argument import Token

    converter_needs_token = False
    if is_annotated(type_):
        from cyclopts.parameter import Parameter

        args = get_args(type_)
        type_ = args[0]
        cparam = Parameter.combine(*(x for x in args[1:] if isinstance(x, Parameter)))
        if cparam._converter:
            converter_needs_token = True
            converter = lambda t_, value: cparam._converter(t_, (value,))  # noqa: E731
        if cparam.name_transform:
            name_transform = cparam.name_transform
    else:
        cparam = None

    convert = partial(_convert, converter=converter, name_transform=name_transform)
    convert_tuple = partial(_convert_tuple, converter=converter, name_transform=name_transform)

    origin_type = get_origin(type_)
    inner_types = [resolve(x) for x in get_args(type_)]

    if type_ is dict:
        out = convert(dict[str, str], token)
    elif type_ in _implicit_iterable_type_mapping:
        out = convert(_implicit_iterable_type_mapping[type_], token)
    elif origin_type in (collections.abc.Iterable, collections.abc.Sequence):
        assert len(inner_types) == 1
        out = convert(list[inner_types[0]], token)  # pyright: ignore[reportGeneralTypeIssues]
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        out = convert(type_.__value__, token)
    elif is_union(origin_type):
        for t in inner_types:
            if is_nonetype(t):
                continue
            try:
                out = convert(t, token)
                break
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
            if res == choice:
                out = res
                break
        else:
            if last_coercion_error:
                last_coercion_error.target_type = type_
                raise last_coercion_error
            else:
                raise CoercionError(token=token[0] if isinstance(token, Sequence) else token, target_type=type_)
    elif origin_type is tuple:
        if isinstance(token, Token):
            # E.g. Tuple[str] (Annotation: tuple containing a single string)
            out = convert_tuple(type_, token, converter=converter)
        else:
            out = convert_tuple(type_, *token, converter=converter)
    elif origin_type in ITERABLE_TYPES:  # NOT including tuple
        count, _ = token_count(inner_types[0])
        if not isinstance(token, Sequence):
            raise ValueError
        if count > 1:
            gen = zip(*[iter(token)] * count)
        else:
            gen = token
        out = origin_type(convert(inner_types[0], e) for e in gen)  # pyright: ignore[reportOptionalCall]
    elif isclass(type_) and issubclass(type_, Enum):
        if isinstance(token, Sequence):
            raise ValueError

        if converter is None:
            element_transformed = name_transform(token.value)
            for member in type_:
                if name_transform(member.name) == element_transformed:
                    out = member
                    break
            else:
                raise CoercionError(token=token, target_type=type_)
        else:
            out = converter(type_, token.value)
    elif is_builtin(type_):
        assert isinstance(token, Token)
        try:
            if converter is None:
                out = _converters.get(type_, type_)(token.value)
            elif converter_needs_token:
                out = converter(type_, token)  # pyright: ignore[reportArgumentType]
            else:
                out = converter(type_, token.value)
        except CoercionError as e:
            if e.target_type is None:
                e.target_type = type_
            if e.token is None:
                e.token = token
            raise
        except ValueError:
            raise CoercionError(token=token, target_type=type_) from None
    else:
        # Convert it into a user-supplied class.
        if not isinstance(token, Sequence):
            token = [token]
        i = 0
        pos_values = []
        hint = type_
        for field_info in get_field_infos(type_, include_var_positional=True).values():
            hint = field_info.hint
            if hint is str:  # Avoids infinite recursion
                pos_values.append(token[i].value)
                i += 1
            else:
                tokens_per_element, consume_all = token_count(hint)
                if tokens_per_element == 1:
                    pos_values.append(convert(hint, token[i]))
                    i += 1
                else:
                    pos_values.append(convert(hint, token[i : i + tokens_per_element]))
                    i += tokens_per_element
                if consume_all:
                    break
            if i == len(token):
                break
        assert i == len(token)
        out = type_(*pos_values)

    if cparam:
        try:
            for validator in cparam.validator:  # pyright: ignore
                validator(type_, out)
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(exception_message=e.args[0] if e.args else "", value=out) from e

    return out


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
    elif maybe_origin_type in ITERABLE_TYPES or origin_type is collections.abc.Iterable:
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
        tokens_per_element, _ = token_count(type_)
        if tokens_per_element == 1:
            return [convert_priv(type_, item) for item in tokens]  # pyright: ignore
        elif len(tokens) == tokens_per_element:
            return convert_priv(type_, tokens)  # pyright: ignore
        else:
            raise NotImplementedError("Unreachable?")


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
    elif annotation in ITERABLE_TYPES or (origin_type in ITERABLE_TYPES and len(get_args(annotation)) == 0):
        return 1, True
    elif (origin_type in ITERABLE_TYPES or origin_type is collections.abc.Iterable) and len(get_args(annotation)):
        return token_count(get_args(annotation)[0])[0], True
    elif is_union(type_):
        sub_args = get_args(type_)
        token_count_target = token_count(sub_args[0])
        for sub_type_ in sub_args[1:]:
            this = token_count(sub_type_)
            if this != token_count_target:
                raise ValueError(
                    f"Cannot Union types that consume different numbers of tokens: {sub_args[0]} {sub_type_}"
                )
        return token_count_target
    elif is_builtin(type_):
        # Many builtins actually take in VAR_POSITIONAL when we really just want 1 argument.
        return 1, False
    else:
        # This is usually/always a custom user-defined class.
        field_infos = get_field_infos(type_, include_var_positional=True)
        count, consume_all = 0, False
        for value in field_infos.values():
            if value.kind is value.VAR_POSITIONAL:
                consume_all = True
            elif not value.required:
                continue
            elem_count, elem_consume_all = token_count(value.hint)
            count += elem_count
            consume_all |= elem_consume_all

        # classes like ``Enum`` can slip through here with a 0 count.
        if not count:
            return 1, False

        return count, consume_all
