import builtins

__all__ = [
    "lookup",
    "bool",
    "int",
    "bytes",
    "bytearray",
]

from ._common import (
    _bool as bool,
)
from ._common import (
    _bytearray as bytearray,
)
from ._common import (
    _bytes as bytes,
)
from ._common import (
    _int as int,
)

lookup = {
    builtins.int: int,
    builtins.bool: bool,
    builtins.bytes: bytes,
    builtins.bytearray: bytearray,
}
