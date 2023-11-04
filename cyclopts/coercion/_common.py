from typing import Union


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
