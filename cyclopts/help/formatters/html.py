"""HTML documentation formatter."""

import io
from typing import TYPE_CHECKING, Any, Optional

from cyclopts._markup import escape_html, extract_text

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
    """
    if type_obj is None:
        return ""

    # Extract plain text if it's a Rich object
    if hasattr(type_obj, "plain"):
        type_str = type_obj.plain.rstrip()
    elif hasattr(type_obj, "__rich_console__"):
        type_str = extract_text(type_obj, None)
    else:
        type_str = str(type_obj)

    # Clean up the type string
    type_str = type_str.replace("<class '", "").replace("'>", "")

    # Handle Optional types
    if type_str.startswith("typing.Optional["):
        inner_type = type_str[16:-1]  # Remove "typing.Optional[" and "]"
        return f"Optional[{inner_type}]"
    elif type_str.startswith("Optional["):
        return type_str

    # Handle Union types
    if type_str.startswith("typing.Union["):
        inner_types = type_str[13:-1]  # Remove "typing.Union[" and "]"
        return f"Union[{inner_types}]"
    elif type_str.startswith("Union["):
        return type_str

    # Handle List/Dict/etc
    if type_str.startswith("typing."):
        return type_str[7:]  # Remove "typing." prefix

    return type_str


class HtmlFormatter:
    """HTML documentation formatter.

    Parameters
    ----------
    heading_level : int
        Starting heading level for panels (default: 2).
        E.g., 2 produces "<h2>Commands</h2>", 3 produces "<h3>Commands</h3>".
    include_hidden : bool
        Include hidden commands/parameters in documentation (default: False).
    app_name : str
        The root application name for generating anchor IDs.
    command_chain : list[str]
        The current command chain for generating anchor IDs.
    """

    def __init__(
        self,
        heading_level: int = 2,
        include_hidden: bool = False,
        app_name: str | None = None,
        command_chain: list[str] | None = None,
    ):
        self.heading_level = heading_level
        self.include_hidden = include_hidden
        self.app_name = app_name
        self.command_chain = command_chain or []
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
            title_text = escape_html(extract_text(panel.title, console))
            self._output.write(f'<h{self.heading_level} class="panel-title">{title_text}</h{self.heading_level}>\n')

        # Write panel description if present
        if panel.description:
            desc_text = escape_html(extract_text(panel.description, console))
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

        # Use list format instead of table
        self._output.write('<ul class="commands-list">\n')

        for entry in entries:
            # Get command name(s)
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            # Generate anchor link if we have app context
            if self.app_name and names:
                # Build the anchor ID for this command
                primary_name = names[0]
                if self.command_chain:
                    # We're in a subcommand, build full chain
                    full_chain = self.command_chain + [primary_name]
                    anchor_id = f"{self.app_name}-{'-'.join(full_chain[1:])}".lower()
                else:
                    # Top-level command
                    anchor_id = f"{self.app_name}-{primary_name}".lower()

                # Create linked command name
                name_html = f'<a href="#{anchor_id}"><code>{escape_html(primary_name)}</code></a>'
                if len(names) > 1:
                    # Add aliases
                    aliases = ", ".join(f"<code>{escape_html(n)}</code>" for n in names[1:])
                    name_html = f"{name_html}, {aliases}"
            else:
                # Fallback to non-linked format
                name_html = ", ".join(f"<code>{escape_html(n)}</code>" for n in names) if names else ""

            desc_html = escape_html(extract_text(entry.description, console))

            self._output.write(f"<li><strong>{name_html}</strong>")
            if desc_html:
                self._output.write(f": {desc_html}")
            self._output.write("</li>\n")

        self._output.write("</ul>\n")

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

        # Use list format instead of table
        self._output.write('<ul class="parameters-list">\n')

        for entry in entries:
            # Build parameter names - prefer negatives for boolean defaults
            names = []
            if entry.names:
                names.extend(entry.names)
            if entry.shorts:
                names.extend(entry.shorts)

            # Check if this is a boolean flag with a default
            default_str = extract_text(entry.default, console) if entry.default is not None else None
            is_bool_flag = False

            # Look for --no- prefixed names to determine if this is a boolean flag
            if names:
                has_positive = any(not n.startswith("--no-") and n.startswith("--") for n in names)
                has_negative = any(n.startswith("--no-") for n in names)
                is_bool_flag = has_positive and has_negative

                if is_bool_flag and default_str in ["True", "enabled"]:
                    # Prefer showing the negative flag when default is True
                    names = [n for n in names if n.startswith("--no-")] + [
                        n for n in names if not n.startswith("--no-")
                    ]
                elif is_bool_flag and default_str in ["False", "disabled"]:
                    # Prefer showing the positive flag when default is False
                    names = [n for n in names if not n.startswith("--no-")] + [
                        n for n in names if n.startswith("--no-")
                    ]

            # Format name with code tags
            if names:
                # For boolean flags, show both but emphasize the preferred one
                if is_bool_flag and len(names) >= 2:
                    name_html = f"<code>{escape_html(names[0])}</code>, <code>{escape_html(names[1])}</code>"
                else:
                    name_html = ", ".join(f"<code>{escape_html(n)}</code>" for n in names)
            else:
                name_html = ""

            # Start list item (no type display)
            self._output.write(f"<li><strong>{name_html}</strong>")

            # Add description
            desc = extract_text(entry.description, console)
            if desc:
                self._output.write(f": {escape_html(desc)}")

            # Add metadata as styled badges
            metadata_items = []

            # Add required marker
            if entry.required:
                metadata_items.append('<span class="metadata-item metadata-required">Required</span>')

            # Add choices
            if entry.choices:
                choices_str = ", ".join(f"<code>{escape_html(str(c))}</code>" for c in entry.choices)
                metadata_items.append(
                    f'<span class="metadata-item metadata-choices"><span class="metadata-label">choices:</span> {choices_str}</span>'
                )

            # Add default - format boolean defaults specially
            if default_str is not None:
                if is_bool_flag:
                    # For boolean flags, show which flag is the default
                    if default_str in ["True", "enabled"]:
                        # Find the positive flag name
                        positive_flag = next(
                            (n for n in names if not n.startswith("--no-") and n.startswith("--")),
                            names[0] if names else "--flag",
                        )
                        metadata_items.append(
                            f'<span class="metadata-item metadata-default"><span class="metadata-label">default:</span> <code>{escape_html(positive_flag)}</code></span>'
                        )
                    elif default_str in ["False", "disabled"]:
                        # Find the negative flag name
                        negative_flag = next((n for n in names if n.startswith("--no-")), "--no-flag")
                        metadata_items.append(
                            f'<span class="metadata-item metadata-default"><span class="metadata-label">default:</span> <code>{escape_html(negative_flag)}</code></span>'
                        )
                    else:
                        metadata_items.append(
                            f'<span class="metadata-item metadata-default"><span class="metadata-label">default:</span> <code>{escape_html(default_str)}</code></span>'
                        )
                else:
                    metadata_items.append(
                        f'<span class="metadata-item metadata-default"><span class="metadata-label">default:</span> <code>{escape_html(default_str)}</code></span>'
                    )

            # Add environment variable
            if entry.env_var:
                env_html = ", ".join(f"<code>{escape_html(e)}</code>" for e in entry.env_var)
                metadata_items.append(
                    f'<span class="metadata-item metadata-env"><span class="metadata-label">env:</span> {env_html}</span>'
                )

            # Write metadata
            if metadata_items:
                self._output.write(f'<span class="parameter-metadata">{"".join(metadata_items)}</span>')

            self._output.write("</li>\n")

        self._output.write("</ul>\n")

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
            usage_text = escape_html(extract_text(usage, console))
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
            desc_text = escape_html(extract_text(description, console))
            if desc_text:
                self._output.write(f'<div class="description">{desc_text}</div>\n')
