"""RST documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING

from cyclopts._markup import extract_text
from cyclopts.docs.base import BaseDocGenerator
from cyclopts.help.formatters._shared import make_rst_section_header

if TYPE_CHECKING:
    from cyclopts.core import App


def _normalize_command_filters(
    commands_filter: list[str] | None = None,
    exclude_commands: list[str] | None = None,
) -> tuple[set[str] | None, set[str] | None]:
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
            if filter_cmd.startswith(name + "."):
                sub_filter = filter_cmd[len(name) + 1 :]
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
    """
    commands = []

    if not app._commands:
        return commands

    if parent_path is None:
        parent_path = []

    normalized_commands_filter, normalized_exclude_commands = _normalize_command_filters(
        commands_filter, exclude_commands
    )

    # Use BaseDocGenerator.iterate_commands to automatically resolve CommandSpec
    for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
        if not _should_include_command(
            name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
        ):
            continue

        display_name = f"{prefix}{name}" if prefix else name
        # For RST, anchors work differently - they're explicit labels
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
    lines: list[str], commands: list[tuple[str, str, "App"]], app_name: str | None = None
) -> None:
    """Generate TOC entries with proper indentation for RST."""
    if not commands:
        return

    lines.append(".. contents:: Commands")
    lines.append("   :local:")
    lines.append("   :depth: 2")
    lines.append("")


def generate_rst_docs(
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
    from cyclopts.help.formatters.rst import RstFormatter

    lines = []

    if command_chain is None:
        command_chain = []

    app_name, full_command, base_title = BaseDocGenerator.get_app_info(app, command_chain)
    # Use clean section headers - remove root command from title for nested commands
    if command_chain:
        title = " ".join(command_chain[1:]) if len(command_chain) > 1 else command_chain[-1]
    else:
        title = base_title

    # Always generate RST anchor/label with improved namespacing
    anchor_parts = ["cyclopts"]
    if command_chain:
        anchor_parts.extend(command_chain)
    else:
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

    if not (no_root_title and not command_chain):
        header_lines = make_rst_section_header(title, effective_heading_level)
        lines.extend(header_lines)
        lines.append("")

    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = BaseDocGenerator.extract_description(app, help_format)
    if description:
        # Extract plain text from description
        # Preserve markup when help_format matches output format (RST)
        preserve = help_format in ("restructuredtext", "rst")
        desc_text = extract_text(description, None, preserve_markup=preserve)
        if desc_text:
            lines.append(desc_text.strip())
            lines.append("")

    # Add usage section - only if we have a parent title
    if not (no_root_title and not command_chain) and command_chain:
        # Render usage as bold text for subcommands
        lines.append("**Usage:**")
        lines.append("")

    # Generate usage line - only if we're documenting a specific command
    if not (no_root_title and not command_chain):
        # Extract usage from app
        usage = BaseDocGenerator.extract_usage(app)
        usage_text = None
        if usage:
            if isinstance(usage, str):
                usage_text = usage
            else:
                usage_text = extract_text(usage, None, preserve_markup=False)

            # Format usage with command chain if this is a subcommand
            if command_chain:
                usage_text = BaseDocGenerator.format_usage_line(usage_text, command_chain, prefix="")

            # Remove "Usage:" prefix if present as we'll add it back in the RST format
            if "Usage:" in usage_text:
                usage_text = usage_text.replace("Usage:", "").strip()

            # Add "Usage:" label
            usage_text = f"Usage: {usage_text}"

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
    categorized = BaseDocGenerator.categorize_panels(help_panels_with_groups, include_hidden)
    # Command panels are not rendered in RST mode (sections integrate with Sphinx's toctree)
    argument_panels = categorized["arguments"]
    option_panels = categorized["options"]
    grouped_panels = categorized["grouped"]

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

        # Use BaseDocGenerator.iterate_commands to automatically resolve CommandSpec
        for name, subapp in BaseDocGenerator.iterate_commands(app, include_hidden):
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
