"""HTML documentation generation for cyclopts apps."""

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from cyclopts.core import App


def _generate_html_toc(
    lines: List[str],
    app: "App",
    include_hidden: bool,
    app_name: str,
    prefix: str,
    depth: int = 0,
) -> None:
    """Recursively generate HTML table of contents."""
    if not app._commands:
        return

    for name, subapp in app._commands.items():
        # Skip built-in commands
        if name in app._help_flags or name in app._version_flags:
            continue

        if isinstance(subapp, type(app)):  # Check if it's an App instance
            if not include_hidden and not subapp.show:
                continue

            # Create display name and anchor
            display_name = f"{prefix}{name}" if prefix else name
            full_path = f"{app_name}-{display_name.replace(' ', '-')}".lower()

            # Add TOC entry
            indent = "  " * (depth + 1)
            lines.append(f'{indent}<li><a href="#{full_path}"><code>{name}</code></a>')

            # Recursively add nested commands
            if subapp._commands:
                lines.append(f"{indent}  <ul>")
                _generate_html_toc(lines, subapp, include_hidden, app_name, f"{display_name} ", depth + 1)
                lines.append(f"{indent}  </ul>")

            lines.append(f"{indent}</li>")


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

.description, .app-description, .command-description {
    margin: 16px 0;
    color: var(--text-color);
}

.panel-description {
    margin: 12px 0;
    color: #666;
}

.help-panel {
    margin: 24px 0;
}

/* List styles for commands and parameters */
.commands-list, .parameters-list {
    list-style: none;
    padding-left: 0;
    margin: 16px 0;
}

.commands-list li, .parameters-list li {
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
}

.commands-list li:last-child, .parameters-list li:last-child {
    border-bottom: none;
}

.commands-list code, .parameters-list code {
    font-weight: 600;
}

