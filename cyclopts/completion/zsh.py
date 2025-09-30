"""Zsh completion script generator."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args

if TYPE_CHECKING:
    from cyclopts import App
    from cyclopts.help import HelpEntry


@dataclass
class CompletionData:
    """Completion data for a command path."""

    commands: list["HelpEntry"]
    parameters: list["HelpEntry"]


def generate_completion_script(app: "App", prog_name: str) -> str:
    """Generate zsh compsys completion script.

    Generates static completion script with no runtime Python dependency.
    Supports:
    - Commands and subcommands (including meta apps)
    - Options with help text descriptions
    - Literal/Enum value completion (choices pre-extracted)
    - Negative flags (--verbose/--no-verbose)
    - Path/file completion for Path types

    Parameters
    ----------
    app : App
        The Cyclopts application to generate completion for.
    prog_name : str
        Program name for completion function naming.
        Must be a valid shell identifier (alphanumeric and underscore).

    Returns
    -------
    str
        Complete zsh completion script ready to source.

    Examples
    --------
    >>> from cyclopts import App
    >>> app = App(name="myapp")
    >>> script = generate_completion_script(app, "myapp")
    >>> Path("_myapp").write_text(script)

    Raises
    ------
    ValueError
        If prog_name contains invalid characters.
    """
    if not prog_name or not re.match(r"^[a-zA-Z0-9_-]+$", prog_name):
        raise ValueError(f"Invalid prog_name: {prog_name!r}. Must be alphanumeric with hyphens/underscores.")

    completion_data: dict[tuple[str, ...], CompletionData] = {}

    def extract_completion_data(command_path: tuple[str, ...] = ()):
        """Recursively extract completion data for command and subcommands."""
        help_panels = app._assemble_help_panels(tokens=list(command_path), help_format="plaintext")

        commands = []
        parameters = []

        for _, panel in help_panels:
            if panel.format == "command":
                commands.extend(panel.entries)
            elif panel.format == "parameter":
                parameters.extend(panel.entries)

        completion_data[command_path] = CompletionData(commands=commands, parameters=parameters)

        for cmd_entry in commands:
            for cmd_name in cmd_entry.names:
                if not cmd_name.startswith("-"):
                    extract_completion_data(command_path + (cmd_name,))

    extract_completion_data()

    lines = [
        f"#compdef {prog_name}",
        "",
        f"_{prog_name}() {{",
        "  local line state",
        "",
    ]

    lines.extend(_generate_completion_for_path(completion_data, ()))

    lines.extend(
        [
            "}",
            "",
            f'_{prog_name} "$@"',
        ]
    )

    return "\n".join(lines)


def _generate_completion_for_path(
    completion_data: dict[tuple[str, ...], CompletionData],
    command_path: tuple[str, ...],
    indent: int = 2,
) -> list[str]:
    """Generate zsh completion code for a specific command path.

    Parameters
    ----------
    completion_data : dict
        All extracted completion data.
    command_path : tuple[str, ...]
        Current command path.
    indent : int
        Indentation level (spaces).

    Returns
    -------
    list[str]
        Lines of zsh code.
    """
    data = completion_data[command_path]
    commands = data.commands
    parameters = data.parameters
    indent_str = " " * indent
    lines = []

    args_specs = []

    for param_entry in parameters:
        specs = _generate_parameter_specs(param_entry)
        args_specs.extend(specs)

    for cmd_entry in commands:
        if any(name.startswith("-") for name in cmd_entry.names):
            specs = _generate_parameter_specs(cmd_entry)
            args_specs.extend(specs)

    has_non_flag_commands = any(not cmd_name.startswith("-") for cmd in commands for cmd_name in cmd.names)

    if has_non_flag_commands:
        args_specs.append("'1: :->cmds'")
        args_specs.append("'*::arg:->args'")

    if args_specs:
        lines.append(f"{indent_str}_arguments -C \\")
        for spec in args_specs[:-1]:
            lines.append(f"{indent_str}  {spec} \\")
        lines.append(f"{indent_str}  {args_specs[-1]}")
        lines.append("")

    if has_non_flag_commands:
        lines.append(f"{indent_str}case $state in")
        lines.append(f"{indent_str}  cmds)")

        cmd_list = []
        for cmd_entry in commands:
            for cmd_name in cmd_entry.names:
                if not cmd_name.startswith("-"):
                    desc = _safe_get_description(cmd_entry)
                    cmd_list.append(f"'{cmd_name}:{desc}'")

        lines.append(f"{indent_str}    local -a commands")
        lines.append(f"{indent_str}    commands=(")
        for cmd in cmd_list:
            lines.append(f"{indent_str}      {cmd}")
        lines.append(f"{indent_str}    )")
        lines.append(f"{indent_str}    _describe 'command' commands")
        lines.append(f"{indent_str}    ;;")

        lines.append(f"{indent_str}  args)")
        depth = len(command_path) + 1
        lines.append(f"{indent_str}    case $line[{depth}] in")

        for cmd_entry in commands:
            for cmd_name in cmd_entry.names:
                if cmd_name.startswith("-"):
                    continue

                sub_path = command_path + (cmd_name,)
                if sub_path in completion_data:
                    lines.append(f"{indent_str}      {cmd_name})")
                    sub_lines = _generate_completion_for_path(completion_data, sub_path, indent + 8)
                    lines.extend(sub_lines)
                    lines.append(f"{indent_str}        ;;")

        lines.append(f"{indent_str}    esac")
        lines.append(f"{indent_str}    ;;")
        lines.append(f"{indent_str}esac")

    return lines


def _generate_parameter_specs(entry: "HelpEntry") -> list[str]:
    """Generate zsh _arguments specs for a parameter.

    Parameters
    ----------
    entry : HelpEntry
        Parameter entry from help panel.

    Returns
    -------
    list[str]
        List of zsh argument specs.
    """
    specs = []
    desc = _safe_get_description(entry)

    action = ""
    if entry.choices:
        choices_str = " ".join(entry.choices)
        action = f"({choices_str})"
    elif entry.type:
        action = _get_completion_action_from_type(entry.type)

    for name in entry.names:
        if not name.startswith("-"):
            continue
        if action:
            spec = f"'{name}[{desc}]:{name.lstrip('-')}:{action}'"
        else:
            spec = f"'{name}[{desc}]'"
        specs.append(spec)

    for short in entry.shorts:
        if action:
            spec = f"'{short}[{desc}]:{short.lstrip('-')}:{action}'"
        else:
            spec = f"'{short}[{desc}]'"
        specs.append(spec)

    return specs


def _get_completion_action_from_type(type_hint: Any) -> str:
    """Get zsh completion action from type hint.

    Handles Union and Optional types by extracting the non-None type.

    Parameters
    ----------
    type_hint : Any
        Type annotation.

    Returns
    -------
    str
        Zsh completion action (e.g., "_files", "_directories", or "").
    """
    from typing import get_origin

    from cyclopts.annotations import is_union
    from cyclopts.utils import is_class_and_subclass

    if is_union(type_hint):
        for arg in get_args(type_hint):
            if arg is not type(None):
                action = _get_completion_action_from_type(arg)
                if action:
                    return action
        return ""

    target_type = get_origin(type_hint) or type_hint

    if target_type is Path or is_class_and_subclass(target_type, Path):
        return "_files"

    return ""


def _safe_get_description(entry: "HelpEntry") -> str:
    """Extract plain text description, escaping zsh special chars.

    Escapes characters that could cause shell injection or break completion.

    Parameters
    ----------
    entry : HelpEntry
        Help entry with description.

    Returns
    -------
    str
        Escaped plain text description (truncated to 80 chars).
    """
    if entry.description is None:
        return ""

    if hasattr(entry.description, "primary_renderable"):
        text = entry.description.primary_renderable.plain
    elif hasattr(entry.description, "plain"):
        text = entry.description.plain
    else:
        text = str(entry.description)

    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("$", "\\$")
    text = text.replace('"', '\\"')
    text = text.replace("'", r"'\''")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")

    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 80:
        text = text[:77] + "..."

    return text
