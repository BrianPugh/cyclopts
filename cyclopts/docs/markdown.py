"""Documentation generation functions for cyclopts apps."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyclopts.core import App


def generate_markdown_docs(
    app: "App",
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
) -> str:
    """Generate markdown documentation for a CLI application.

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
        Default is 1 (single #).

    Returns
    -------
    str
        The generated markdown documentation.
    """
    from cyclopts.help import format_doc, format_usage
    from cyclopts.help.formatters.markdown import MarkdownFormatter, _extract_plain_text

    # Build the main documentation
    lines = []

    # Add main title and description
    app_name = app.name[0] if app._name else Path(sys.argv[0]).name
    lines.append(f"{'#' * heading_level} {app_name}")
    lines.append("")

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = format_doc(app, help_format)
    if description:
        # Extract plain text from description
        desc_text = _extract_plain_text(description, None)
        if desc_text:
            lines.append(desc_text.strip())
            lines.append("")

    # Add usage section if not suppressed
    if app.usage is None:
        usage = format_usage(app, [])
        if usage:
            lines.append(f"{'#' * (heading_level + 1)} Usage")
            lines.append("")
            lines.append("```")
            usage_text = _extract_plain_text(usage, None)
            lines.append(usage_text.strip())
            lines.append("```")
            lines.append("")
    elif app.usage:  # Non-empty custom usage
        lines.append(f"{'#' * (heading_level + 1)} Usage")
        lines.append("")
        lines.append("```")
        lines.append(app.usage.strip())
        lines.append("```")
        lines.append("")

    # Get help panels for the current app
    help_panels_with_groups = app._assemble_help_panels([], help_format)

    # Render panels
    formatter = MarkdownFormatter(
        heading_level=heading_level + 1,  # Panels will be one level below main title
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
        lines.append("")

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
                lines.append(f"{'#' * (heading_level + 1)} Command: {name}")
                lines.append("")

                # Get subapp help
                with subapp.app_stack([subapp]):
                    sub_help_format = subapp.app_stack.resolve("help_format", fallback=help_format)
                    sub_description = format_doc(subapp, sub_help_format)
                    if sub_description:
                        sub_desc_text = _extract_plain_text(sub_description, None)
                        if sub_desc_text:
                            lines.append(sub_desc_text.strip())
                            lines.append("")

                    # Generate usage for subcommand
                    if subapp.usage is None:
                        sub_usage = format_usage(subapp, [])
                        if sub_usage:
                            lines.append(f"{'#' * (heading_level + 2)} Usage")
                            lines.append("")
                            lines.append("```")
                            sub_usage_text = _extract_plain_text(sub_usage, None)
                            lines.append(sub_usage_text.strip().replace(subapp.name[0], f"{app_name} {name}"))
                            lines.append("```")
                            lines.append("")
                    elif subapp.usage:
                        lines.append(f"{'#' * (heading_level + 2)} Usage")
                        lines.append("")
                        lines.append("```")
                        lines.append(subapp.usage.strip())
                        lines.append("```")
                        lines.append("")

                    # Only show subcommand panels if we're in recursive mode
                    # (Otherwise we just show the basic info about this command)
                    if recursive:
                        # Get help panels for subcommand
                        sub_panels = subapp._assemble_help_panels([], sub_help_format)

                        # Render subcommand panels
                        sub_formatter = MarkdownFormatter(
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
                            lines.append("")

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
                                    nested_docs = generate_markdown_docs(
                                        nested_app,
                                        recursive=recursive,
                                        include_hidden=include_hidden,
                                        heading_level=heading_level + 2,
                                    )
                                    # Update the title to include parent command
                                    nested_lines = nested_docs.split("\n")
                                    if nested_lines and nested_lines[0].startswith("#"):
                                        nested_lines[0] = f"{'#' * (heading_level + 2)} Command: {nested_name}"
                                    lines.extend(nested_lines)
                                    lines.append("")

    # Join all lines into final document
    doc = "\n".join(lines).rstrip() + "\n"
    return doc