/* Metadata styling */
.parameter-metadata {
    display: inline-flex;
    gap: 8px;
    margin-left: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.metadata-item {
    display: inline-block;
    padding: 2px 8px;
    font-size: 0.85em;
    border-radius: 4px;
    background: var(--code-bg);
    border: 1px solid var(--border-color);
}

.metadata-required {
    background: #fee;
    border-color: #fcc;
    color: #c00;
    font-weight: 600;
}

.metadata-default {
    background: #f0f8ff;
    border-color: #d0e8ff;
    color: #0066cc;
}

.metadata-env {
    background: #f0fff0;
    border-color: #d0ffd0;
    color: #080;
}

.metadata-choices {
    background: #fffaf0;
    border-color: #ffd0a0;
    color: #840;
}

.metadata-label {
    font-weight: 600;
    opacity: 0.8;
    text-transform: uppercase;
    font-size: 0.9em;
}

/* Table of Contents */
.table-of-contents {
    background: var(--header-bg);
    border-radius: 6px;
    padding: 16px;
    margin: 24px 0;
}

.table-of-contents h2 {
    margin-top: 0;
    border-bottom: none;
    padding-bottom: 0;
}

.table-of-contents ul {
    margin: 8px 0;
    padding-left: 24px;
}

.table-of-contents li {
    margin: 4px 0;
}

.table-of-contents a {
    color: var(--link-color);
    text-decoration: none;
}

.table-of-contents a:hover {
    text-decoration: underline;
}

/* General link styles */
a {
    color: var(--link-color);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.commands-list a code {
    color: var(--link-color);
}

/* Back to top link */
.back-to-top {
    display: inline-block;
    margin-top: 8px;
    font-size: 0.9em;
    opacity: 0.7;
}

.back-to-top:hover {
    opacity: 1;
}

/* Responsive design */
@media (max-width: 768px) {
    body {
        padding: 10px;
    }

    .commands-list, .parameters-list {
        font-size: 0.9em;
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

    .usage {
        background: #2d2d2d;
        border-left-color: #66b3ff;
    }

    .table-of-contents {
        background: #2d2d2d;
    }

    .metadata-required {
        background: #4a2020;
        border-color: #6a3030;
        color: #ff9999;
    }

    .metadata-default {
        background: #20304a;
        border-color: #304060;
        color: #99ccff;
    }

    .metadata-env {
        background: #204a20;
        border-color: #306030;
        color: #99ff99;
    }

    .metadata-choices {
        background: #4a3020;
        border-color: #604030;
        color: #ffcc99;
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
    command_chain: Optional[list[str]] = None,
    generate_toc: bool = True,
    no_root_title: bool = False,
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
    command_chain : list[str]
        Internal parameter to track command hierarchy.
        Default is None.
    generate_toc : bool
        If True, generate a table of contents for multi-command apps.
        Default is True.
    no_root_title : bool
        If True, skip generating the root application title.
        Useful when embedding in existing documentation with its own title.
        Default is False.

    Returns
    -------
    str
        The generated HTML documentation.
    """
    from cyclopts.help import format_doc, format_usage
    from cyclopts.help.formatters.html import HtmlFormatter, _escape_html, _extract_plain_text

    # Initialize command chain if not provided
    if command_chain is None:
        command_chain = []

    # Build the main documentation
    lines = []

    # Only add the outer div for standalone documents or root level
    if standalone or not command_chain:
        lines.append('<div class="cli-documentation">')

    # Determine the app name and full command path
    if not command_chain:
        # Root level - use app name or derive from sys.argv
        app_name = app.name[0]
        full_command = app_name
        title = app_name
        # Add title unless no_root_title is True for root level
        if not (no_root_title and not command_chain):
            lines.append(f'<h{heading_level} class="app-title">{title}</h{heading_level}>')
    else:
        # Nested command - build full path
        app_name = command_chain[0] if command_chain else app.name[0]
        full_command = " ".join(command_chain)
        # Create anchor-friendly ID
        anchor_id = f"{app_name}-{'-'.join(command_chain[1:])}"
        anchor_id = anchor_id.lower().replace(" ", "-")
        lines.append('<section class="command-section">')
        lines.append(
            f'<h{heading_level} id="{anchor_id}" class="command-title"><code>{_escape_html(full_command)}</code></h{heading_level}>'
        )

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = format_doc(app, help_format)
    if description:
        desc_text = _extract_plain_text(description, None)
        if desc_text:
            lines.append(f'<div class="app-description">{_escape_html(desc_text)}</div>')

    # Generate table of contents if this is the root level and has commands
    if generate_toc and not command_chain and app._commands:
        lines.append('<div class="table-of-contents">')
        lines.append("<h2>Table of Contents</h2>")
        lines.append("<ul>")
        _generate_html_toc(lines, app, include_hidden, app_name, "", 0)
        lines.append("</ul>")
        lines.append("</div>")

    # Add usage section if not suppressed
    if app.usage is None:
        usage = format_usage(app, [])
        if usage:
            lines.append(f"<h{heading_level + 1}>Usage</h{heading_level + 1}>")
            lines.append('<div class="usage-block">')
            usage_text = _extract_plain_text(usage, None)
            # Format usage with correct command path
            if "Usage:" in usage_text:
                usage_text = usage_text.replace("Usage: ", "")
            # Build proper command path
            parts = usage_text.split(" ", 1)
            if len(parts) > 1 and not command_chain:
                usage_text = f"$ {app_name} {parts[1]}"
            elif command_chain:
                usage_text = f"$ {full_command} {parts[1] if len(parts) > 1 else ''}".strip()
            else:
                usage_text = f"$ {usage_text}" if not usage_text.startswith("$") else usage_text
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
        app_name=app_name,
        command_chain=command_chain,
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

                # Build the command chain for this subcommand
                sub_command_chain = command_chain + [name] if command_chain else [app_name, name]

                # Generate subcommand documentation
                lines.append('<section class="command-section">')
                # Create anchor-friendly ID
                anchor_id = (
                    f"{app_name}-{'-'.join(sub_command_chain[1:])}".lower()
                    if len(sub_command_chain) > 1
                    else f"{app_name}-{name}".lower()
                )
                lines.append(
                    f'<h{heading_level + 1} id="{anchor_id}" class="command-title"><code>{_escape_html(" ".join(sub_command_chain))}</code></h{heading_level + 1}>'
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
                            # Format usage with full command path
                            if "Usage:" in sub_usage_text:
                                sub_usage_text = sub_usage_text.replace("Usage: ", "")
                            # Build the full command path for usage
                            usage_parts = sub_usage_text.split(" ", 1)
                            full_cmd = " ".join(sub_command_chain)
                            if len(usage_parts) > 1:
                                sub_usage_text = f"$ {full_cmd} {usage_parts[1]}"
                            else:
                                sub_usage_text = f"$ {full_cmd}"
                            lines.append(f'<pre class="usage">{_escape_html(sub_usage_text)}</pre>')
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
                            app_name=app_name,
                            command_chain=sub_command_chain,
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
                                    # Build nested command chain
                                    nested_chain = sub_command_chain + [nested_name]
                                    # Recursively generate docs for nested commands
                                    nested_docs = generate_html_docs(
                                        nested_app,
                                        recursive=recursive,
                                        include_hidden=include_hidden,
                                        heading_level=heading_level + 2,
                                        standalone=False,  # Not standalone for nested
                                        custom_css=None,
                                        command_chain=nested_chain,  # Pass the command chain
                                        generate_toc=False,  # No TOC for nested commands
                                    )
                                    lines.append(nested_docs)

                # Add back to top link if we're in a nested section
                if command_chain:
                    lines.append('<a href="#top" class="back-to-top">↑ Back to top</a>')
                lines.append("</section>")

    # Close section if nested command
    if command_chain:
        lines.append("</section>")

    # Only close cli-documentation div for standalone or root
    if standalone or not command_chain:
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
<body id="top">
{body_content}
</body>
</html>"""
        return doc
    else:
        return body_content
