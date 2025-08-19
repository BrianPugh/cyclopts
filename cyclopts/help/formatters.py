from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import RenderableType

    from cyclopts.help import ColumnSpec, TableEntry


def wrap_formatter(out: "RenderableType", entry: "TableEntry", col_spec: "ColumnSpec") -> "RenderableType":
    import textwrap
    from functools import partial

    wrap = partial(
        textwrap.wrap,
        subsequent_indent="  ",
        break_on_hyphens=False,
        tabsize=4,
    )

    if col_spec.max_width:
        new = "\n".join(wrap(str(out), col_spec.max_width))
    else:
        new = "\n".join(wrap(str(out)))
    return new
