from typing import Union


def coerce_bool(s: Union[str, bool]) -> bool:
    if isinstance(s, bool):
        return s

    s = s.lower()
    if s in {"no", "n", "0", "false", "f"}:
        return False
    return True


def coerce_int(s: str) -> int:
    return int(s, 0)


default_coercion_lookup = {
    int: coerce_int,
    bool: coerce_bool,
}
