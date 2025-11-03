"""Documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING

from cyclopts._markup import extract_text
from cyclopts.docs.base import BaseDocGenerator

if TYPE_CHECKING:
    from cyclopts.core import App


def _normalize_command_filters(
    commands_filter: list[str] | None = None,
    exclude_commands: list[str] | None = None,
) -> tuple[set[str] | None, set[str] | None]:
    """Normalize command filter lists by converting underscores to dashes.

    Parameters
    ----------
    commands_filter : list[str] | None
        List of commands to include.
    exclude_commands : list[str] | None
        List of commands to exclude.

    Returns
    -------
    tuple[set[str] | None, set[str] | None]
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
    parent_path: list[str],
    normalized_commands_filter: set[str] | None,
    normalized_exclude_commands: set[str] | None,
    subapp: "App",
) -> bool:
    """Determine if a command should be included based on filters.

    Parameters
    ----------
    name : str
        The command name.
    parent_path : list[str]
        Path to parent commands.
    normalized_commands_filter : set[str] | None
        Set of commands to include (already normalized).
    normalized_exclude_commands : set[str] | None
        Set of commands to exclude (already normalized).
    subapp : App
        The subcommand App instance.

    Returns
    -------
    bool
        True if the command should be included, False otherwise.
    """
    full_path = ".".join(parent_path + [name]) if parent_path else name

    if normalized_exclude_commands:
        if name in normalized_exclude_commands or full_path in normalized_exclude_commands:
            return False
        for i in range(len(parent_path)):
            parent_segment = ".".join(parent_path[: i + 1])
            if parent_segment in normalized_exclude_commands:
                return False

    if normalized_commands_filter is not None:
        if name in normalized_commands_filter or full_path in normalized_commands_filter:
            return True

        for i in range(len(parent_path)):
            parent_segment = ".".join(parent_path[: i + 1])
            if parent_segment in normalized_commands_filter:
                return True

        if not parent_path and name in normalized_commands_filter:
            return True

        if hasattr(subapp, "_commands") and subapp._commands:
            for filter_cmd in normalized_commands_filter:
                if filter_cmd.startswith(full_path + "."):
                    return True

        return False

    return True


def _adjust_filters_for_subcommand(
    name: str,
    normalized_commands_filter: set[str] | None,
    normalized_exclude_commands: set[str] | None,
) -> tuple[list[str] | None, list[str] | None]:
    """Adjust filter lists for subcommand context.

    Parameters
    ----------
    name : str
        The current command name.
    normalized_commands_filter : set[str] | None
        Set of commands to include (already normalized).
    normalized_exclude_commands : set[str] | None
        Set of commands to exclude (already normalized).

    Returns
    -------
    tuple[list[str] | None, list[str] | None]
        Adjusted commands_filter and exclude_commands lists (denormalized).
    """
    sub_commands_filter = None
    if normalized_commands_filter is not None:
        sub_commands_filter = []
        for filter_cmd in normalized_commands_filter:
            if filter_cmd.startswith(name + "."):
                sub_filter = filter_cmd[len(name) + 1 :]
                sub_commands_filter.append(sub_filter.replace("-", "_"))
            elif filter_cmd == name:
                sub_commands_filter = None
                break

        if sub_commands_filter == []:
            sub_commands_filter = []

    sub_exclude_commands = None
    if normalized_exclude_commands:
        sub_exclude_commands = []
        for exclude_cmd in normalized_exclude_commands:
            if exclude_cmd.startswith(name + "."):
                sub_exclude = exclude_cmd[len(name) + 1 :]
                sub_exclude_commands.append(sub_exclude.replace("-", "_"))
            else:
                sub_exclude_commands.append(exclude_cmd.replace("-", "_"))

    return sub_commands_filter, sub_exclude_commands


