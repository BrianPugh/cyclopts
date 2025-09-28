"""RST documentation generation functions for cyclopts apps."""

import sys
from pathlib import Path
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

        # Check if this is an App instance (subcommand) and should be shown
        if hasattr(subapp, "show"):
            if not include_hidden and not subapp.show:
                continue

        # Create display name and anchor
        display_name = f"{prefix}{name}" if prefix else name
        # For RST, anchors work differently - they're explicit labels
        anchor = display_name.replace(" ", "-").lower()

        commands.append((display_name, anchor, subapp))

        # Recursively collect nested commands
        nested = _collect_commands_for_toc(subapp, include_hidden=include_hidden, prefix=f"{display_name} ")
        commands.extend(nested)

    return commands


def _generate_toc_entries(
    lines: List[str], commands: List[Tuple[str, str, "App"]], app_name: Optional[str] = None
) -> None:
    """Generate TOC entries with proper indentation for RST."""
    if not commands:
        return

    lines.append(".. contents:: Commands")
    lines.append("   :local:")
    lines.append("   :depth: 2")
    lines.append("")


def _make_section_header(title: str, level: int) -> List[str]:
    """Create an RST section header.

    Parameters
    ----------
    title : str
        Section title.
    level : int
        Heading level (1-6).

    Returns
    -------
    List[str]
        RST formatted section header lines.
    """
    # RST section markers in order
    markers = {
        1: "=",
        2: "-",
        3: "^",
        4: '"',
        5: "'",
        6: "~",
    }

    if level < 1:
        level = 1
    elif level > 6:
        level = 6

    marker = markers[level]
    underline = marker * len(title)

    # Level 1 gets both overline and underline
    if level == 1:
        return [underline, title, underline]
    else:
        return [title, underline]


def generate_rst_docs(
    app: "App",
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
    command_chain: Optional[list[str]] = None,
    generate_toc: bool = True,
) -> str:
    """Generate reStructuredText documentation for a CLI application.

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
        Default is 1 (uses '=' markers).
    command_chain : list[str]
        Internal parameter to track command hierarchy.
        Default is None.
    generate_toc : bool
        If True, generate a table of contents for multi-command apps.
        Default is True.

    Returns
    -------
    str
        The generated RST documentation.
    """
    from cyclopts.help import format_doc, format_usage
    from cyclopts.help.formatters.rst import RstFormatter, _extract_plain_text

    # Build the main documentation
    lines = []

    # Initialize command chain if not provided
    if command_chain is None:
        command_chain = []

    # Determine the app name and full command path
    if not command_chain:
        # Root level - use app name or derive from sys.argv
        app_name = app.name[0] if app._name else Path(sys.argv[0]).name
        full_command = app_name
        title = app_name
    else:
        # Nested command - build full path
        app_name = command_chain[0] if command_chain else app.name[0]
        full_command = " ".join(command_chain)
        title = f"``{full_command}``"

    # Add title
    header_lines = _make_section_header(title, heading_level)
    lines.extend(header_lines)
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

    # Generate table of contents if this is the root level and has commands
    if generate_toc and not command_chain and app._commands:
        # Collect all commands recursively for TOC
        toc_commands = _collect_commands_for_toc(app, include_hidden=include_hidden)
        if toc_commands:
            _generate_toc_entries(lines, toc_commands, app_name=app_name)
            lines.append("")

    # Add usage section
    usage_heading = _make_section_header("Usage", heading_level + 1)
    lines.extend(usage_heading)
    lines.append("")

    # Generate usage line
    usage = format_usage(app, [])
    usage_text = _extract_plain_text(usage, None)
    if usage_text:
        lines.append("::")
        lines.append("")
        # Indent usage text
        for line in usage_text.split("\n"):
            lines.append(f"    {line}")
        lines.append("")

    # Get help panels for the current app
    help_panels_with_groups = app._assemble_help_panels([], help_format)

    # Create formatter for help panels
    formatter = RstFormatter(heading_level=heading_level + 1, include_hidden=include_hidden)

    # Separate panels into categories
    command_panels = []
    argument_panels = []
    option_panels = []
    grouped_panels = []

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
                    argument_panels.append((group, panel))
                elif group_name and group_name not in ["Parameters", "Options"]:
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

    # Render panels in order: Arguments, Options, Commands
    # Render arguments
    if argument_panels:
        arg_heading = _make_section_header("Arguments", heading_level + 1)
        lines.extend(arg_heading)
        lines.append("")
        for _, panel in argument_panels:
            formatter.reset()
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
                lines.append("")

    # Render options
    if option_panels or grouped_panels:
        opt_heading = _make_section_header("Options", heading_level + 1)
        lines.extend(opt_heading)
        lines.append("")

        # First render ungrouped options
        for _, panel in option_panels:
            formatter.reset()
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
                lines.append("")

        # Then render grouped options
        for _, panel in grouped_panels:
            formatter.reset()
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
                lines.append("")

    # Render commands
    if command_panels:
        cmd_heading = _make_section_header("Commands", heading_level + 1)
        lines.extend(cmd_heading)
        lines.append("")
        for _, panel in command_panels:
            formatter.reset()
            panel.title = ""
            formatter(None, None, panel)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
                lines.append("")

    # Recursively document subcommands
    if recursive and app._commands:
        for name, subapp in app._commands.items():
            # Skip built-in commands
            if name in app._help_flags or name in app._version_flags:
                continue

            # Check if this is an App instance (subcommand) and should be shown
            if hasattr(subapp, "show"):
                if not include_hidden and not subapp.show:
                    continue

            # Add some spacing before subcommand
            lines.append("")

            # Recursively generate docs for subcommand
            subcommand_chain = command_chain + [name] if command_chain else [app_name, name]
            subdocs = generate_rst_docs(
                subapp,
                recursive=recursive,
                include_hidden=include_hidden,
                heading_level=heading_level + 1,
                command_chain=subcommand_chain,
                generate_toc=False,  # Only generate TOC at root level
            )
            lines.append(subdocs)

    return "\n".join(lines)
