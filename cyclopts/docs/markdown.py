"""Documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from cyclopts.core import App


def _collect_commands_for_toc(
    app: "App", include_hidden: bool = False, prefix: str = ""
) -> List[Tuple[str, str, "App"]]:
    """Recursively collect all commands for table of contents.

    Returns a list of (display_name, anchor, app) tuples.
    """
    commands = []

    if not app._commands:
        return commands

    for name, subapp in app._commands.items():
        # Skip built-in commands
        if name in app._help_flags or name in app._version_flags:
            continue

        if isinstance(subapp, type(app)):  # Check if it's an App instance
            if not include_hidden and not subapp.show:
                continue

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
    lines: List[str], commands: List[Tuple[str, str, "App"]], level: int = 0, app_name: Optional[str] = None
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
    command_chain: Optional[list[str]] = None,
    generate_toc: bool = True,
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

    Returns
    -------
    str
        The generated markdown documentation.
    """
    from cyclopts.help import format_doc, format_usage
    from cyclopts.help.formatters.markdown import MarkdownFormatter, _extract_plain_text

    # Build the main documentation
    lines = []

    # Initialize command chain if not provided
    if command_chain is None:
        command_chain = []

    # Determine the app name and full command path
    if not command_chain:
        # Root level - use app name or derive from sys.argv
        app_name = app.name[0]
        full_command = app_name
        title = app_name
    else:
        # Nested command - build full path
        app_name = command_chain[0] if command_chain else app.name[0]
        full_command = " ".join(command_chain)
        title = f"`{full_command}`"

    lines.append(f"{'#' * heading_level} {title}")
    lines.append("")

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = format_doc(app, help_format)
    if description:
        # Extract plain text from description
        # Preserve markup when help_format matches output format (markdown)
        preserve = help_format in ("markdown", "md")
        desc_text = _extract_plain_text(description, None, preserve_markup=preserve)
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
    if app.usage is None:
        usage = format_usage(app, [])
        if usage:
            lines.append("**Usage**:")
            lines.append("")
            lines.append("```console")
            usage_text = _extract_plain_text(usage, None, preserve_markup=False)
            # Ensure usage starts with $ for console style
            usage_line = usage_text.strip()
            if "Usage:" in usage_line:
                usage_line = usage_line.replace("Usage: ", "")
            # Replace the app name in usage with full command path
            parts = usage_line.split(" ", 1)
            if len(parts) > 1 and not command_chain:
                usage_line = f"{app_name} {parts[1]}"
            elif command_chain:
                usage_line = f"{full_command} {parts[1] if len(parts) > 1 else ''}".strip()
            if not usage_line.startswith("$"):
                usage_line = f"$ {usage_line}"
            lines.append(usage_line)
            lines.append("```")
            lines.append("")
    elif app.usage:  # Non-empty custom usage
        lines.append("**Usage**:")
        lines.append("")
        lines.append("```console")
        usage_line = app.usage.strip()
        if not usage_line.startswith("$"):
            usage_line = f"$ {usage_line}"
        lines.append(usage_line)
        lines.append("```")
        lines.append("")

    # Get help panels for the current app
    help_panels_with_groups = app._assemble_help_panels([], help_format)

    # Separate panels into categories for organized output
    command_panels = []
    argument_panels = []
    option_panels = []  # Ungrouped options
    grouped_panels = []  # Options with custom groups

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

        if panel.entries:
            if panel.format == "command":
                command_panels.append((group, panel))
            elif panel.format == "parameter":
                # Check panel title to determine how to handle it
                group_name = panel.title

                # Handle "Arguments" panel specially
                if group_name == "Arguments":
                    # These are positional arguments
                    argument_panels.append((group, panel))
                elif group_name in ["Condiments", "Toppings"] or (
                    group_name and group_name not in ["Parameters", "Options"]
                ):
                    # This is a custom group - keep it as-is
                    grouped_panels.append((group, panel))
                else:
                    # Regular parameters - separate into args and options
                    args = []
                    opts = []
                    for entry in panel.entries:
                        is_positional = entry.required and entry.default is None
                        if is_positional:
                            args.append(entry)
                        else:
                            opts.append(entry)

                    if args:
                        arg_panel = panel.__class__(title="", entries=args, format=panel.format, description=None)
                        argument_panels.append((group, arg_panel))

                    if opts:
                        opt_panel = panel.__class__(title="", entries=opts, format=panel.format, description=None)
                        option_panels.append((group, opt_panel))

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

                # Generate subcommand documentation in Typer style
                lines.append(f"{'#' * (heading_level + 1)} `{' '.join(sub_command_chain)}`")
                lines.append("")

                # Get subapp help
                with subapp.app_stack([subapp]):
                    sub_help_format = subapp.app_stack.resolve("help_format", fallback=help_format)
                    # Preserve markup when sub_help_format matches output format (markdown)
                    preserve_sub = sub_help_format in ("markdown", "md")
                    sub_description = format_doc(subapp, sub_help_format)
                    if sub_description:
                        sub_desc_text = _extract_plain_text(sub_description, None, preserve_markup=preserve_sub)
                        if sub_desc_text:
                            lines.append(sub_desc_text.strip())
                            lines.append("")

                    # Generate usage for subcommand
                    if subapp.usage is None:
                        # Generate usage for the subcommand
                        sub_usage = format_usage(subapp, [])
                        if sub_usage:
                            lines.append("**Usage**:")
                            lines.append("")
                            lines.append("```console")
                            sub_usage_text = _extract_plain_text(sub_usage, None, preserve_markup=False)
                            # Build the proper command chain for display
                            usage_line = sub_usage_text.strip()
                            if "Usage:" in usage_line:
                                usage_line = usage_line.replace("Usage: ", "")
                            # Build the full command path for usage
                            usage_parts = usage_line.split(" ", 1)
                            full_cmd = " ".join(sub_command_chain)
                            if len(usage_parts) > 1:
                                usage_line = f"{full_cmd} {usage_parts[1]}"
                            else:
                                usage_line = full_cmd
                            if not usage_line.startswith("$"):
                                usage_line = f"$ {usage_line}"
                            lines.append(usage_line)
                            lines.append("```")
                            lines.append("")
                    elif subapp.usage:
                        lines.append("**Usage**:")
                        lines.append("")
                        lines.append("```console")
                        usage_line = subapp.usage.strip()
                        if not usage_line.startswith("$"):
                            usage_line = f"$ {usage_line}"
                        lines.append(usage_line)
                        lines.append("```")
                        lines.append("")

                    # Only show subcommand panels if we're in recursive mode
                    # (Otherwise we just show the basic info about this command)
                    if recursive:
                        # Get help panels for subcommand
                        sub_panels = subapp._assemble_help_panels([], sub_help_format)

                        # Separate panels for organized output
                        sub_argument_panels = []
                        sub_option_panels = []  # Ungrouped options
                        sub_grouped_panels = []  # Options with custom groups
                        sub_command_panels = []

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
                                if sub_panel.format == "command":
                                    sub_command_panels.append((sub_group, sub_panel))
                                elif sub_panel.format == "parameter":
                                    # Check if this panel has a custom group name
                                    group_name = sub_panel.title

                                    # Handle "Arguments" panel specially
                                    if group_name == "Arguments":
                                        # These are positional arguments
                                        sub_argument_panels.append((sub_group, sub_panel))
                                    elif group_name in ["Condiments", "Toppings"] or (
                                        group_name and group_name not in ["Parameters", "Options"]
                                    ):
                                        # This is a custom group - keep it as-is
                                        sub_grouped_panels.append((sub_group, sub_panel))
                                    else:
                                        # Regular parameters - separate into args and options
                                        args = []
                                        opts = []
                                        for entry in sub_panel.entries:
                                            is_positional = entry.required and entry.default is None
                                            if is_positional:
                                                args.append(entry)
                                            else:
                                                opts.append(entry)

                                        if args:
                                            arg_panel = sub_panel.__class__(
                                                title="", entries=args, format=sub_panel.format, description=None
                                            )
                                            sub_argument_panels.append((sub_group, arg_panel))

                                        if opts:
                                            opt_panel = sub_panel.__class__(
                                                title="", entries=opts, format=sub_panel.format, description=None
                                            )
                                            sub_option_panels.append((sub_group, opt_panel))

                        # Render panels in Typer order
                        sub_formatter = MarkdownFormatter(
                            heading_level=heading_level + 2, include_hidden=include_hidden, table_style="list"
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
                                                _extract_plain_text(
                                                    entry.description, None, preserve_markup=preserve_sub
                                                )
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
                                    nested_command_chain = sub_command_chain + [nested_name]
                                    # Recursively generate docs for nested commands
                                    nested_docs = generate_markdown_docs(
                                        nested_app,
                                        recursive=recursive,
                                        include_hidden=include_hidden,
                                        heading_level=heading_level + 1,
                                        command_chain=nested_command_chain,
                                        generate_toc=False,  # Don't generate TOC for nested commands
                                    )
                                    # Just append the generated docs - no title replacement
                                    lines.append(nested_docs)
                                    lines.append("")

    # Join all lines into final document
    doc = "\n".join(lines).rstrip() + "\n"
    return doc
