"""Markdown documentation formatter."""

import io
from typing import TYPE_CHECKING, Any, Optional, Union, get_args, get_origin

from cyclopts._markup import extract_text

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions

    from cyclopts.help import HelpEntry, HelpPanel


def _format_type_name(type_obj: Any) -> str:
    """Format a type object into a readable string.

    Parameters
    ----------
    type_obj : Any
        Type object to format.

    Returns
    -------
    str
        Formatted type name.

    Examples
    --------
    >>> _format_type_name(str)
    'str'
    >>> _format_type_name(Optional[int])
    'int'
    >>> _format_type_name(list[str])
    'list[str]'
    """
    if type_obj is None:
        return ""

    # Handle string representation of types
    if isinstance(type_obj, str):
        # Clean up common patterns
        type_str = type_obj
        type_str = type_str.replace("<class '", "").replace("'>", "")
        type_str = type_str.replace("typing.", "")

        # Handle Optional types
        if "Optional[" in type_str:
            # Extract the inner type
            inner = type_str[type_str.index("[") + 1 : type_str.rindex("]")]
            return inner

        return type_str

    # Get string representation of the type
    type_str = str(type_obj)

    # Clean up class representations
    if type_str.startswith("<class '"):
        type_str = type_str[8:-2]  # Remove "<class '...'>" wrapper

    # Handle typing module types
    origin = get_origin(type_obj)
    if origin is Union:
        args = get_args(type_obj)
        # Check if it's Optional (Union with None)
        if len(args) == 2 and type(None) in args:
            non_none = args[0] if args[1] is type(None) else args[1]
            return _format_type_name(non_none)
        # Format as Union
        formatted_args = [_format_type_name(arg) for arg in args]
        return f"Union[{', '.join(formatted_args)}]"
    elif origin:
        # Handle generic types like List, Dict, etc.
        args = get_args(type_obj)
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            formatted_args = [_format_type_name(arg) for arg in args]
            return f"{origin_name}[{', '.join(formatted_args)}]"
        return origin_name

    # Handle built-in types
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__

    # Clean up typing module prefixes
    type_str = type_str.replace("typing.", "")

    return type_str


