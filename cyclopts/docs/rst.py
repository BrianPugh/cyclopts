"""RST documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from cyclopts.core import App


def _normalize_command_filters(
    commands_filter: Optional[List[str]] = None,
    exclude_commands: Optional[List[str]] = None,
) -> Tuple[Optional[Set[str]], Optional[Set[str]]]:
    """Normalize command filter lists by converting underscores to dashes.

    Parameters
    ----------
    commands_filter : Optional[List[str]]
        List of commands to include.
    exclude_commands : Optional[List[str]]
        List of commands to exclude.

    Returns
    -------
    Tuple[Optional[Set[str]], Optional[Set[str]]]
        Normalized include and exclude sets for O(1) lookup.
    """
    normalized_include = None
    if commands_filter is not None:
        normalized_include = {cmd.replace("_", "-") for cmd in commands_filter}

    normalized_exclude = None
    if exclude_commands:
        normalized_exclude = {cmd.replace("_", "-") for cmd in exclude_commands}

    return normalized_include, normalized_exclude


def _should_include_command(
    name: str,
    parent_path: List[str],
    normalized_commands_filter: Optional[Set[str]],
    normalized_exclude_commands: Optional[Set[str]],
    subapp: "App",
) -> bool:
    """Determine if a command should be included based on filters.

    Parameters
    ----------
    name : str
        The command name.
    parent_path : List[str]
        Path to parent commands.
    normalized_commands_filter : Optional[Set[str]]
        Set of commands to include (already normalized).
    normalized_exclude_commands : Optional[Set[str]]
        Set of commands to exclude (already normalized).
    subapp : App
        The subcommand App instance.

    Returns
    -------
    bool
        True if the command should be included, False otherwise.
    """
    # Build the full command path for nested commands
    full_path = ".".join(parent_path + [name]) if parent_path else name

    # Check exclusion list first
    if normalized_exclude_commands:
        # Check both the command name and full path
        if name in normalized_exclude_commands or full_path in normalized_exclude_commands:
            return False
        # Check if any parent path is excluded
        for i in range(len(parent_path)):
            parent_segment = ".".join(parent_path[: i + 1])
            if parent_segment in normalized_exclude_commands:
                return False

    # Check inclusion list
    if normalized_commands_filter is not None:
        # Check if command name or full path is in the filter
        if name in normalized_commands_filter or full_path in normalized_commands_filter:
            return True

        # Check if any parent path is included (to include all subcommands)
        for i in range(len(parent_path)):
            parent_segment = ".".join(parent_path[: i + 1])
            if parent_segment in normalized_commands_filter:
                return True

        # Also check if just the base command name matches for top-level commands
        if not parent_path and name in normalized_commands_filter:
            return True

        # Check if any child commands should be included
        if hasattr(subapp, "_commands") and subapp._commands:
            # Check if any filter starts with this command's full path
            for filter_cmd in normalized_commands_filter:
                if filter_cmd.startswith(full_path + "."):
                    return True

        return False

    # No filter specified, include by default
    return True


def _adjust_filters_for_subcommand(
    name: str,
    normalized_commands_filter: Optional[Set[str]],
    normalized_exclude_commands: Optional[Set[str]],
) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """Adjust filter lists for subcommand context.

    Parameters
    ----------
    name : str
        The current command name.
    normalized_commands_filter : Optional[Set[str]]
        Set of commands to include (already normalized).
    normalized_exclude_commands : Optional[Set[str]]
        Set of commands to exclude (already normalized).

    Returns
    -------
    Tuple[Optional[List[str]], Optional[List[str]]]
        Adjusted commands_filter and exclude_commands lists (denormalized).
    """
    sub_commands_filter = None
    if normalized_commands_filter is not None:
        sub_commands_filter = []
        for filter_cmd in normalized_commands_filter:
            # If filter starts with current command name + ".", strip the prefix
            if filter_cmd.startswith(name + "."):
                sub_filter = filter_cmd[len(name) + 1 :]
                # Convert back to original format for recursive call
                sub_commands_filter.append(sub_filter.replace("-", "_"))
            # If filter matches exactly, include all subcommands (pass None)
            elif filter_cmd == name:
                sub_commands_filter = None
                break

        # If we have an empty list, no subcommands should be shown
        if sub_commands_filter == []:
            sub_commands_filter = []

    sub_exclude_commands = None
    if normalized_exclude_commands:
        sub_exclude_commands = []
        for exclude_cmd in normalized_exclude_commands:
            # If exclude starts with current command name + ".", strip the prefix
            if exclude_cmd.startswith(name + "."):
                sub_exclude = exclude_cmd[len(name) + 1 :]
                sub_exclude_commands.append(sub_exclude.replace("-", "_"))
            # Keep other exclusions unchanged (convert back to original)
            else:
                sub_exclude_commands.append(exclude_cmd.replace("-", "_"))

    return sub_commands_filter, sub_exclude_commands


def _collect_commands_for_toc(
    app: "App",
    include_hidden: bool = False,
    prefix: str = "",
    commands_filter: Optional[List[str]] = None,
    exclude_commands: Optional[List[str]] = None,
    parent_path: Optional[List[str]] = None,
) -> List[Tuple[str, str, "App"]]:
    """Recursively collect all commands for table of contents.

    Returns a list of (display_name, anchor, app) tuples.
    """
    commands = []

    if not app._commands:
        return commands

    if parent_path is None:
        parent_path = []

    # Normalize filter lists for efficient lookup
    normalized_commands_filter, normalized_exclude_commands = _normalize_command_filters(
        commands_filter, exclude_commands
    )

    for name, subapp in app._commands.items():
        # Skip built-in commands
        if name in app._help_flags or name in app._version_flags:
            continue

        # Check if this is an App instance (subcommand) and should be shown
        if hasattr(subapp, "show"):
            if not include_hidden and not subapp.show:
                continue

        # Apply command filtering
        if not _should_include_command(
            name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
        ):
            continue

        # Create display name and anchor
        display_name = f"{prefix}{name}" if prefix else name
        # For RST, anchors work differently - they're explicit labels
        anchor = display_name.replace(" ", "-").lower()

        commands.append((display_name, anchor, subapp))

        # Recursively collect nested commands
        nested_path = parent_path + [name]
        nested = _collect_commands_for_toc(
            subapp,
            include_hidden=include_hidden,
            prefix=f"{display_name} ",
            commands_filter=commands_filter,  # Pass original filters, they'll be normalized in recursive call
            exclude_commands=exclude_commands,  # Pass original filters, they'll be normalized in recursive call
            parent_path=nested_path,
        )
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
    flatten_commands: bool = False,
    commands_filter: Optional[list[str]] = None,
    exclude_commands: Optional[list[str]] = None,
    no_root_title: bool = False,
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
    flatten_commands : bool
        If True, generate all commands at the same heading level instead of nested.
        Default is False.
    commands_filter : list[str], optional
        If specified, only include commands in this list.
        Supports nested command paths like "db.migrate".
        Default is None (include all commands).
    exclude_commands : list[str], optional
        If specified, exclude commands in this list.
        Supports nested command paths like "db.migrate".
        Default is None (no exclusions).
    no_root_title : bool
        If True, skip generating the root application title.
        Useful when embedding in existing documentation with its own title.
        Default is False.

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
        app_name = app.name[0]
        title = app_name
    else:
        # Nested command - build full path
        app_name = command_chain[0] if command_chain else app.name[0]
        # Use clean section headers - remove root command from title
        title = " ".join(command_chain[1:]) if len(command_chain) > 1 else command_chain[-1]

    # Always generate RST anchor/label with improved namespacing
    # Create a safe anchor name from the app name and command path
    anchor_parts = ["cyclopts"]
    if command_chain:
        # For subcommands, include the full hierarchy
        anchor_parts.extend(command_chain)
    else:
        # For root, just use the app name
        anchor_parts.append(app_name)
    anchor_name = "-".join(anchor_parts).replace(" ", "-").replace("/", "-").lower()
    lines.append(f".. _{anchor_name}:")
    lines.append("")

    # Determine effective heading level for this command
    if no_root_title and not command_chain:
        # Skip title entirely for root when no_root_title is True
        effective_heading_level = heading_level
    elif flatten_commands and command_chain:
        # When flattening, all commands use the same heading level
        effective_heading_level = heading_level
    else:
        # Normal hierarchical: increment level for nested commands
        effective_heading_level = heading_level + len(command_chain) - 1 if command_chain else heading_level

    # Add title
    if not (no_root_title and not command_chain):
        header_lines = _make_section_header(title, effective_heading_level)
        lines.extend(header_lines)
        lines.append("")

    # Add application description
    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = format_doc(app, help_format)
    if description:
        # Extract plain text from description
        # Preserve markup when help_format matches output format (RST)
        preserve = help_format in ("restructuredtext", "rst")
        desc_text = _extract_plain_text(description, None, preserve_markup=preserve)
        if desc_text:
            lines.append(desc_text.strip())
            lines.append("")

    # Skip TOC generation (sections integrate with Sphinx's toctree)
    if False:  # Previously: generate_toc and not command_chain and app._commands
        # Collect all commands recursively for TOC
        toc_commands = _collect_commands_for_toc(
            app,
            include_hidden=include_hidden,
            commands_filter=commands_filter,
            exclude_commands=exclude_commands,
        )
        if toc_commands:
            _generate_toc_entries(lines, toc_commands, app_name=app_name)
            lines.append("")

    # Add usage section - only if we have a parent title
    if not (no_root_title and not command_chain) and command_chain:
        # Render usage as bold text for subcommands
        lines.append("**Usage:**")
        lines.append("")

    # Generate usage line - only if we're documenting a specific command
    if not (no_root_title and not command_chain):
        # For subcommands, we need to construct the usage with the full command path
        if command_chain:
            # Create a mock usage string with the full command path
            from rich.text import Text

            from cyclopts.help import format_usage

            usage_parts = ["Usage:"] + list(command_chain)

            # Check if the app has commands
            if any(app[x].show for x in app._registered_commands):
                usage_parts.append("COMMAND")

            # Check for arguments/options
            help_panels_with_groups = app._assemble_help_panels(
                [], app.app_stack.resolve("help_format", fallback="restructuredtext")
            )
            has_args = False
            has_options = False
            for _, panel in help_panels_with_groups:
                if panel.format == "parameter":
                    for entry in panel.entries:
                        if entry.required and entry.default is None:
                            has_args = True
                        else:
                            has_options = True

            # Check for default command (only add [ARGS] if no explicit args were found)
            if app.default_command and not has_args:
                usage_parts.append("[ARGS]")
            elif has_args:
                usage_parts.append("[ARGS]")

            if has_options:
                usage_parts.append("[OPTIONS]")

            usage = Text(" ".join(usage_parts))
        else:
            # Root command - use format_usage normally
            usage = format_usage(app, [])
        usage_text = _extract_plain_text(usage, None, preserve_markup=False)
        if usage_text:
            # Use literal block with double colon
            lines.append("::")
            lines.append("")
            # Indent usage text with 4 spaces for literal block
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
    if argument_panels and not (no_root_title and not command_chain):
        # Use bold text instead of subsections
        lines.append("**Arguments:**")
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
    if (option_panels or grouped_panels) and not (no_root_title and not command_chain):
        # Use bold text instead of subsections
        lines.append("**Options:**")
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

    # Skip command list entirely (sections integrate with Sphinx's toctree)
    # Command panels are not rendered in sections mode

    # Recursively document subcommands
    if recursive and app._commands:
        # Normalize filter lists for efficient lookup
        normalized_commands_filter, normalized_exclude_commands = _normalize_command_filters(
            commands_filter, exclude_commands
        )
        # parent_path should be empty at each app's root level, not the command chain
        parent_path = []

        for name, subapp in app._commands.items():
            # Skip built-in commands
            if name in app._help_flags or name in app._version_flags:
                continue

            # Check if this is an App instance (subcommand) and should be shown
            if hasattr(subapp, "show"):
                if not include_hidden and not subapp.show:
                    continue

            # Apply command filtering
            if not _should_include_command(
                name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
            ):
                continue

            # Add some spacing before subcommand
            lines.append("")

            # Recursively generate docs for subcommand
            subcommand_chain = command_chain + [name] if command_chain else [app_name, name]
            # When flattening, keep the same base heading level; otherwise increment
            if flatten_commands:
                next_heading_level = heading_level
            else:
                # Normal hierarchical mode - don't increment heading_level, let the chain length determine it
                next_heading_level = heading_level

            # Adjust filters for the subcommand context
            sub_commands_filter, sub_exclude_commands = _adjust_filters_for_subcommand(
                name, normalized_commands_filter, normalized_exclude_commands
            )

            subdocs = generate_rst_docs(
                subapp,
                recursive=recursive,
                include_hidden=include_hidden,
                heading_level=next_heading_level,
                command_chain=subcommand_chain,
                generate_toc=False,  # Only generate TOC at root level
                flatten_commands=flatten_commands,
                commands_filter=sub_commands_filter,
                exclude_commands=sub_exclude_commands,
                no_root_title=False,  # Subcommands should have titles
            )
            lines.append(subdocs)

    return "\n".join(lines)
