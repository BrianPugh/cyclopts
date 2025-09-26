"""HTML documentation generation for cyclopts apps."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cyclopts.core import App


# CSS styles embedded as a string - clean, modern design
DEFAULT_CSS = """
:root {
    --bg-color: #ffffff;
    --text-color: #333333;
    --border-color: #e0e0e0;
    --code-bg: #f5f5f5;
    --link-color: #0066cc;
    --header-bg: #f8f9fa;
    --required-color: #d73027;
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-color);
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
}

h1 { font-size: 2em; border-bottom: 2px solid var(--border-color); padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }

code {
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', Consolas, monospace;
    font-size: 0.9em;
}

pre {
    background: var(--code-bg);
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: 'Courier New', Consolas, monospace;
    font-size: 0.9em;
}

pre code {
    background: none;
    padding: 0;
}

.usage-block {
    margin: 16px 0;
}

.usage {
    background: #f8f9fa;
    border-left: 4px solid #0066cc;
}

.description {
    margin: 16px 0;
}

.panel-description {
    margin: 12px 0;
    color: #666;
}

.help-panel {
    margin: 24px 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
}

th, td {
    text-align: left;
    padding: 12px;
    border: 1px solid var(--border-color);
}

th {
    background: var(--header-bg);
    font-weight: 600;
}

tr:hover {
    background: #f8f9fa;
}

.required-col {
    width: 80px;
    text-align: center;
}

.required-cell {
    text-align: center;
    color: var(--required-color);
    font-weight: bold;
}

.commands-table code,
.parameters-table code {
    background: #fff;
    padding: 2px 4px;
    font-weight: 600;
}

/* Responsive design */
@media (max-width: 768px) {
    body {
        padding: 10px;
    }

    table {
        font-size: 0.9em;
    }

    th, td {
        padding: 8px;
    }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-color: #1e1e1e;
        --text-color: #e0e0e0;
        --border-color: #444;
        --code-bg: #2d2d2d;
        --link-color: #66b3ff;
        --header-bg: #2d2d2d;
    }

    .commands-table code,
    .parameters-table code {
        background: #2d2d2d;
    }

    .usage {
        background: #2d2d2d;
        border-left-color: #66b3ff;
    }

    tr:hover {
        background: #2d2d2d;
    }
}

/* Command sections */
.command-section {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 2px solid var(--border-color);
}

