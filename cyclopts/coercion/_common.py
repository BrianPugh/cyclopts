import inspect
import typing
from typing import Callable, Literal, Tuple, Union

from cyclopts.parameter import get_hint_parameter
from cyclopts.typing import is_iterable_type_hint


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


_lookup = {
    int: _int,
    bool: _bool,
    bytes: _bytes,
    bytearray: _bytearray,
    # typing.Literal:
}


class Pipeline(list):
    def __call__(self, value):
        for f in self:
            value = f(value)
        return value


def get_coercion(parameter: inspect.Parameter) -> Tuple[Callable, bool]:
    """Get the coercion function, and whether or not the type is iterable."""
    is_iterable = False
    hint, param = get_hint_parameter(parameter)

    if is_iterable_type_hint(hint):
        is_iterable = True
        hint = typing.get_args(hint)[0]

    if param.coercion:
        coercion = [param.coercion] if callable(param.coercion) else param.coercion
        coercion = Pipeline(coercion)
        return coercion, is_iterable

    if typing.get_origin(hint) is Literal:
        choices = typing.get_args(hint)
        # TODO: get type of first non-None choice
        raise NotImplementedError

    hint = typing.get_origin(hint) or hint
    coercion = _lookup.get(hint, hint)
    coercion = [coercion] if callable(coercion) else coercion
    coercion = Pipeline(coercion)

    return coercion, is_iterable
