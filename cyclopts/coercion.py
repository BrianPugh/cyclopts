import builtins
from typing import Union

__all__ = [
    "bool",
    "int",
    "default_coercion_lookup",
]


def bool(s: Union[str, builtins.bool]) -> bool:
    if isinstance(s, builtins.bool):
        return s

    s = s.lower()
    if s in {"no", "n", "0", "false", "f"}:
        return False
    return True


def int(s: str) -> int:
    return builtins.int(s, 0)


default_coercion_lookup = {
    builtins.int: int,
    builtins.bool: bool,
}