.command-section:first-child {
    border-top: none;
}
"""


def generate_html_docs(
    app: "App",
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
    standalone: bool = True,
    custom_css: Optional[str] = None,
) -> str:
    """Generate HTML documentation for a CLI application.

    Parameters
    ----------
    app : App
        The cyclopts App instance to document.
    recursive : bool
        If True, generate documentation for all subcommands recursively.
        Default is True.
    include_hidden : bool
        If True, include hidden commands/parameters in documentation.
        Default is False.
    heading_level : int
        Starting heading level for the main application title.
        Default is 1.
    standalone : bool
        If True, generate a complete HTML document with <html>, <head>, etc.
        If False, generate only the body content. Default is True.
    custom_css : str
        Custom CSS to use instead of the default styles.

    Returns
    -------
    str
        The generated HTML documentation.
    """
    from cyclopts.help import format_doc, format_usage
    from cyclopts.help.formatters.html import HtmlFormatter, _escape_html, _extract_plain_text

    # Build the main documentation
    lines = []

    # Start main content div
    lines.append('<div class="cli-documentation">')

    # Add main title and description
    app_name = app.name[0] if app._name else Path(sys.argv[0]).name
    lines.append(f'<h{heading_level} class="app-title">{_escape_html(app_name)}</h{heading_level}>')

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = format_doc(app, help_format)
    if description:
        desc_text = _extract_plain_text(description, None)
        if desc_text:
            lines.append(f'<div class="app-description">{_escape_html(desc_text)}</div>')

    # Add usage section if not suppressed
    if app.usage is None:
        usage = format_usage(app, [])
        if usage:
            lines.append(f"<h{heading_level + 1}>Usage</h{heading_level + 1}>")
            lines.append('<div class="usage-block">')
            usage_text = _extract_plain_text(usage, None)
            lines.append(f'<pre class="usage">{_escape_html(usage_text)}</pre>')
            lines.append("</div>")
    elif app.usage:  # Non-empty custom usage
        lines.append(f"<h{heading_level + 1}>Usage</h{heading_level + 1}>")
        lines.append('<div class="usage-block">')
        lines.append(f'<pre class="usage">{_escape_html(app.usage)}</pre>')
        lines.append("</div>")

    # Get help panels for the current app
    help_panels_with_groups = app._assemble_help_panels([], help_format)

    # Render panels
    formatter = HtmlFormatter(
        heading_level=heading_level + 1,
        include_hidden=include_hidden,
    )
    formatter.reset()
    for group, panel in help_panels_with_groups:
        if not include_hidden and group and not group.show:
            continue
        # Filter out entries based on include_hidden
        if not include_hidden:
            panel.entries = [
                e
                for e in panel.entries
                if not (
                    e.names and all(n.startswith("--help") or n.startswith("--version") or n == "-h" for n in e.names)
                )
            ]
        if panel.entries:  # Only render non-empty panels
            formatter(None, None, panel)

    panel_docs = formatter.get_output().strip()
    if panel_docs:
        lines.append(panel_docs)

    # Handle recursive documentation for subcommands
    if app._commands:
        # Iterate through registered commands
        for name, subapp in app._commands.items():
            # Skip built-in help and version commands
            if name in app._help_flags or name in app._version_flags:
                continue

            if isinstance(subapp, type(app)):  # Check if it's an App instance
                # Check if subapp should be shown
                if not include_hidden and not subapp.show:
                    continue

                # Generate subcommand documentation
                lines.append('<section class="command-section">')
                lines.append(
                    f'<h{heading_level + 1} class="command-title">Command: {_escape_html(name)}</h{heading_level + 1}>'
                )

                # Get subapp help
                with subapp.app_stack([subapp]):
                    sub_help_format = subapp.app_stack.resolve("help_format", fallback=help_format)
                    sub_description = format_doc(subapp, sub_help_format)
                    if sub_description:
                        sub_desc_text = _extract_plain_text(sub_description, None)
                        if sub_desc_text:
                            lines.append(f'<div class="command-description">{_escape_html(sub_desc_text)}</div>')

                    # Generate usage for subcommand
                    if subapp.usage is None:
                        sub_usage = format_usage(subapp, [])
                        if sub_usage:
                            lines.append(f"<h{heading_level + 2}>Usage</h{heading_level + 2}>")
                            lines.append('<div class="usage-block">')
                            sub_usage_text = _extract_plain_text(sub_usage, None)
                            escaped_usage = _escape_html(sub_usage_text.replace(subapp.name[0], f"{app_name} {name}"))
                            lines.append(f'<pre class="usage">{escaped_usage}</pre>')
                            lines.append("</div>")
                    elif subapp.usage:
                        lines.append(f"<h{heading_level + 2}>Usage</h{heading_level + 2}>")
                        lines.append('<div class="usage-block">')
                        lines.append(f'<pre class="usage">{_escape_html(subapp.usage)}</pre>')
                        lines.append("</div>")

                    # Only show subcommand panels if we're in recursive mode
                    if recursive:
                        # Get help panels for subcommand
                        sub_panels = subapp._assemble_help_panels([], sub_help_format)

                        # Render subcommand panels
                        sub_formatter = HtmlFormatter(
                            heading_level=heading_level + 2,
                            include_hidden=include_hidden,
                        )
                        for sub_group, sub_panel in sub_panels:
                            if not include_hidden and sub_group and not sub_group.show:
                                continue
                            # Filter out built-in commands if not including hidden
                            if not include_hidden:
                                sub_panel.entries = [
                                    e
                                    for e in sub_panel.entries
                                    if not (
                                        e.names
                                        and all(
                                            n.startswith("--help") or n.startswith("--version") or n == "-h"
                                            for n in e.names
                                        )
                                    )
                                ]
                            if sub_panel.entries:
                                sub_formatter(None, None, sub_panel)

                        sub_panel_docs = sub_formatter.get_output().strip()
                        if sub_panel_docs:
                            lines.append(sub_panel_docs)

                    # Recursively handle nested subcommands
                    if recursive and subapp._commands:
                        # Filter out built-in commands
                        nested_commands = {
                            k: v
                            for k, v in subapp._commands.items()
                            if k not in subapp._help_flags and k not in subapp._version_flags
                        }
                        if nested_commands:
                            for nested_name, nested_app in nested_commands.items():
                                if isinstance(nested_app, type(app)):  # Check if it's an App instance
                                    if not include_hidden and not nested_app.show:
                                        continue
                                    # Recursively generate docs for nested commands
                                    nested_docs = generate_html_docs(
                                        nested_app,
                                        recursive=recursive,
                                        include_hidden=include_hidden,
                                        heading_level=heading_level + 2,
                                        standalone=False,  # Not standalone for nested
                                        custom_css=None,
                                    )
                                    # Update the title
                                    nested_docs = nested_docs.replace(
                                        f'<h{heading_level + 2} class="app-title">{_escape_html(nested_app.name[0] if nested_app._name else nested_name)}</h{heading_level + 2}>',
                                        f'<h{heading_level + 2} class="command-title">Command: {_escape_html(nested_name)}</h{heading_level + 2}>',
                                    )
                                    lines.append(nested_docs)

                lines.append("</section>")

    lines.append("</div>")  # Close cli-documentation div

    # Join all lines into body content
    body_content = "\n".join(lines)

    # If standalone, wrap in complete HTML document
    if standalone:
        css = custom_css if custom_css else DEFAULT_CSS
        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape_html(app_name)} - CLI Documentation</title>
    <style>
{css}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""
        return doc
    else:
        return body_content