class MarkdownFormatter:
    """Markdown documentation formatter.

    Parameters
    ----------
    heading_level : int
        Starting heading level for panels (default: 2).
        E.g., 2 produces "## Commands", 3 produces "### Commands".
    table_style : str
        Style for parameter/command tables: "table" or "list" (default: "table").
    include_hidden : bool
        Include hidden commands/parameters in documentation (default: False).
    """

    def __init__(
        self,
        heading_level: int = 2,
        table_style: str = "table",
        include_hidden: bool = False,
    ):
        self.heading_level = heading_level
        self.table_style = table_style
        self.include_hidden = include_hidden
        self._output = io.StringIO()

    def reset(self) -> None:
        """Reset the internal output buffer."""
        self._output = io.StringIO()

    def get_output(self) -> str:
        """Get the accumulated markdown output.

        Returns
        -------
        str
            The markdown documentation string.
        """
        return self._output.getvalue()

    def __call__(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        panel: "HelpPanel",
    ) -> None:
        """Format and render a help panel as markdown.

        Parameters
        ----------
        console : Optional[Console]
            Console for rendering (used for extracting plain text).
        options : Optional[ConsoleOptions]
            Console rendering options (unused for markdown).
        panel : HelpPanel
            Help panel to render.
        """
        if not panel.entries:
            return

        # Write panel title as heading
        if panel.title:
            title_text = extract_text(panel.title, console)
            heading = "#" * self.heading_level
            self._output.write(f"{heading} {title_text}\n\n")

        # Write panel description if present
        if panel.description:
            desc_text = extract_text(panel.description, console)
            if desc_text:
                self._output.write(f"{desc_text}\n\n")

        # Format entries based on panel type
        if panel.format == "command":
            self._format_command_panel(panel.entries, console)
        elif panel.format == "parameter":
            self._format_parameter_panel(panel.entries, console)

        self._output.write("\n")

    def _format_command_panel(self, entries: list["HelpEntry"], console: Optional["Console"]) -> None:
        """Format command entries as markdown.

        Parameters
        ----------
        entries : list[HelpEntry]
            Command entries to format.
        console : Optional[Console]
            Console for text extraction.
        """
        # Always use list style for Typer-like output
        for entry in entries:
            # Get command name(s)
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            if names:
                # Use first name as primary
                primary_name = names[0]
                desc = extract_text(entry.description, console)

                if desc:
                    self._output.write(f"* `{primary_name}`: {desc}")
                else:
                    self._output.write(f"* `{primary_name}`:")

                self._output.write("\n")

    def _format_parameter_panel(self, entries: list["HelpEntry"], console: Optional["Console"]) -> None:
        """Format parameter entries as markdown in Typer style.

        Parameters
        ----------
        entries : list[HelpEntry]
            Parameter entries to format.
        console : Optional[Console]
            Console for text extraction.
        """
        # Always use list style for Typer-like output
        for entry in entries:
            # Build parameter names
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            if names:
                # In cyclopts, parameters have both positional and option names
                # Determine if we should display as positional based on requirement and default
                is_positional = entry.required and entry.default is None

                if is_positional:
                    # For positional arguments, only show the positional name (uppercase)
                    positional_names = [n for n in names if not n.startswith("-")]
                    name_str = positional_names[0].upper() if positional_names else names[0].upper()
                else:
                    # For options, format with both short and long forms
                    if len(names) > 1:
                        # Show short option first if available
                        if any(n.startswith("-") and not n.startswith("--") for n in names):
                            short_opts = [n for n in names if n.startswith("-") and not n.startswith("--")]
                            long_opts = [n for n in names if n.startswith("--")]
                            name_str = ", ".join(short_opts + long_opts)
                        else:
                            name_str = ", ".join(names)
                    else:
                        name_str = names[0]

                # Start the entry (no type display)
                self._output.write(f"* `{name_str}`: ")

                # Add description
                desc = extract_text(entry.description, console)
                if desc:
                    self._output.write(desc)

                # Add metadata in brackets
                # Handle required separately for bold formatting
                is_required = False
                if entry.required and not is_positional:
                    # Only show required for options, arguments show it differently
                    is_required = True
                elif is_positional and entry.required:
                    # For positional args, add [required] at the end
                    is_required = True

                metadata = []
                if entry.choices:
                    choices_str = ", ".join(entry.choices)
                    metadata.append(f"choices: {choices_str}")

                if entry.env_var:
                    env_str = ", ".join(entry.env_var)
                    metadata.append(f"env: {env_str}")

                if entry.default is not None:
                    default_str = extract_text(entry.default, console)
                    # For boolean flags, format as flag style
                    if entry.type and _format_type_name(entry.type) == "bool":
                        # Find the positive and negative flag names
                        positive_flag = None
                        negative_flag = None
                        for name in names:
                            if name.startswith("--no-"):
                                negative_flag = name
                            elif name.startswith("--"):
                                if not positive_flag:  # Take first positive flag
                                    positive_flag = name

                        if default_str.lower() == "true" and positive_flag:
                            metadata.append(f"default: {positive_flag}")
                        elif default_str.lower() == "false" and negative_flag:
                            metadata.append(f"default: {negative_flag}")
                        # Don't show default if we can't determine the flag
                    else:
                        metadata.append(f"default: {default_str}")

                # Write required in bold and separate brackets first
                if is_required:
                    self._output.write("  **[required]**")

                # Write each metadata item in its own brackets with italics
                for item in metadata:
                    self._output.write(f"  *[{item}]*")

                self._output.write("\n")

    def render_usage(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        usage: Any,
    ) -> None:
        """Render the usage line as markdown.

        Parameters
        ----------
        console : Optional[Console]
            Console for text extraction.
        options : Optional[ConsoleOptions]
            Console rendering options (unused).
        usage : Any
            The usage line content.
        """
        if usage:
            usage_text = extract_text(usage, console)
            if usage_text:
                self._output.write(f"```\n{usage_text}\n```\n\n")

    def render_description(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        description: Any,
    ) -> None:
        """Render the description as markdown.

        Parameters
        ----------
        console : Optional[Console]
            Console for text extraction.
        options : Optional[ConsoleOptions]
            Console rendering options (unused).
        description : Any
            The description content.
        """
        if description:
            desc_text = extract_text(description, console)
            if desc_text:
                self._output.write(f"{desc_text}\n\n")
