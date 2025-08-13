"""Default converters.

"""

def asterisk_converter(_: "RenderableType", inp: "AbstractTableEntry") -> "RenderableType":
    if inp.required:
        return "*"
    return ""


def stretch_name_converter(_: "RenderableType", inp: "AbstractTableEntry") -> "RenderableType":
    """Split name into two parts based on --.

    Example
    -------
        '--foo--no-foo'  to '--foo --no-foo'.
    """
    out = " --".join(inp.name.split("--"))
    return out[1:] if out[0] == " " else out


def combine_long_short_converter(_: "RenderableType", inp: "AbstractTableEntry") -> "RenderableType":
    """Concatenate a name and its short version.

    Examples
    --------
        name = "--help"
        short = "-h"
        return: "--help -h"
    """
    return inp.name + " " + inp.short



