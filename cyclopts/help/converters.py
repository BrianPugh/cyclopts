from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import RenderableType

    from cyclopts.help import TableEntry


def asterisk_required_converter(entry: "TableEntry") -> "RenderableType":
    if entry.required:
        return "*"
    return ""


def combine_long_short_converter(entry: "TableEntry") -> "RenderableType":
    """Concatenate names and shorts.

    Examples
    --------
        names = ("--help",)
        shorts = ("-h",)
        return: "--help -h"
    """
    names_str = " ".join(entry.names) if entry.names else ""
    shorts_str = " ".join(entry.shorts) if entry.shorts else ""

    if names_str and shorts_str:
        return names_str + " " + shorts_str
    return names_str or shorts_str
