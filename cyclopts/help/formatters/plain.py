"""Plain text help formatter for improved accessibility."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

    from cyclopts.help import HelpPanel


def _to_plain_text(obj: Any, console: "Console") -> str:
    """Extract plain text from Rich renderables.

    Parameters
    ----------
    obj : Any
        Object to convert to plain text.
    console : Console
        Console for rendering Rich objects.

    Returns
    -------
    str
        Plain text representation.
    """
    if obj is None:
        return ""
    if hasattr(obj, "plain"):
        return obj.plain.rstrip()
    if hasattr(obj, "primary_renderable"):
        # InlineText object - render it to plain text
        with console.capture() as capture:
            console.print(obj, end="")
        return capture.get().rstrip()
    if hasattr(obj, "__rich_console__"):
        # Other Rich renderables
        with console.capture() as capture:
            console.print(obj, end="")
        return capture.get().rstrip()
    return str(obj).rstrip()


def _split_parameter_names(name: str) -> list[str]:
    """Split concatenated parameter names.

    Handles cases like "VERBOSE--verbose--no-verbose" by intelligently
    splitting them into separate option names.

    Parameters
    ----------
    name : str
        Concatenated parameter names.

    Returns
    -------
    list[str]
        List of individual option names.
    """
    import re

    # Split on "--" but keep the "--" with each option
    parts = re.split(r"(--)", name)
    names = []
    current = ""
    for part in parts:
        if part == "--":
            if current and not current.startswith("--"):
                # Save the previous part (like "VERBOSE")
                names.append(current)
                current = "--"
            else:
                current += part
        elif part:
            current += part
            if current.startswith("--"):
                names.append(current)
                current = ""
    if current:
        names.append(current)
    return names


def _format_parameter_entry(
    name: str,
    short: str,
    desc: str,
    console: "Console",
) -> None:
    """Format and print a parameter entry.

    Parameters
    ----------
    name : str
        Parameter name(s).
    short : str
        Short form of the parameter.
    desc : str
        Parameter description.
    console : Console
        Console to print to.
    """
    names = _split_parameter_names(name)

    # Print each option name
    for i, option_name in enumerate(names):
        if i == 0 and desc:
            # First option gets the description
            if short:
                console.print(f"  {option_name}, {short}: {desc}")
            else:
                console.print(f"  {option_name}: {desc}")
        else:
            console.print(f"  {option_name}")


def _format_command_entry(
    name: str,
    short: str,
    desc: str,
    console: "Console",
) -> None:
    """Format and print a command entry.

    Parameters
    ----------
    name : str
        Command name(s).
    short : str
        Short form of the command.
    desc : str
        Command description.
    console : Console
        Console to print to.
    """
    # Check if name has newlines (for commands with multiple names)
    name_lines = name.split("\n") if name else []

    if len(name_lines) > 1:
        # Multiple option names on separate lines
        for i, line in enumerate(name_lines):
            line = line.strip()
            if line:
                if i == 0:
                    # First line gets short form and description
                    parts = [line]
                    if short:
                        parts.append(", " + short)
                    entry_name = " ".join(parts)
                    if desc:
                        console.print(f"  {entry_name}: {desc}")
                    else:
                        console.print(f"  {entry_name}")
                else:
                    # Additional lines
                    console.print(f"  {line}")
    elif name:
        # Single name
        parts = []
        if name:
            parts.append(name)
        if short:
            parts.append(", " + short)

        entry_name = " ".join(parts)

        if desc:
            console.print(f"  {entry_name}: {desc}")
        else:
            console.print(f"  {entry_name}")
    elif short:
        # Only short name
        if desc:
            console.print(f"  {short}: {desc}")
        else:
            console.print(f"  {short}")


def format_plain(
    help_panels: list["HelpPanel"],
    usage: Any,
    description: Any,
    console: "Console",
) -> None:
    """Format help as plain text without Rich formatting.

    Parameters
    ----------
    help_panels : list[HelpPanel]
        List of help panels to render.
    usage : Any
        The usage line (Text or str).
    description : Any
        The description (can be various Rich renderables).
    console : Console
        Console to render to.
    """
    # Print usage line
    if usage:
        usage_text = _to_plain_text(usage, console)
        if usage_text:
            console.print(usage_text)

    # Print description with blank line after usage
    if description:
        desc_text = _to_plain_text(description, console)
        if desc_text:
            if usage:  # Only add blank line if there was usage text
                console.print("")
            console.print(desc_text)

    # Print help panels
    for panel in help_panels:
        if not panel.entries:
            continue

        # Print panel title with appropriate formatting
        if panel.title:
            console.print("")
            console.print(f"{panel.title}:")

        # Print each entry in the panel
        for entry in panel.entries:
            # Extract the components
            name = _to_plain_text(entry.name, console)
            short = _to_plain_text(entry.short, console)
            desc = _to_plain_text(entry.description, console)

            # Format the entry line
            if name or short:
                # Handle parameters section specially - names might be concatenated
                if panel.title == "Parameters" and name:  # TODO: this is wrong; don't rely on title name.
                    _format_parameter_entry(name, short, desc, console)
                else:
                    # For commands or other panels
                    _format_command_entry(name, short, desc, console)
