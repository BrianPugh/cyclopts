from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import RenderableType

    from cyclopts.help import AbstractTableEntry


def asterisk_required_converter(out: "RenderableType", entry: "AbstractTableEntry") -> "RenderableType":
    if entry.required:
        return "*"
    return ""


def stretch_name_converter(out: "RenderableType", entry: "AbstractTableEntry") -> "RenderableType":
    """Split name into two parts based on --.

    Example
    -------
        '--foo--no-foo'  to '--foo --no-foo'.
    """
    if entry.name is None:
        return ""
    out = " --".join(entry.name.split("--"))
    return out[1:] if out[0] == " " else out


def combine_long_short_converter(out: "RenderableType", entry: "AbstractTableEntry") -> "RenderableType":
    """Concatenate a name and its short version.

    Examples
    --------
        name = "--help"
        short = "-h"
        return: "--help -h"
    """
    name = "" if entry.name is None else entry.name
    short = "" if entry.short is None else entry.short
    return name + " " + short
