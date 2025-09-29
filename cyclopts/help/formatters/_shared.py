"""Shared utilities for help formatters and documentation generators."""

import io
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console


def extract_plain_text(obj: Any, console: Optional["Console"] = None, preserve_markup: bool = False) -> str:
    """Extract plain text from Rich renderables or any object.

    Parameters
    ----------
    obj : Any
        Object to convert to plain text.
    console : Optional[Console]
        Console for rendering Rich objects.
    preserve_markup : bool
        If True, preserve original markdown/RST markup when available.
        Should be True when input and output formats match.

    Returns
    -------
    str
        Plain text representation.
    """
    if obj is None:
        return ""

    if hasattr(obj, "primary_renderable"):
        if preserve_markup and hasattr(obj.primary_renderable, "markup"):
            return obj.primary_renderable.markup.rstrip()
        return extract_plain_text(obj.primary_renderable, console, preserve_markup=preserve_markup)

    if hasattr(obj, "plain"):
        return obj.plain.rstrip()

    if preserve_markup and hasattr(obj, "markup"):
        return obj.markup.rstrip()

    if hasattr(obj, "__rich_console__"):
        from rich.console import Console

        plain_console = Console(
            file=io.StringIO(),
            width=console.width if console else 120,
            force_terminal=False,
            no_color=True,
            highlight=False,
            markup=False,
            emoji=False,
        )
        with plain_console.capture() as capture:
            plain_console.print(obj, end="")
        return capture.get().rstrip()

    return str(obj).rstrip()


def make_rst_section_header(title: str, level: int) -> list[str]:
    """Create an RST section header.

    Parameters
    ----------
    title : str
        Section title.
    level : int
        Heading level (1-6).

    Returns
    -------
    List[str]
        RST formatted section header lines.
    """
    markers = {
        1: "=",
        2: "-",
        3: "^",
        4: '"',
        5: "'",
        6: "~",
    }

    if level < 1:
        level = 1
    elif level > 6:
        level = 6

    marker = markers[level]
    underline = marker * len(title)

    if level == 1:
        return [underline, title, underline]
    else:
        return [title, underline]


def escape_rst(text: str | None) -> str:
    """Escape special reStructuredText characters in text.

    Parameters
    ----------
    text : Optional[str]
        Text to escape. Can be None.

    Returns
    -------
    str
        Escaped text safe for RST.
    """
    if not text:
        return ""
    return text.replace("\\", "\\\\")


def escape_markdown(text: str | None) -> str | None:
    """Escape special markdown characters in text.

    Parameters
    ----------
    text : Optional[str]
        Text to escape. Can be None.

    Returns
    -------
    Optional[str]
        Escaped text safe for markdown, or None if input was None.
    """
    if not text:
        return text

    if any(pattern in text for pattern in ["**", "*", "`", "[", "]", "#"]):
        return text

    text = text.replace("|", "\\|")
    return text


def escape_html(text: str | None) -> str:
    """Escape special HTML characters in text.

    Parameters
    ----------
    text : Optional[str]
        Text to escape. Can be None.

    Returns
    -------
    str
        Escaped text safe for HTML.
    """
    if not text:
        return ""

    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    return text
