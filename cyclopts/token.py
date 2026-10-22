import itertools
from typing import Any

from attrs import evolve, field

from cyclopts.utils import UNSET, frozen

_creation_order = itertools.count()


@frozen(kw_only=True)
class Token:
    """Tracks how a user supplied a value to the application."""

    keyword: str | None = None
    value: str = ""
    source: str = ""
    index: int = field(default=0, kw_only=True)
    keys: tuple[str, ...] = field(default=(), kw_only=True)
    implicit_value: Any = field(default=UNSET, kw_only=True)

    # Let a ``Foo | dict`` falling back to ``dict`` recover each key as typed, in input order.
    _option_name: str | None = field(default=None, alias="_option_name", eq=False, repr=False)
    """CLI-style option name (``--x.my-field``) of a config token, whose ``keyword`` is ``[x][my-field]``."""
    _order: int = field(factory=lambda: next(_creation_order), alias="_order", eq=False, repr=False)

    @property
    def address(self) -> tuple[tuple[str, ...], int]:
        """Hashable subkey destination address for this token."""
        return (self.keys, self.index)

    def evolve(self, **kwargs) -> "Token":
        # TODO: replace return-hint with Self cp311
        return evolve(self, **kwargs)
