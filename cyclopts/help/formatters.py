def wrap_formatter(inp: "RenderableType", _: "AbstractTableEntry", col_spec: "ColumnSpec") -> "RenderableType":
    import textwrap
    from functools import partial

    wrap = partial(
        textwrap.wrap,
        subsequent_indent="  ",
        break_on_hyphens=False,
        tabsize=4,
    )

    if col_spec.max_width:
        new = "\n".join(wrap(inp, col_spec.max_width))
    else:
        new = "\n".join(wrap(inp))
    return new
