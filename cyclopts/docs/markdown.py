"""Documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING

from cyclopts._markup import extract_text
from cyclopts.docs.base import BaseDocGenerator

if TYPE_CHECKING:
    from cyclopts.core import App


def _collect_commands_for_toc(
    app: "App", include_hidden: bool = False, prefix: str = ""
) -> list[tuple[str, str, "App"]]:
    """Recursively collect all commands for table of contents.

    Returns a list of (display_name, anchor, app) tuples.
    """
    commands = []

    if not app._commands:
        return commands

    for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
        # Create display name and anchor
        display_name = f"{prefix}{name}" if prefix else name
        # Anchor is the markdown heading converted to lowercase with dashes
        anchor = display_name.replace(" ", "-").lower()

        commands.append((display_name, anchor, subapp))

        # Recursively collect nested commands
        nested = _collect_commands_for_toc(subapp, include_hidden=include_hidden, prefix=f"{display_name} ")
        commands.extend(nested)

    return commands


def _generate_toc_entries(
    lines: list[str], commands: list[tuple[str, str, "App"]], level: int = 0, app_name: str | None = None
) -> None:
    """Generate TOC entries with proper indentation."""
    for display_name, anchor, _app in commands:
        # Calculate depth based on number of spaces in display name
        depth = display_name.count(" ")
        indent = "  " * depth

        # Get just the command name (last part)
        cmd_name = display_name.split()[-1]

        # Create the TOC entry with markdown link
        # The anchor for markdown headings with backticks
        # ## `burgery create` becomes #burgery-create
        if app_name and depth == 0:
            full_name = f"{app_name} {display_name}"
        elif app_name:
            full_name = f"{app_name} {display_name}"
        else:
            full_name = display_name

        # Convert to anchor format (lowercase, replace spaces with dashes)
        anchor = full_name.lower().replace(" ", "-")
        lines.append(f"{indent}- [`{cmd_name}`](#{anchor})")


def generate_markdown_docs(
    app: "App",
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
    command_chain: list[str] | None = None,
    generate_toc: bool = True,
    flatten_commands: bool = False,
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
    command_chain : list[str]
        Internal parameter to track command hierarchy.
        Default is None.
    generate_toc : bool
        If True, generate a table of contents for multi-command apps.
        Default is True.
    flatten_commands : bool
        If True, generate all commands at the same heading level instead of nested.
        Default is False.

    Returns
    -------
    str
        The generated markdown documentation.
    """
    from cyclopts.help.formatters.markdown import MarkdownFormatter

    # Build the main documentation
    lines = []

    # Initialize command chain if not provided
    if command_chain is None:
        command_chain = []

    # Determine the app name and full command path
    app_name, full_command, base_title = BaseDocGenerator.get_app_info(app, command_chain)
    title = f"`{full_command}`" if command_chain else base_title

    # Add title for all levels
    lines.append(f"{'#' * heading_level} {title}")
    lines.append("")

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = BaseDocGenerator.extract_description(app, help_format)
    if description:
        # Extract plain text from description
        # Preserve markup when help_format matches output format (markdown)
        preserve = help_format in ("markdown", "md")
        desc_text = extract_text(description, None, preserve_markup=preserve)
        if desc_text:
            lines.append(desc_text.strip())
            lines.append("")

    # Generate table of contents if this is the root level and has commands
    if generate_toc and not command_chain and app._commands:
        # Collect all commands recursively for TOC
        toc_commands = _collect_commands_for_toc(app, include_hidden=include_hidden)
        if toc_commands:
            lines.append("## Table of Contents")
            lines.append("")
            _generate_toc_entries(lines, toc_commands, level=0, app_name=app_name)
            lines.append("")

    # Add usage section if not suppressed
    usage = BaseDocGenerator.extract_usage(app)
    if usage:
        lines.append("**Usage**:")
        lines.append("")
        lines.append("```console")
        if isinstance(usage, str):
            usage_text = usage
        else:
            usage_text = extract_text(usage, None, preserve_markup=False)
        usage_line = BaseDocGenerator.format_usage_line(usage_text, command_chain, prefix="$")
        lines.append(usage_line)
        lines.append("```")
        lines.append("")

    # Get help panels for the current app
    help_panels_with_groups = app._assemble_help_panels([], help_format)

    # Separate panels into categories for organized output
    categorized = BaseDocGenerator.categorize_panels(help_panels_with_groups, include_hidden)
    command_panels = categorized["commands"]
    argument_panels = categorized["arguments"]
    option_panels = categorized["options"]
    grouped_panels = categorized["grouped"]

    # Render panels in Typer order: Arguments, Options, Commands
    formatter = MarkdownFormatter(
        heading_level=heading_level + 1,
        include_hidden=include_hidden,
        table_style="list",  # Always use list style for Typer-like output
    )

    # Render arguments
    if argument_panels:
        lines.append("**Arguments**:\n")
        for _group, panel in argument_panels:
            formatter.reset()
            # Don't show panel title for arguments
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
        lines.append("")

    # Render options
    if option_panels:
        lines.append("**Options**:\n")
        for _group, panel in option_panels:
            formatter.reset()
            # Don't show panel title for options
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
        lines.append("")

    # Render grouped options (e.g., Condiments, Toppings)
    if grouped_panels:
        for _group, panel in grouped_panels:
            if panel.title:
                lines.append(f"**{panel.title}**:\n")
                formatter.reset()
                panel_copy = panel.__class__(
                    title="",  # Don't show title again in formatter
                    entries=panel.entries,
                    format=panel.format,
                    description=panel.description,
                )
                formatter(None, None, panel_copy)
                output = formatter.get_output().strip()
                if output:
                    lines.append(output)
                lines.append("")

    # Render commands
    if command_panels:
        lines.append("**Commands**:\n")
        for _group, panel in command_panels:
            formatter.reset()
            # Don't show panel title for commands
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
        lines.append("")

    # Handle recursive documentation for subcommands
    if app._commands:
        # Iterate through registered commands using iterate_commands helper
        # This automatically resolves CommandSpec instances
        for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
            # Build the command chain for this subcommand
            sub_command_chain = BaseDocGenerator.build_command_chain(command_chain, name, app_name)

            # Determine heading level for subcommand
            if flatten_commands:
                sub_heading_level = heading_level
            else:
                sub_heading_level = heading_level + 1

            # Generate subcommand documentation in Typer style
            lines.append(f"{'#' * sub_heading_level} `{' '.join(sub_command_chain)}`")
            lines.append("")

            # Get subapp help
            with subapp.app_stack([subapp]):
                sub_help_format = subapp.app_stack.resolve("help_format", fallback=help_format)
                # Preserve markup when sub_help_format matches output format (markdown)
                preserve_sub = sub_help_format in ("markdown", "md")
                sub_description = BaseDocGenerator.extract_description(subapp, sub_help_format)
                if sub_description:
                    sub_desc_text = extract_text(sub_description, None, preserve_markup=preserve_sub)
                    if sub_desc_text:
                        lines.append(sub_desc_text.strip())
                        lines.append("")

                # Generate usage for subcommand
                sub_usage = BaseDocGenerator.extract_usage(subapp)
                if sub_usage:
                    lines.append("**Usage**:")
                    lines.append("")
                    lines.append("```console")
                    if isinstance(sub_usage, str):
                        sub_usage_text = sub_usage
                    else:
                        sub_usage_text = extract_text(sub_usage, None, preserve_markup=False)
                    usage_line = BaseDocGenerator.format_usage_line(sub_usage_text, sub_command_chain, prefix="$")
                    lines.append(usage_line)
                    lines.append("```")
                    lines.append("")

                # Only show subcommand panels if we're in recursive mode
                # (Otherwise we just show the basic info about this command)
                if recursive:
                    # Get help panels for subcommand
                    sub_panels = subapp._assemble_help_panels([], sub_help_format)

                    # Separate panels for organized output
                    sub_categorized = BaseDocGenerator.categorize_panels(sub_panels, include_hidden)
                    sub_argument_panels = sub_categorized["arguments"]
                    sub_option_panels = sub_categorized["options"]
                    sub_grouped_panels = sub_categorized["grouped"]
                    sub_command_panels = sub_categorized["commands"]

                    # Render panels in Typer order
                    if flatten_commands:
                        panel_heading_level = heading_level + 1
                    else:
                        panel_heading_level = heading_level + 2
                    sub_formatter = MarkdownFormatter(
                        heading_level=panel_heading_level, include_hidden=include_hidden, table_style="list"
                    )

                    # Arguments
                    if sub_argument_panels:
                        lines.append("**Arguments**:\n")
                        for _group, panel in sub_argument_panels:
                            sub_formatter.reset()
                            sub_formatter(None, None, panel)
                            output = sub_formatter.get_output().strip()
                            if output:
                                lines.append(output)
                        lines.append("")

                    # Ungrouped Options
                    if sub_option_panels:
                        lines.append("**Options**:\n")
                        for _group, panel in sub_option_panels:
                            sub_formatter.reset()
                            sub_formatter(None, None, panel)
                            output = sub_formatter.get_output().strip()
                            if output:
                                lines.append(output)
                        lines.append("")

                    # Grouped Options (e.g., Condiments, Toppings)
                    if sub_grouped_panels:
                        for _group, panel in sub_grouped_panels:
                            if panel.title:
                                lines.append(f"**{panel.title}**:\n")
                                sub_formatter.reset()
                                panel_copy = panel.__class__(
                                    title="",  # Don't show title again in formatter
                                    entries=panel.entries,
                                    format=panel.format,
                                    description=panel.description,
                                )
                                sub_formatter(None, None, panel_copy)
                                output = sub_formatter.get_output().strip()
                                if output:
                                    lines.append(output)
                                lines.append("")

                    # Commands - only show list if not recursively documenting them
                    if sub_command_panels:
                        # Check if we'll be recursively documenting these commands
                        will_recurse = recursive and subapp._commands
                        if will_recurse:
                            # Just show a simple command list without the duplicate heading
                            lines.append("**Commands**:\n")
                            for _group, panel in sub_command_panels:
                                for entry in panel.entries:
                                    if entry.names:
                                        cmd_name = entry.names[0]
                                        desc_text = (
                                            extract_text(entry.description, None, preserve_markup=preserve_sub)
                                            if entry.description
                                            else ""
                                        )
                                        lines.append(f"* `{cmd_name}`: {desc_text}")
                            lines.append("")
                        else:
                            # Show full command panel if not recursing
                            lines.append("**Commands**:\n")
                            for _group, panel in sub_command_panels:
                                sub_formatter.reset()
                                sub_formatter(None, None, panel)
                                output = sub_formatter.get_output().strip()
                                if output:
                                    lines.append(output)
                            lines.append("")

            # Recursively handle nested subcommands
            if recursive and subapp._commands:
                for nested_name, nested_app in BaseDocGenerator.iterate_commands(subapp, include_hidden):
                    # Build nested command chain
                    nested_command_chain = BaseDocGenerator.build_command_chain(
                        sub_command_chain, nested_name, app_name
                    )
                    # Determine heading level for nested commands
                    if flatten_commands:
                        nested_heading_level = heading_level
                    else:
                        nested_heading_level = heading_level + 1
                    # Recursively generate docs for nested commands
                    nested_docs = generate_markdown_docs(
                        nested_app,
                        recursive=recursive,
                        include_hidden=include_hidden,
                        heading_level=nested_heading_level,
                        command_chain=nested_command_chain,
                        generate_toc=False,  # Don't generate TOC for nested commands
                        flatten_commands=flatten_commands,
                    )
                    # Just append the generated docs - no title replacement
                    lines.append(nested_docs)
                    lines.append("")

    # Join all lines into final document
    doc = "\n".join(lines).rstrip() + "\n"
    return doc
