import collections.abc
import json
import operator
import re
import sys
import typing
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime, timedelta
from enum import Enum, Flag
from functools import partial, reduce
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
)

if sys.version_info >= (3, 12):
    from typing import TypeAliasType
else:
    TypeAliasType = None

from cyclopts.annotations import is_annotated, is_enum_flag, is_nonetype, is_union, resolve
from cyclopts.exceptions import CoercionError, ValidationError
from cyclopts.field_info import get_field_infos
from cyclopts.utils import UNSET, default_name_transform, grouper, is_builtin, is_class_and_subclass

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None

if TYPE_CHECKING:
    from cyclopts.argument import Token


_implicit_iterable_type_mapping: dict[type, type] = {
    Iterable: list[str],
    typing.Sequence: list[str],
    Sequence: list[str],
    frozenset: frozenset[str],
    list: list[str],
    set: set[str],
    tuple: tuple[str, ...],
}

ITERABLE_TYPES = {
    Iterable,
    typing.Sequence,
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
    elif "." in s:
        # Casting to a float first allows for things like "30.0"
        # We handle this conditionally because very large integers can lose
        # meaningful precision when cast to a float.
        return int(round(float(s)))
    else:
        return int(s)


def _bytes(s: str) -> bytes:
    return bytes(s, encoding="utf8")


def _bytearray(s: str) -> bytearray:
    return bytearray(_bytes(s))


def _date(s: str) -> date:
    """Parse a date string.

    Returns
    -------
    datetime.date
    """
    return date.fromisoformat(s)


def _datetime(s: str) -> datetime:
    """Parse a datetime string.

    Returns
    -------
    datetime.datetime
    """
    formats = [
        # ISO 8601 formats (unambiguous internationally)
        "%Y-%m-%d",  # 1956-01-31
        "%Y-%m-%dT%H:%M:%S",  # 1956-01-31T10:00:00
        "%Y-%m-%d %H:%M:%S",  # 1956-01-31 10:00:00
        "%Y-%m-%dT%H:%M:%S%z",  # 1956-01-31T10:00:00+0000
        "%Y-%m-%dT%H:%M:%S.%f",  # 1956-01-31T10:00:00.123456
        "%Y-%m-%dT%H:%M:%S.%f%z",  # 1956-01-31T10:00:00.123456+0000
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    raise ValueError


def _timedelta(s: str) -> timedelta:
    """Parse a timedelta string."""
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]

    matches = re.findall(r"((\d+\.\d+|\d+)([smhdwMy]))", s)

    if not matches:
        raise ValueError(f"Could not parse duration string: {s}")

    seconds = 0
    for _, value, unit in matches:
        value = float(value)
        if unit == "s":
            seconds += value
        elif unit == "m":
            seconds += value * 60
        elif unit == "h":
            seconds += value * 3600
        elif unit == "d":
            seconds += value * 86400
        elif unit == "w":
            seconds += value * 604800
        elif unit == "M":
            # Approximation: 1 month = 30 days
            seconds += value * 2592000
        elif unit == "y":
            # Approximation: 1 year = 365 days
            seconds += value * 31536000

    if negative:
        seconds = -seconds
    return timedelta(seconds=seconds)


def get_enum_member(
    type_: Any,
    token: Union["Token", str],
    name_transform: Callable[[str], str],
):
    """Match a token's value to an enum's member.

    Applies ``name_transform`` to both the value and the member.
    """
    from cyclopts.argument import Token

    is_token = isinstance(token, Token)
    value = token.value if is_token else token
    value_transformed = name_transform(value)
    for name, member in type_.__members__.items():
        if name_transform(name) == value_transformed:
            return member
    raise CoercionError(
        token=token if is_token else None,
        target_type=type_,
    )


def convert_enum_flag(
    enum_type: type[Flag],
    tokens: Iterable[str] | Iterable["Token"],
    name_transform: Callable[[str], str],
) -> Flag:
    """Convert tokens to a Flag enum value.

    Parameters
    ----------
    enum_type : type[Flag]
        The Flag enum type to convert to.
    tokens : Iterable[str] | Iterable[Token]
        The tokens to convert. Can be member names or :class:`Token` objects.
    name_transform : Callable[[str], str] | None
        Function to transform names for comparison.

    Returns
    -------
    Flag
        The combined flag value.

    Raises
    ------
    CoercionError
        If a token is not a valid flag member.
    """
    return reduce(
        operator.or_,
        (get_enum_member(enum_type, token, name_transform) for token in tokens),
        enum_type(0),
    )


# For types that need more logic than just invoking their type
_converters: dict[Any, Callable] = {
    bool: _bool,
    int: _int,
    bytes: _bytes,
    bytearray: _bytearray,
    date: _date,
    datetime: _datetime,
    timedelta: _timedelta,
}


def _convert_tuple(
    type_: type[Any],
    *tokens: "Token",
    converter: Callable[[type, str], Any] | None,
    name_transform: Callable[[str], str],
) -> tuple:
    convert = partial(_convert, converter=converter, name_transform=name_transform)
    inner_types = tuple(x for x in get_args(type_) if x is not ...)
    inner_token_count, consume_all = token_count(type_)
    # Elements like boolean-flags will have an inner_token_count of 0.
    inner_token_count = max(inner_token_count, 1)
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
        out = tuple(convert(inner_type, arg) for inner_type, arg in zip(inner_types, batched, strict=False))
    return out


def _convert_json(
    type_: Any,
    data: dict,
    field_infos: dict,
    converter: Callable | None,
    name_transform: Callable[[str], str],
):
    """Convert JSON dict to dataclass with proper type conversion for fields.

    Parameters
    ----------
    type_ : Type
        The dataclass type to create.
    data : dict
        The JSON dictionary containing field values.
    field_infos : dict
        Field information from the dataclass.
    converter : Callable | None
        Optional converter function.
    name_transform : Callable[[str], str]
        Function to transform field names.

    Returns
    -------
    Instance of type_ with properly converted field values.
    """
    from cyclopts.token import Token

    converted_data = {}
    for field_name, field_info in field_infos.items():
        if field_name in data:
            value = data[field_name]
            # Convert the value to the proper type
            if value is not None and not is_class_and_subclass(field_info.hint, str):
                # Create a token for the value and convert it
                token = Token(value=json.dumps(value) if isinstance(value, dict | list) else str(value))
                # Always attempt conversion, let errors propagate for consistency
                converted_value = convert(field_info.hint, [token], converter, name_transform)
            else:
                converted_value = value
            converted_data[field_name] = converted_value

    # Create the dataclass with converted values
    return type_(**converted_data)


def _create_json_decode_error_message(
    token: "Token",
    type_: Any,
    error: json.JSONDecodeError,
) -> str:
    """Create a helpful error message for JSON decode errors.

    Parameters
    ----------
    token : Token
        The token containing the invalid JSON.
    type_ : Type
        The target type we were trying to convert to.
    error : json.JSONDecodeError
        The JSON decode error that occurred.

    Returns
    -------
    str
        A formatted error message with context and hints.
    """
    value_str = token.value.strip()

    # Try to provide context around the error
    error_pos = error.pos if hasattr(error, "pos") else error.colno - 1 if hasattr(error, "colno") else 0

    # Create a snippet showing the error location
    snippet_start = max(0, error_pos - 20)
    snippet_end = min(len(value_str), error_pos + 20)
    snippet = value_str[snippet_start:snippet_end]

    # Add markers if we truncated
    if snippet_start > 0:
        snippet = "..." + snippet
    if snippet_end < len(value_str):
        snippet = snippet + "..."

    # Calculate where the error marker should point
    marker_pos = error_pos - snippet_start
    if snippet_start > 0:
        marker_pos += 3  # Account for "..."

    # Common error patterns with helpful hints
    hint = ""
    if re.search(r"\bTrue\b", value_str):
        hint = "\n    Hint: Use lowercase 'true' instead of Python's True"
    elif re.search(r"\bFalse\b", value_str):
        hint = "\n    Hint: Use lowercase 'false' instead of Python's False"
    elif re.search(r"\bNone\b", value_str):
        hint = "\n    Hint: Use 'null' instead of Python's None"
    elif "'" in value_str:
        hint = "\n    Hint: JSON requires double quotes, not single quotes"

    return f"Invalid JSON for {type_.__name__}:\n    {snippet}\n    {' ' * marker_pos}^ {error.msg}{hint}"


def _convert(
    type_,
    token: Union["Token", Sequence["Token"]],
    *,
    converter: Callable[[Any, str], Any] | None,
    name_transform: Callable[[str], str],
):
    """Inner recursive conversion function for public ``convert``.

    Parameters
    ----------
    converter: Callable
    name_transform: Callable
    """
    from cyclopts.argument import Token
    from cyclopts.parameter import Parameter

    converter_needs_token = False
    if is_annotated(type_):
        from cyclopts.parameter import Parameter

        type_, cparam = Parameter.from_annotation(type_)
        if cparam.converter:
            converter_needs_token = True

            def converter_with_token(t_, value):
                assert cparam.converter
                return cparam.converter(t_, (value,))

            converter = converter_with_token

        if cparam.name_transform:
            name_transform = cparam.name_transform
    else:
        cparam = None

    convert = partial(_convert, converter=converter, name_transform=name_transform)
    convert_tuple = partial(_convert_tuple, converter=converter, name_transform=name_transform)

    origin_type = get_origin(type_)
    # Inner types **may** be ``Annotated``
    inner_types = get_args(type_)

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
    elif origin_type in ITERABLE_TYPES:
        # NOT including tuple; handled in ``origin_type is tuple`` body above.
        count, _ = token_count(inner_types[0])
        if not isinstance(token, Sequence):
            raise ValueError

        # Check if tokens are JSON strings
        inner_type = inner_types[0]
        if (
            count > 1
            and any(isinstance(t, Token) and t.value.strip().startswith("{") for t in token)
            and inner_type is not str
        ):
            # Each token is a complete JSON representation of the dataclass
            gen = token
        elif count > 1:
            gen = zip(*[iter(token)] * count, strict=False)
        else:
            gen = token
        out = origin_type(convert(inner_types[0], e) for e in gen)  # pyright: ignore[reportOptionalCall]
    elif is_class_and_subclass(type_, Flag):
        # TODO: this might never execute since enum.Flag is now handled in ``convert``.
        out = convert_enum_flag(type_, token if isinstance(token, Sequence) else [token], name_transform)
    elif is_class_and_subclass(type_, Enum):
        if isinstance(token, Sequence):
            raise ValueError

        if converter is None:
            out = get_enum_member(type_, token, name_transform)
        else:
            out = converter(type_, token.value)
    else:
        field_infos = get_field_infos(type_)
        # Hope that if there is no field_info, that it takes `*args` and would be happy with a single ``str`` input.
        # This is common for many types, such as libraries that try to mimic pathlib.Path interface.
        # TODO: This doesn't respect the type-annotation of ``*args``.
        if is_builtin(type_) or not field_infos:
            assert isinstance(token, Token)
            try:
                if token.implicit_value is not UNSET:
                    out = token.implicit_value
                elif converter is None:
                    out = _converters.get(type_, type_)(token.value)  # pyright: ignore[reportOptionalCall]
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
            # First check if we have a single token that's a JSON string
            if isinstance(token, Token) and token.value.strip().startswith("{") and type_ is not str:
                try:
                    data = json.loads(token.value)
                    if not isinstance(data, dict):
                        # JSON was valid but didn't produce a dict (e.g., it was an array or scalar)
                        raise TypeError  # noqa: TRY301
                    # Convert dict to dataclass with proper type conversion
                    out = _convert_json(type_, data, field_infos, converter, name_transform)
                except json.JSONDecodeError as e:
                    # Create helpful error message for invalid JSON
                    msg = _create_json_decode_error_message(token, type_, e)
                    raise CoercionError(msg=msg, token=token, target_type=type_) from e
                except TypeError:
                    # Fall back to positional argument parsing
                    if not isinstance(token, Sequence):
                        token = [token]
                    i = 0
                    pos_values = []
                    hint = type_
                    for field_info in field_infos.values():
                        hint = field_info.hint
                        if is_class_and_subclass(hint, str):  # Avoids infinite recursion
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
            else:
                # Standard positional argument parsing
                if not isinstance(token, Sequence):
                    token = [token]
                i = 0
                pos_values = []
                hint = type_
                for field_info in field_infos.values():
                    hint = field_info.hint
                    if isclass(hint) and issubclass(hint, str):  # Avoids infinite recursion
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
        # An inner type may have an independent Parameter annotation;
        # e.g.:
        #    Uint8 = Annotated[int, ...]
        #    rgb: tuple[Uint8, Uint8, Uint8]
        try:
            for validator in cparam.validator:  # pyright: ignore
                validator(type_, out)
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(exception_message=e.args[0] if e.args else "", value=out) from e

    return out


def convert(
    type_: Any,
    tokens: Sequence[str] | Sequence["Token"] | NestedCliArgs,
    converter: Callable[[type, str], Any] | None = None,
    name_transform: Callable[[str], str] | None = None,
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
    elif is_enum_flag(maybe_origin_type):
        # Unlike other types that can accept multiple tokens, the result is not a sequence, it's a single
        # enum.Flag object.
        return convert_enum_flag(maybe_origin_type, tokens, name_transform)
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
    type_ = resolve(type_)
    origin_type = get_origin(type_)

    if (origin_type or type_) is tuple:
        args = get_args(type_)
        if args:
            return sum(token_count(x)[0] for x in args if x is not ...), ... in args
        else:
            return 1, True
    elif (origin_type or type_) is bool:
        return 0, False
    elif type_ in ITERABLE_TYPES or (origin_type in ITERABLE_TYPES and len(get_args(type_)) == 0):
        return 1, True
    elif is_enum_flag(type_):
        return 1, True
    elif (origin_type in ITERABLE_TYPES or origin_type is collections.abc.Iterable) and len(get_args(type_)):
        return token_count(get_args(type_)[0])[0], True
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        return token_count(type_.__value__)
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
        field_infos = get_field_infos(type_)
        count, consume_all = 0, False
        for value in field_infos.values():
            if value.kind is value.VAR_POSITIONAL:
                consume_all = True
            elif not value.required:
                continue
            elem_count, elem_consume_all = token_count(value.hint)
            count += elem_count
            consume_all |= elem_consume_all

        # classes like ``enum.Enum`` can slip through here with a 0 count.
        if not count:
            return 1, False

        return count, consume_all
