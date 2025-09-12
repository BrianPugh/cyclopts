"""Plain text help formatter for improved accessibility."""

from typing import TYPE_CHECKING, Any, Optional

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


class PlainFormatter:
    """Plain text formatter for improved accessibility.

    Parameters
    ----------
    indent_width : int
        Number of spaces to indent entries (default: 2).
    max_width : Optional[int]
        Maximum line width for wrapping text.
    """

    def __init__(
        self,
        indent_width: int = 2,
        max_width: Optional[int] = None,
    ):
        self.indent_width = indent_width
        self.max_width = max_width
        self.indent = " " * indent_width

    def __call__(
        self,
        panel: "HelpPanel",
        console: "Console",
    ) -> None:
        """Format and render a single help panel as plain text.

        Parameters
        ----------
        panel : HelpPanel
            Help panel to render.
        console : Console
            Console to render to.
        """
        if not panel.entries:
            return

        # Print panel title with appropriate formatting
        if panel.title:
            console.print("")
            console.print(f"{panel.title}:")

        # Print each entry in the panel
        for entry in panel.entries:
            # Extract the components
            # Join names and shorts if they are tuples
            names_text = " ".join(entry.names) if entry.names else ""
            shorts_text = " ".join(entry.shorts) if entry.shorts else ""
            desc = _to_plain_text(entry.description, console)

            # Format the entry line
            if names_text or shorts_text:
                # Handle parameters section specially
                if panel.format == "parameter":
                    self._format_parameter_entry(entry.names, entry.shorts, desc, console)
                else:
                    # For commands or other panels
                    self._format_command_entry(entry.names, entry.shorts, desc, console)

    def render_usage(
        self,
        usage: Any,
        console: "Console",
    ) -> None:
        """Render the usage line.

        Parameters
        ----------
        usage : Any
            The usage line (Text or str).
        console : Console
            Console to render to.
        """
        if usage:
            usage_text = _to_plain_text(usage, console)
            if usage_text:
                console.print(usage_text)

    def render_description(
        self,
        description: Any,
        console: "Console",
    ) -> None:
        """Render the description.

        Parameters
        ----------
        description : Any
            The description (can be various Rich renderables).
        console : Console
            Console to render to.
        """
        if description:
            desc_text = _to_plain_text(description, console)
            if desc_text:
                console.print("")
                console.print(desc_text)

    def _format_parameter_entry(
        self,
        names: tuple[str, ...],
        shorts: tuple[str, ...],
        desc: str,
        console: "Console",
    ) -> None:
        """Format and print a parameter entry.

        Parameters
        ----------
        names : tuple[str, ...]
            Parameter long names.
        shorts : tuple[str, ...]
            Short forms of the parameter.
        desc : str
            Parameter description.
        console : Console
            Console to print to.
        """
        # Combine all names and shorts
        all_options = list(names) + list(shorts)

        if not all_options:
            return

        # First option gets the description
        first_option = all_options[0]
        if len(all_options) > 1:
            # Multiple options - show them all on first line with description
            options_str = ", ".join(all_options)
            if desc:
                console.print(f"{self.indent}{options_str}: {desc}")
            else:
                console.print(f"{self.indent}{options_str}")
        else:
            # Single option
            if desc:
                console.print(f"{self.indent}{first_option}: {desc}")
            else:
                console.print(f"{self.indent}{first_option}")

    def _format_command_entry(
        self,
        names: tuple[str, ...],
        shorts: tuple[str, ...],
        desc: str,
        console: "Console",
    ) -> None:
        """Format and print a command entry.

        Parameters
        ----------
        names : tuple[str, ...]
            Command long names.
        shorts : tuple[str, ...]
            Short forms of the command.
        desc : str
            Command description.
        console : Console
            Console to print to.
        """
        # For commands, we typically want to show long names on separate lines
        # and shorts together
        if names:
            for i, name in enumerate(names):
                if i == 0:
                    # First name gets the shorts and description
                    parts = [name]
                    if shorts:
                        parts.append(", " + " ".join(shorts))
                    entry_name = "".join(parts)
                    if desc:
                        console.print(f"{self.indent}{entry_name}: {desc}")
                    else:
                        console.print(f"{self.indent}{entry_name}")
                else:
                    # Additional names on separate lines
                    console.print(f"{self.indent}{name}")
        elif shorts:
            # Only short names
            shorts_str = " ".join(shorts)
            if desc:
                console.print(f"{self.indent}{shorts_str}: {desc}")
            else:
                console.print(f"{self.indent}{shorts_str}")
