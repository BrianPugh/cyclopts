"""Markup and format conversion utilities.

Pure utility layer for text processing across help and docs systems.
"""

import io
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console
    from rich.console import Group as RichGroup


def _indent_text(text: str, left: int) -> str:
    """Prepend *left* spaces to each non-empty line of *text*."""
    indent = " " * left
    return "\n".join(indent + line if line else line for line in text.split("\n"))


def _extract_group_text(group: "RichGroup", console: Optional["Console"], preserve_markup: bool) -> str:
    r"""Extract text from a :class:`rich.console.Group`.

    Unlike the main :func:`extract_text` path (which ``rstrip``\\s each
    result), this function preserves inter-element spacing so that blank
    lines between sections survive the round-trip.  It reconstructs
    spacing by:

    * reading ``.markup`` directly (skipping rstrip) for InlineText children,
    * normalising to ``"\\n\\n"`` for ``force_empty_end``, and
    * appending ``"\\n"`` after Padding content.
    """
    from rich.console import NewLine
    from rich.padding import Padding

    parts: list[str] = []
    for child in group.renderables:
        if isinstance(child, NewLine):
            parts.append("\n" * child.count)
        elif isinstance(child, Padding):
            inner = extract_text(child.renderable, console, preserve_markup)
            if child.left and not preserve_markup:
                inner = _indent_text(inner, child.left)
            parts.append(inner + "\n")
        elif hasattr(child, "primary_renderable"):
            primary = getattr(child, "primary_renderable", None)
            if primary is not None:
                if preserve_markup and hasattr(primary, "markup"):
                    text = primary.markup
                else:
                    text = extract_text(primary, console, preserve_markup)
                if getattr(child, "force_empty_end", False):
                    text = text.rstrip("\n") + "\n\n"
                parts.append(text)
            else:
                parts.append(extract_text(child, console, preserve_markup))
        else:
            parts.append(extract_text(child, console, preserve_markup))
    return "".join(parts).rstrip()


def extract_text(obj: Any, console: Optional["Console"] = None, preserve_markup: bool = False) -> str:
    """Extract text from Rich renderables or any object.

    Parameters
    ----------
    obj : Any
        Object to convert to text.
    console : Console | None
        Console for rendering Rich objects.
    preserve_markup : bool
        If True, preserve original markdown/RST markup when available.
        When False, always render to plain text.

    Returns
    -------
    str
        Text representation (plain or with markup preserved).
    """
    from rich.console import Group as RichGroup
    from rich.console import NewLine
    from rich.padding import Padding

    if obj is None:
        return ""

    if isinstance(obj, RichGroup):
        return _extract_group_text(obj, console, preserve_markup)

    if isinstance(obj, Padding):
        inner = extract_text(obj.renderable, console, preserve_markup)
        if obj.left and not preserve_markup:
            inner = _indent_text(inner, obj.left)
        return inner

    if isinstance(obj, NewLine):
        return "\n" * obj.count

    if hasattr(obj, "primary_renderable"):
        primary = getattr(obj, "primary_renderable", None)
        if primary is not None:
            if preserve_markup and hasattr(primary, "markup"):
                return primary.markup.rstrip()
            return extract_text(primary, console, preserve_markup=preserve_markup)

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


def escape_rst(text: str | None) -> str:
    """Escape special reStructuredText characters in text.

    Parameters
    ----------
    text : str | None
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

    If the text appears to already contain markdown formatting (bold, italic,
    code, links, or headings), it is returned unchanged. Otherwise, pipe
    characters are escaped for table compatibility.

    Parameters
    ----------
    text : str | None
        Text to escape. Can be None.

    Returns
    -------
    str | None
        Escaped text safe for markdown, or None if input was None.
    """
    if not text:
        return text

    if any(pattern in text for pattern in ["**", "``", "`", "](", "#"]):
        return text

    text = text.replace("|", "\\|")
    return text


def escape_html(text: str | None) -> str:
    """Escape special HTML characters in text.

    Parameters
    ----------
    text : str | None
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
