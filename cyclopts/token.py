from typing import Any, Optional

from attrs import field, frozen

from cyclopts.utils import UNSET


@frozen(kw_only=True)
class Token:
    """Tracks how a user supplied a value to the application."""

    keyword: Optional[str] = None
    value: str = ""
    source: str = ""
    index: int = field(default=0, kw_only=True)
    keys: tuple[str, ...] = field(default=(), kw_only=True)
    implicit_value: Any = field(default=UNSET, kw_only=True)