def _collect_commands_for_toc(
    app: "App",
    include_hidden: bool = False,
    prefix: str = "",
    commands_filter: list[str] | None = None,
    exclude_commands: list[str] | None = None,
    parent_path: list[str] | None = None,
) -> list[tuple[str, str, "App"]]:
    """Recursively collect all commands for table of contents.

    Returns a list of (display_name, anchor, app) tuples.
    Note: anchor is unused and left for backward compatibility; actual anchors
    are generated in _generate_toc_entries to match heading behavior.
    """
    commands = []

    if not app._commands:
        return commands

    if parent_path is None:
        parent_path = []

    normalized_commands_filter, normalized_exclude_commands = _normalize_command_filters(
        commands_filter, exclude_commands
    )

    for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
        if not _should_include_command(
            name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
        ):
            continue

        display_name = f"{prefix}{name}" if prefix else name
        anchor = display_name.replace(" ", "-").lower()

        commands.append((display_name, anchor, subapp))

        nested_path = parent_path + [name]
        nested = _collect_commands_for_toc(
            subapp,
            include_hidden=include_hidden,
            prefix=f"{display_name} ",
            commands_filter=commands_filter,
            exclude_commands=exclude_commands,
            parent_path=nested_path,
        )
        commands.extend(nested)

    return commands


def _generate_toc_entries(
    lines: list[str],
    commands: list[tuple[str, str, "App"]],
    level: int = 0,
    app_name: str | None = None,
) -> None:
    """Generate TOC entries with proper indentation.

    Parameters
    ----------
    lines : list[str]
        List to append TOC entries to.
    commands : list[tuple[str, str, "App"]]
        List of (display_name, unused_anchor, app) tuples.
    level : int
        Unused, kept for backward compatibility.
    app_name : str | None
        Unused, kept for backward compatibility.
    """
    # Track anchor usage to handle duplicates (e.g., sub1.create and sub2.create both → #create)
    # Markdown processors append _1, _2, etc. to duplicate anchors
    anchor_counts: dict[str, int] = {}

    for display_name, _unused_anchor, _app in commands:
        # Calculate depth based on number of spaces in display name
        # Subtract 1 because app_name prefix is included for anchor matching but not for hierarchy
        depth = display_name.count(" ") - 1
        # Use 4 spaces per level for proper markdown nested lists (CommonMark spec)
        indent = "    " * depth

        # Get just the command name (last part)
        cmd_name = display_name.split()[-1]

        # Generate anchor using shared logic from BaseDocGenerator
        anchor = BaseDocGenerator.generate_anchor(display_name)

        # Handle duplicate anchors the same way markdown processors do
        if anchor in anchor_counts:
            # This is a duplicate - append _N suffix
            anchor_counts[anchor] += 1
            anchor = f"{anchor}_{anchor_counts[anchor]}"
        else:
            # First occurrence of this anchor
            anchor_counts[anchor] = 0

        lines.append(f"{indent}- [`{cmd_name}`](#{anchor})")


