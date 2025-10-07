"""Shared utilities for help formatters and documentation generators."""


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
    list[str]
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
