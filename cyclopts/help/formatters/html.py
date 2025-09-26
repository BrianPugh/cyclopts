"""HTML documentation formatter."""

import html
import io
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions

    from cyclopts.help import HelpEntry, HelpPanel


def _escape_html(text: Optional[str]) -> str:
    """Escape special HTML characters in text.

    Parameters
    ----------
    text : Optional[str]
        Text to escape. Can be None.

    Returns
    -------
    str
        Escaped text safe for HTML.
    """
    if not text:
        return ""
    return html.escape(text)


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
        import io

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


class HtmlFormatter:
    """HTML documentation formatter.

    Parameters
    ----------
    heading_level : int
        Starting heading level for panels (default: 2).
        E.g., 2 produces "<h2>Commands</h2>", 3 produces "<h3>Commands</h3>".
    include_hidden : bool
        Include hidden commands/parameters in documentation (default: False).
    """

    def __init__(
        self,
        heading_level: int = 2,
        include_hidden: bool = False,
    ):
        self.heading_level = heading_level
        self.include_hidden = include_hidden
        self._output = io.StringIO()

    def reset(self) -> None:
        """Reset the internal output buffer."""
        self._output = io.StringIO()

    def get_output(self) -> str:
        """Get the accumulated HTML output.

        Returns
        -------
        str
            The HTML documentation string.
        """
        return self._output.getvalue()

    def __call__(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        panel: "HelpPanel",
    ) -> None:
        """Format and render a help panel as HTML.

        Parameters
        ----------
        console : Optional[Console]
            Console for rendering (used for extracting plain text).
        options : Optional[ConsoleOptions]
            Console rendering options (unused for HTML).
        panel : HelpPanel
            Help panel to render.
        """
        if not panel.entries:
            return

        # Write panel as a section
        self._output.write('<section class="help-panel">\n')

        # Write panel title as heading
        if panel.title:
            title_text = _escape_html(_extract_plain_text(panel.title, console))
            self._output.write(f'<h{self.heading_level} class="panel-title">{title_text}</h{self.heading_level}>\n')

        # Write panel description if present
        if panel.description:
            desc_text = _escape_html(_extract_plain_text(panel.description, console))
            if desc_text:
                self._output.write(f'<div class="panel-description">{desc_text}</div>\n')

        # Format entries based on panel type
        if panel.format == "command":
            self._format_command_panel(panel.entries, console)
        elif panel.format == "parameter":
            self._format_parameter_panel(panel.entries, console)

        self._output.write("</section>\n")

    def _format_command_panel(self, entries: list["HelpEntry"], console: Optional["Console"]) -> None:
        """Format command entries as HTML.

        Parameters
        ----------
        entries : list[HelpEntry]
            Command entries to format.
        console : Optional[Console]
            Console for text extraction.
        """
        if not entries:
            return

        self._output.write('<table class="commands-table">\n')
        self._output.write("<thead>\n")
        self._output.write("<tr><th>Command</th><th>Description</th></tr>\n")
        self._output.write("</thead>\n")
        self._output.write("<tbody>\n")

        for entry in entries:
            # Get command name(s)
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            name_html = ", ".join(f"<code>{_escape_html(n)}</code>" for n in names) if names else ""
            desc_html = _escape_html(_extract_plain_text(entry.description, console))

            self._output.write(f"<tr><td>{name_html}</td><td>{desc_html}</td></tr>\n")

        self._output.write("</tbody>\n")
        self._output.write("</table>\n")

    def _format_parameter_panel(self, entries: list["HelpEntry"], console: Optional["Console"]) -> None:
        """Format parameter entries as HTML.

        Parameters
        ----------
        entries : list[HelpEntry]
            Parameter entries to format.
        console : Optional[Console]
            Console for text extraction.
        """
        if not entries:
            return

        # Determine which columns we need
        has_required = any(e.required for e in entries)

        self._output.write('<table class="parameters-table">\n')
        self._output.write("<thead>\n")
        self._output.write("<tr>")
        if has_required:
            self._output.write('<th class="required-col">Required</th>')
        self._output.write("<th>Parameter</th><th>Description</th></tr>\n")
        self._output.write("</thead>\n")
        self._output.write("<tbody>\n")

        for entry in entries:
            # Build parameter names
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            name_html = ", ".join(f"<code>{_escape_html(n)}</code>" for n in names) if names else ""

            # Build description with metadata
            desc_parts = []
            desc = _extract_plain_text(entry.description, console)
            if desc:
                desc_parts.append(_escape_html(desc))

            # Add metadata as a list
            metadata = []
            if entry.type:
                type_str = _extract_plain_text(entry.type, console)
                if type_str:
                    metadata.append(f"Type: <code>{_escape_html(type_str)}</code>")

            if entry.choices:
                choices_html = ", ".join(f"<code>{_escape_html(str(c))}</code>" for c in entry.choices)
                metadata.append(f"Choices: {choices_html}")

            if entry.env_var:
                env_html = ", ".join(f"<code>{_escape_html(e)}</code>" for e in entry.env_var)
                metadata.append(f"Environment: {env_html}")

            if entry.default is not None:
                default_str = _extract_plain_text(entry.default, console)
                metadata.append(f"Default: <code>{_escape_html(default_str)}</code>")

            # Combine description and metadata
            full_desc = desc_parts[0] if desc_parts else ""
            if metadata:
                metadata_html = "<br>".join(metadata)
                if full_desc:
                    full_desc += "<br><br>" + metadata_html
                else:
                    full_desc = metadata_html

            # Write table row
            self._output.write("<tr>")
            if has_required:
                required_marker = "✓" if entry.required else ""
                self._output.write(f'<td class="required-cell">{required_marker}</td>')
            self._output.write(f"<td>{name_html}</td><td>{full_desc}</td></tr>\n")

        self._output.write("</tbody>\n")
        self._output.write("</table>\n")

    def render_usage(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        usage: Any,
    ) -> None:
        """Render the usage line as HTML.

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
            usage_text = _escape_html(_extract_plain_text(usage, console))
            if usage_text:
                self._output.write('<div class="usage-block">\n')
                self._output.write(f'<pre class="usage">{usage_text}</pre>\n')
                self._output.write("</div>\n")

    def render_description(
        self,
        console: Optional["Console"],
        options: Optional["ConsoleOptions"],
        description: Any,
    ) -> None:
        """Render the description as HTML.

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
            desc_text = _escape_html(_extract_plain_text(description, console))
            if desc_text:
                self._output.write(f'<div class="description">{desc_text}</div>\n')