def generate_markdown_docs(
    app: "App",
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
    command_chain: list[str] | None = None,
    generate_toc: bool = True,
    flatten_commands: bool = False,
    commands_filter: list[str] | None = None,
    exclude_commands: list[str] | None = None,
    no_root_title: bool = False,
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
    commands_filter : list[str] | None
        If specified, only include commands in this list.
        Supports nested command paths like "db.migrate".
        Default is None (include all commands).
    exclude_commands : list[str] | None
        If specified, exclude commands in this list.
        Supports nested command paths like "db.migrate".
        Default is None (no exclusions).
    no_root_title : bool
        If True, skip the root application title. Used for plugin contexts.
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
    is_root = command_chain is None
    if command_chain is None:
        command_chain = []

    # Determine the app name and full command path
    app_name, full_command, base_title = BaseDocGenerator.get_app_info(app, command_chain)
    # Always use full command path for nested commands to avoid anchor collisions
    # (e.g., "files cp" and "other cp" would both generate #cp without this)
    if command_chain:
        # Show full command path (same for both hierarchical and flattened modes)
        title = f"`{full_command}`"
    else:
        # Root app: use base title
        title = base_title

    # Add title for all levels (unless skipping root title)
    if not (no_root_title and is_root):
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
        # Use app_name as prefix so TOC paths match heading paths (e.g., "myapp files cp")
        toc_commands = _collect_commands_for_toc(
            app,
            include_hidden=include_hidden,
            prefix=f"{app_name} " if app_name else "",
            commands_filter=commands_filter,
            exclude_commands=exclude_commands,
        )
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

    # Normalize filter lists for efficient lookup (used for both panels and recursive docs)
    normalized_commands_filter, normalized_exclude_commands = _normalize_command_filters(
        commands_filter, exclude_commands
    )
    # Parent path is always empty at the current app level. Filters are adjusted for each
    # recursive call via _adjust_filters_for_subcommand(), so filtering logic remains correct
    # without threading parent_path through recursive generate_markdown_docs() calls.
    parent_path = []

    # Build a mapping of command names to App objects for filtering
    command_map = {}
    if app._commands:
        for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden=True):
            command_map[name] = subapp

    # Render commands
    if command_panels:
        # First, collect all filtered panels
        filtered_panels_output = []
        for _group, panel in command_panels:
            # Filter command entries based on commands_filter and exclude_commands
            filtered_entries = []
            for entry in panel.entries:
                if entry.names:
                    cmd_name = entry.names[0]
                    # Get the App object for this command
                    subapp = command_map.get(cmd_name)
                    # If there's no subapp (e.g., --help, --version), include it if no filters are specified
                    if subapp is None:
                        # Non-command entries (like --help, --version) are included if no filters are specified
                        if normalized_commands_filter is None and normalized_exclude_commands is None:
                            filtered_entries.append(entry)
                    else:
                        # Check if this command should be included based on filters
                        if _should_include_command(
                            cmd_name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
                        ):
                            filtered_entries.append(entry)

            # Only render if there are filtered entries
            if filtered_entries:
                formatter.reset()
                # Create a new panel with filtered entries
                filtered_panel = panel.__class__(
                    title="",  # Don't show panel title for commands
                    entries=filtered_entries,
                    format=panel.format,
                    description=panel.description,
                )
                formatter(None, None, filtered_panel)
                output = formatter.get_output().strip()
                if output:
                    filtered_panels_output.append(output)

        # Only add header if there are panels to render
        if filtered_panels_output:
            lines.append("**Commands**:\n")
            for output in filtered_panels_output:
                lines.append(output)
            lines.append("")

    # Handle recursive documentation for subcommands
    if app._commands:
        # Iterate through registered commands using iterate_commands helper
        # This automatically resolves CommandSpec instances
        for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
            # Apply command filtering
            if not _should_include_command(
                name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
            ):
                continue

            # Build the command chain for this subcommand
            sub_command_chain = BaseDocGenerator.build_command_chain(command_chain, name, app_name)

            # Determine heading level for subcommand
            if flatten_commands:
                sub_heading_level = heading_level
            elif no_root_title and not command_chain:
                # When root title is skipped, subcommands "take over" the root heading level
                sub_heading_level = heading_level
            else:
                sub_heading_level = heading_level + 1

            # Generate subcommand documentation
            # Always use full command path to avoid anchor collisions
            display_name = " ".join(sub_command_chain)
            lines.append(f"{'#' * sub_heading_level} `{display_name}`")
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
                    # For root-level commands, use just the command name in usage
                    if command_chain:
                        # Nested command: show full command chain
                        usage_command_chain = sub_command_chain
                    else:
                        # Root-level command: show just the command name
                        usage_command_chain = [name]
                    usage_line = BaseDocGenerator.format_usage_line(sub_usage_text, usage_command_chain, prefix="$")
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
                        # Adjust filters for the subcommand context to apply when rendering Commands section
                        sub_commands_filter_for_panel, sub_exclude_commands_for_panel = _adjust_filters_for_subcommand(
                            name, normalized_commands_filter, normalized_exclude_commands
                        )
                        normalized_sub_filter_panel, normalized_sub_exclude_panel = _normalize_command_filters(
                            sub_commands_filter_for_panel, sub_exclude_commands_for_panel
                        )

                        # Build a map of command names to App objects for filtering
                        sub_command_map = {}
                        if subapp._commands:
                            for sub_cmd_name, sub_cmd_app in BaseDocGenerator.iterate_commands(
                                subapp, include_hidden=True
                            ):
                                sub_command_map[sub_cmd_name] = sub_cmd_app

                        # Build parent path for nested commands
                        nested_parent_path_for_panel = parent_path + [name] if parent_path else [name]

                        # Check if we'll be recursively documenting these commands
                        will_recurse = recursive and subapp._commands
                        if will_recurse:
                            # Just show a simple command list without the duplicate heading
                            # Collect entries first to check if there are any
                            command_entries = []
                            for _group, panel in sub_command_panels:
                                for entry in panel.entries:
                                    if entry.names:
                                        cmd_name = entry.names[0]
                                        # Apply filtering
                                        sub_cmd_app = sub_command_map.get(cmd_name)
                                        if sub_cmd_app and not _should_include_command(
                                            cmd_name,
                                            nested_parent_path_for_panel,
                                            normalized_sub_filter_panel,
                                            normalized_sub_exclude_panel,
                                            sub_cmd_app,
                                        ):
                                            continue

                                        desc_text = (
                                            extract_text(entry.description, None, preserve_markup=preserve_sub)
                                            if entry.description
                                            else ""
                                        )
                                        command_entries.append(f"* `{cmd_name}`: {desc_text}")
                            # Only add header if there are entries
                            if command_entries:
                                lines.append("**Commands**:\n")
                                lines.extend(command_entries)
                                lines.append("")
                        else:
                            # Show full command panel if not recursing
                            # Filter panel entries based on adjusted filters
                            filtered_panels_output = []
                            for _group, panel in sub_command_panels:
                                filtered_entries = []
                                for entry in panel.entries:
                                    if entry.names:
                                        cmd_name = entry.names[0]
                                        # Apply filtering
                                        sub_cmd_app = sub_command_map.get(cmd_name)
                                        if sub_cmd_app and not _should_include_command(
                                            cmd_name,
                                            nested_parent_path_for_panel,
                                            normalized_sub_filter_panel,
                                            normalized_sub_exclude_panel,
                                            sub_cmd_app,
                                        ):
                                            continue
                                        filtered_entries.append(entry)

                                if filtered_entries:
                                    sub_formatter.reset()
                                    filtered_panel = panel.__class__(
                                        title="",
                                        entries=filtered_entries,
                                        format=panel.format,
                                        description=panel.description,
                                    )
                                    sub_formatter(None, None, filtered_panel)
                                    output = sub_formatter.get_output().strip()
                                    if output:
                                        filtered_panels_output.append(output)

                            # Only add header if there's output
                            if filtered_panels_output:
                                lines.append("**Commands**:\n")
                                lines.extend(filtered_panels_output)
                                lines.append("")

            # Recursively handle nested subcommands
            if recursive and subapp._commands:
                # Adjust filters for this subcommand context
                sub_commands_filter, sub_exclude_commands = _adjust_filters_for_subcommand(
                    name, normalized_commands_filter, normalized_exclude_commands
                )

                # Normalize the adjusted filters for checking
                normalized_sub_filter, normalized_sub_exclude = _normalize_command_filters(
                    sub_commands_filter, sub_exclude_commands
                )

                # Build parent path for nested commands
                nested_parent_path = parent_path + [name] if parent_path else [name]

                for nested_name, nested_app in BaseDocGenerator.iterate_commands(subapp, include_hidden):
                    # Apply filtering to nested commands
                    if not _should_include_command(
                        nested_name, nested_parent_path, normalized_sub_filter, normalized_sub_exclude, nested_app
                    ):
                        continue

                    # Build nested command chain
                    nested_command_chain = BaseDocGenerator.build_command_chain(
                        sub_command_chain, nested_name, app_name
                    )
                    # Determine heading level for nested commands
                    if flatten_commands:
                        nested_heading_level = heading_level
                    else:
                        nested_heading_level = sub_heading_level + 1
                    # Recursively generate docs for nested commands
                    nested_docs = generate_markdown_docs(
                        nested_app,
                        recursive=recursive,
                        include_hidden=include_hidden,
                        heading_level=nested_heading_level,
                        command_chain=nested_command_chain,
                        generate_toc=False,  # Don't generate TOC for nested commands
                        flatten_commands=flatten_commands,
                        commands_filter=sub_commands_filter,
                        exclude_commands=sub_exclude_commands,
                        no_root_title=False,  # Always show title for nested commands
                    )
                    # Just append the generated docs - no title replacement
                    lines.append(nested_docs)
                    lines.append("")

    # Join all lines into final document
    doc = "\n".join(lines).rstrip() + "\n"
    return doc
