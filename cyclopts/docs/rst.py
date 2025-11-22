"""RST documentation generation functions for cyclopts apps."""

from typing import TYPE_CHECKING

from cyclopts._markup import extract_text
from cyclopts.docs.base import (
    adjust_filters_for_subcommand,
    extract_description,
    extract_usage,
    generate_anchor,
    get_app_info,
    iterate_commands,
    normalize_command_filters,
    should_include_command,
    should_show_usage,
)
from cyclopts.help.formatters._shared import make_rst_code_block_title, make_rst_section_header

if TYPE_CHECKING:
    from cyclopts.core import App


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

    normalized_commands_filter, normalized_exclude_commands = normalize_command_filters(
        commands_filter, exclude_commands
    )

    for name, subapp in iterate_commands(app, include_hidden):
        if not should_include_command(
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
    code_block_title: bool = False,
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

    app_name, full_command, base_title = get_app_info(app, command_chain)
    # Title logic: match markdown behavior for consistency
    # - Hierarchical mode: show just command name (last part of chain)
    # - Flattened mode: show full command path
    # - Root: use base title
    if command_chain and not flatten_commands:
        # Hierarchical: show just the command name (last part of chain)
        title = command_chain[-1]
    elif command_chain:
        # Flattened: show full command path
        title = full_command
    else:
        # Root app: use base title
        title = base_title

    # Always generate RST anchor/label with improved namespacing
    # RST uses a "cyclopts-" prefix for namespacing
    anchor_parts = ["cyclopts"]
    if command_chain:
        anchor_parts.extend(command_chain)
    else:
        anchor_parts.append(app_name)
    # Use shared anchor generation logic, then add RST-specific slash replacement
    anchor_name = generate_anchor(" ".join(anchor_parts)).replace("/", "-")
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
        if code_block_title:
            header_lines = make_rst_code_block_title(title)
        else:
            header_lines = make_rst_section_header(title, effective_heading_level)
        lines.extend(header_lines)
        lines.append("")

    help_format = app.app_stack.resolve("help_format", fallback="restructuredtext")
    description = extract_description(app, help_format)
    if description:
        # Extract plain text from description
        # Preserve markup when help_format matches output format (RST)
        preserve = help_format in ("restructuredtext", "rst")
        desc_text = extract_text(description, None, preserve_markup=preserve)
        if desc_text:
            lines.append(desc_text.strip())
            lines.append("")

    # Add usage section if appropriate
    if should_show_usage(app):
        # Generate usage line - only if we're documenting a specific command
        if not (no_root_title and not command_chain):
            # Extract usage from app
            usage = extract_usage(app)
            usage_text = None
            if usage:
                if isinstance(usage, str):
                    usage_text = usage
                else:
                    usage_text = extract_text(usage, None, preserve_markup=False)

                # Format usage with command chain if this is a subcommand
                if command_chain:
                    # Add command chain to usage
                    parts = usage_text.split(None, 1)
                    if len(parts) > 1:
                        usage_text = f"{' '.join(command_chain)} {parts[1]}"
                    else:
                        usage_text = " ".join(command_chain)

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

    # Render panels as-is without categorization
    for group, panel in help_panels_with_groups:
        # Skip hidden panels unless include_hidden is True
        if not include_hidden and group and not group.show:
            continue

        # Skip command panels entirely (not rendered in RST mode)
        if panel.format == "command":
            continue

        # Skip if no_root_title and we're at root
        if no_root_title and not command_chain:
            continue

        # Render parameter panels as-is
        if panel.format == "parameter":
            # Render panel title if present
            if panel.title:
                lines.append(f"**{panel.title}:**")
                lines.append("")

            formatter.reset()
            panel_copy = panel.copy(title="")
            formatter(None, None, panel_copy)
            output = formatter.get_output().strip()
            if output:
                lines.append(output)
                lines.append("")

    if recursive and app._commands:
        normalized_commands_filter, normalized_exclude_commands = normalize_command_filters(
            commands_filter, exclude_commands
        )
        parent_path = []

        for name, subapp in iterate_commands(app, include_hidden):
            if not should_include_command(
                name, parent_path, normalized_commands_filter, normalized_exclude_commands, subapp
            ):
                continue

            lines.append("")

            subcommand_chain = command_chain + [name] if command_chain else [app_name, name]
            if flatten_commands:
                next_heading_level = heading_level
            elif no_root_title and not command_chain:
                next_heading_level = heading_level - 1
            else:
                next_heading_level = heading_level

            sub_commands_filter, sub_exclude_commands = adjust_filters_for_subcommand(
                name, normalized_commands_filter, normalized_exclude_commands
            )

            # Push subapp onto app_stack so should_show_usage() can detect subcommand context
            with subapp.app_stack([subapp]):
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
                    code_block_title=code_block_title,
                )
            lines.append(subdocs)

    return "\n".join(lines)
