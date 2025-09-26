"""Markdown documentation formatter."""

import io
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions

    from cyclopts.help import HelpEntry, HelpPanel


def _escape_markdown(text: Optional[str]) -> Optional[str]:
    """Escape special markdown characters in text.

    Parameters
    ----------
    text : Optional[str]
        Text to escape. Can be None.

    Returns
    -------
    Optional[str]
        Escaped text safe for markdown, or None if input was None.
    """
    # Escape characters that have special meaning in markdown
    # But preserve intentional markdown formatting
    if not text:
        return text

    # Don't escape if it looks like it already contains markdown formatting
    if any(pattern in text for pattern in ["**", "*", "`", "[", "]", "#"]):
        return text

    # Escape pipe characters for table compatibility
    text = text.replace("|", "\\|")
    return text


def _extract_plain_text(obj: Any, console: Optional["Console"] = None) -> str:
    """Extract plain text from Rich renderables or any object.

    Parameters
    ----------
    obj : Any
        Object to convert to plain text.
    console : Optional[Console]
        Console for rendering Rich objects.

    Returns
    -------
    str
        Plain text representation.
    """
    if obj is None:
        return ""

    # Rich Text objects have a .plain property
    if hasattr(obj, "plain"):
        return obj.plain.rstrip()

    # For Rich renderables, extract without styles
    if hasattr(obj, "__rich_console__"):
        from rich.console import Console

        # Create a plain console for text extraction
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

    # Fallback to string conversion
    return str(obj).rstrip()


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
            title_text = _extract_plain_text(panel.title, console)
            heading = "#" * self.heading_level
            self._output.write(f"{heading} {title_text}\n\n")

        # Write panel description if present
        if panel.description:
            desc_text = _extract_plain_text(panel.description, console)
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
        if self.table_style == "table" and entries:
            # Create markdown table
            self._output.write("| Command | Description |\n")
            self._output.write("| ------- | ----------- |\n")

            for entry in entries:
                # Get command name(s)
                names = []
                if entry.names:
                    names.extend(entry.names)
                if entry.shorts:
                    names.extend(entry.shorts)

                name_str = ", ".join(f"`{n}`" for n in names) if names else ""
                desc_str = _escape_markdown(_extract_plain_text(entry.description, console))

                self._output.write(f"| {name_str} | {desc_str} |\n")
        else:
            # Use definition list style
            for entry in entries:
                names = []
                if entry.names:
                    names.extend(entry.names)
                if entry.shorts:
                    names.extend(entry.shorts)

                if names:
                    name_str = ", ".join(f"`{n}`" for n in names)
                    self._output.write(f"**{name_str}**\n")

                    desc = _extract_plain_text(entry.description, console)
                    if desc:
                        self._output.write(f"{desc}")

                    self._output.write("\n\n")

    def _format_parameter_panel(self, entries: list["HelpEntry"], console: Optional["Console"]) -> None:
        """Format parameter entries as markdown.

        Parameters
        ----------
        entries : list[HelpEntry]
            Parameter entries to format.
        console : Optional[Console]
            Console for text extraction.
        """
        if self.table_style == "table" and entries:
            # Determine which columns we need
            has_required = any(e.required for e in entries)

            # Create markdown table with appropriate columns
            if has_required:
                self._output.write("| Required | Parameter | Description |\n")
                self._output.write("| :------: | --------- | ----------- |\n")
            else:
                self._output.write("| Parameter | Description |\n")
                self._output.write("| --------- | ----------- |\n")

            for entry in entries:
                # Build parameter names
                names = []
                if entry.names:
                    names.extend(entry.names)
                if entry.shorts:
                    names.extend(entry.shorts)

                name_str = ", ".join(f"`{n}`" for n in names) if names else ""

                # Build description with metadata
                desc_parts = []
                desc = _extract_plain_text(entry.description, console)
                if desc:
                    desc_parts.append(_escape_markdown(desc))

                # Add metadata on separate lines for clarity
                metadata = []
                if entry.type:
                    type_str = _extract_plain_text(entry.type, console)
                    if type_str:
                        metadata.append(f"Type: `{type_str}`")

                if entry.choices:
                    choices_str = ", ".join(f"`{c}`" for c in entry.choices)
                    metadata.append(f"Choices: {choices_str}")

                if entry.env_var:
                    env_str = ", ".join(f"`{e}`" for e in entry.env_var)
                    metadata.append(f"Env: {env_str}")

                if entry.default is not None:
                    default_str = _extract_plain_text(entry.default, console)
                    metadata.append(f"Default: `{default_str}`")

                if metadata:
                    desc_parts.append("<br>".join(metadata))

                full_desc = "<br><br>".join(desc_parts)

                # Write table row
                if has_required:
                    required_marker = "✓" if entry.required else ""
                    self._output.write(f"| {required_marker} | {name_str} | {full_desc} |\n")
                else:
                    self._output.write(f"| {name_str} | {full_desc} |\n")
        else:
            # Use definition list style
            for entry in entries:
                names = []
                if entry.names:
                    names.extend(entry.names)
                if entry.shorts:
                    names.extend(entry.shorts)

                if names:
                    name_str = ", ".join(f"`{n}`" for n in names)
                    required_str = " *(required)*" if entry.required else ""
                    self._output.write(f"**{name_str}**{required_str}")

                    # Add description
                    desc = _extract_plain_text(entry.description, console)
                    if desc:
                        self._output.write(f"  \n{desc}")

                    # Add metadata as bullet points
                    metadata = []
                    if entry.type:
                        type_str = _extract_plain_text(entry.type, console)
                        if type_str:
                            metadata.append(f"Type: `{type_str}`")

                    if entry.choices:
                        choices_str = ", ".join(f"`{c}`" for c in entry.choices)
                        metadata.append(f"Choices: {choices_str}")

                    if entry.env_var:
                        env_str = ", ".join(f"`{e}`" for e in entry.env_var)
                        metadata.append(f"Environment: {env_str}")

                    if entry.default is not None:
                        default_str = _extract_plain_text(entry.default, console)
                        metadata.append(f"Default: `{default_str}`")

                    if metadata:
                        self._output.write("  \n")
                        for item in metadata:
                            self._output.write(f"  - {item}  \n")

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
            usage_text = _extract_plain_text(usage, console)
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
            desc_text = _extract_plain_text(description, console)
            if desc_text:
                self._output.write(f"{desc_text}\n\n")
