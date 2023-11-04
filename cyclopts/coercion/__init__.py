import builtins

__all__ = [
    "lookup",
]

from ._common import _bool as bool
from ._common import _int as int

lookup = {
    builtins.int: int,
    builtins.bool: bool,
}
