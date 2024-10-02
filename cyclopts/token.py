from typing import Any, Optional

from attrs import field, frozen


@frozen(kw_only=True)
class Token:
    """
    Purely a dataclass containing factual book-keeping for a user input.
    """

    # Value like "--foo" or `--foo.bar.baz` that indicated token; ``None`` when positional.
    # Could also be something like "tool.project.foo" if `source=="config"`
    # or could be `TOOL_PROJECT_FOO` if coming from an `source=="env"`
    # **This should be pretty unadulterated from the user's input.**
    # Used ONLY for error message purposes.
    keyword: Optional[str] = None

    # Empty string when a flag. The parsed token value (unadulterated)
    # See ``Token.implicit_value``
    value: str = ""

    # Where the token came from; used for error message purposes.
    # Cyclopts specially uses "cli" for cli-parsed tokens.
    source: str = ""

    index: int = field(default=0, kw_only=True)

    # Only used for Arguments that take arbitrary keys.
    keys: tuple[str, ...] = field(default=(), kw_only=True)

    implicit_value: Any = field(default=None, kw_only=True)
