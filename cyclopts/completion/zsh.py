"""Zsh completion script generator.

This module generates static zsh completion scripts for Cyclopts applications by
leveraging the existing help system infrastructure. The completion generator:

1. **Extracts** completion data by calling `app._assemble_help_panels()` recursively
   for each command path, reusing the help system's parameter and command extraction.

2. **Transforms** the help panel data (HelpEntry objects) into zsh completion primitives:
   - Commands → _describe -t commands 'command' list
   - Parameters → _arguments specs with descriptions
   - Literal/Enum choices → completion value lists
   - Path types → _files action
   - Negative flags → automatic --no-* variants

3. **Generates** a static zsh completion script using the compsys framework with no
   runtime Python dependency.

Key Design Decisions
--------------------
- **Static Generation**: No runtime Python overhead; fast completion response
- **Help System Reuse**: Avoids reimplementing parameter/choice extraction
- **Security First**: Comprehensive escaping prevents shell injection
- **Recursive Structure**: Naturally handles nested subcommands via state machine

Example
-------
>>> from cyclopts import App
>>> app = App(name="myapp")
>>> @app.default
... def main(verbose: bool = False):
...     '''My application.'''
...     pass
>>> script = generate_completion_script(app, "myapp")
>>> Path("_myapp").write_text(script)  # Install to fpath directory
"""

import re
from textwrap import dedent
from textwrap import indent as textwrap_indent
from typing import TYPE_CHECKING

from cyclopts.completion._base import (
    CompletionAction,
    CompletionData,
    clean_description_text,
    extract_completion_data,
    get_completion_action,
    is_flag_argument,
)
from cyclopts.help.help import docstring_parse

if TYPE_CHECKING:
    from cyclopts import App
    from cyclopts.argument import Argument, ArgumentCollection


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

    completion_data = extract_completion_data(app)

    lines = [
        f"#compdef {prog_name}",
        "",
        f"_{prog_name}() {{",
        "  local line state",
        "",
    ]

    lines.extend(_generate_completion_for_path(completion_data, (), prog_name=prog_name))

    lines.extend(
        [
            "}",
            "",
            f'_{prog_name} "$@"',
        ]
    )

    return "\n".join(lines) + "\n"


def _generate_run_command_completion(
    arguments: "ArgumentCollection",
    indent_str: str,
    prog_name: str,
) -> list[str]:
    """Generate special dynamic completion for the 'run' command.

    The run command loads a Python script dynamically, so we need to call back
    into Python at completion time to discover available commands and options.

    Parameters
    ----------
    arguments : ArgumentCollection
        Arguments for the run command.
    indent_str : str
        Indentation string.
    prog_name : str
        Program name for the callback.

    Returns
    -------
    list[str]
        Lines of zsh completion code.
    """
    template = dedent(f"""\
        local script_path
        local -a completions
        local -a remaining_words

        # If completing first argument (the script path), suggest files
        if [[ $CURRENT -eq 2 ]]; then
          _files
          return
        fi

        # Get absolute path to the script file
        script_path=${{words[2]}}
        script_path=${{script_path:a}}
        if [[ -f $script_path ]]; then
          remaining_words=(${{words[3,-1]}})
          local result
          local cmd

          if command -v {prog_name} &>/dev/null; then
            cmd="{prog_name}"
          else
            return
          fi
          # Call back into cyclopts to get dynamic completions from the script
          result=$($cmd _complete run "$script_path" "${{remaining_words[@]}}" 2>/dev/null)
          if [[ -n $result ]]; then
            # Parse and display completion results
            completions=()
            while IFS= read -r line; do
              completions+=($line)
            done <<< $result
            _describe 'command' completions
          fi
        fi""")

    indented = textwrap_indent(template, indent_str)
    return [line.rstrip() for line in indented.split("\n")]


def _generate_completion_for_path(
    completion_data: dict[tuple[str, ...], CompletionData],
    command_path: tuple[str, ...],
    indent: int = 2,
    prog_name: str = "cyclopts",
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
    prog_name : str
        Program name for dynamic completion callback.

    Returns
    -------
    list[str]
        Lines of zsh code.
    """
    data = completion_data[command_path]
    commands = data.commands
    arguments = data.arguments
    indent_str = " " * indent
    lines = []

    if command_path == ("run",) and prog_name == "cyclopts":
        lines.extend(_generate_run_command_completion(arguments, indent_str, prog_name))
        return lines

    args_specs = []

    # Separate positional from keyword arguments
    positional_args = [arg for arg in arguments if arg.is_positional_only() and arg.show]
    keyword_args = [arg for arg in arguments if not arg.is_positional_only() and arg.show]

    # Sort positionals by index (should never be None for positional-only args)
    positional_args.sort(key=lambda a: a.index or 0)

    # Generate keyword argument specs
    for argument in keyword_args:
        specs = _generate_keyword_specs(argument)
        args_specs.extend(specs)

    # Check for flag commands (commands that look like options)
    for cmd_app in commands:
        if any(name.startswith("-") for name in cmd_app.name):
            specs = _generate_keyword_specs_for_command(cmd_app)
            args_specs.extend(specs)

    has_non_flag_commands = any(not cmd_name.startswith("-") for cmd in commands for cmd_name in cmd.name)

    # Generate positional argument specs
    # Only add positionals if there are no subcommands (they conflict in zsh)
    if positional_args and not has_non_flag_commands:
        for argument in positional_args:
            spec = _generate_positional_spec(argument)
            args_specs.append(spec)

    if has_non_flag_commands:
        args_specs.append("'1: :->cmds'")
        args_specs.append("'*::arg:->args'")

    if args_specs:
        c_flag = "-C " if has_non_flag_commands else ""
        lines.append(f"{indent_str}_arguments {c_flag}\\")
        for spec in args_specs[:-1]:
            lines.append(f"{indent_str}  {spec} \\")
        lines.append(f"{indent_str}  {args_specs[-1]}")
        lines.append("")

    if has_non_flag_commands:
        lines.append(f"{indent_str}case $state in")
        lines.append(f"{indent_str}  cmds)")

        cmd_list = []
        for cmd_app in commands:
            for cmd_name in cmd_app.name:
                if not cmd_name.startswith("-"):
                    desc = _safe_get_description_from_app(cmd_app)
                    cmd_list.append(f"'{cmd_name}:{desc}'")

        lines.append(f"{indent_str}    local -a commands")
        lines.append(f"{indent_str}    commands=(")
        for cmd in cmd_list:
            lines.append(f"{indent_str}      {cmd}")
        lines.append(f"{indent_str}    )")
        lines.append(f"{indent_str}    _describe -t commands 'command' commands")
        lines.append(f"{indent_str}    ;;")

        lines.append(f"{indent_str}  args)")
        lines.append(f"{indent_str}    case $words[1] in")

        for cmd_app in commands:
            for cmd_name in cmd_app.name:
                if cmd_name.startswith("-"):
                    continue

                sub_path = command_path + (cmd_name,)
                if sub_path in completion_data:
                    lines.append(f"{indent_str}      {cmd_name})")
                    sub_lines = _generate_completion_for_path(completion_data, sub_path, indent + 8, prog_name)
                    lines.extend(sub_lines)
                    lines.append(f"{indent_str}        ;;")

        lines.append(f"{indent_str}    esac")
        lines.append(f"{indent_str}    ;;")
        lines.append(f"{indent_str}esac")

    return lines


def _escape_completion_choice(choice: str) -> str:
    """Escape special characters in a completion choice value for zsh.

    Parameters
    ----------
    choice : str
        Raw choice value.

    Returns
    -------
    str
        Escaped choice value safe for zsh completion.
    """
    choice = re.sub(r"[\x00-\x1f\x7f]", "", choice)
    choice = choice.replace("\\", "\\\\")
    choice = choice.replace("'", r"'\''")
    choice = choice.replace("`", "\\`")
    choice = choice.replace("$", "\\$")
    choice = choice.replace('"', '\\"')
    choice = choice.replace(" ", "\\ ")
    choice = choice.replace("(", "\\(")
    choice = choice.replace(")", "\\)")
    choice = choice.replace("[", "\\[")
    choice = choice.replace("]", "\\]")
    choice = choice.replace(";", "\\;")
    choice = choice.replace("|", "\\|")
    choice = choice.replace("&", "\\&")
    choice = choice.replace(":", "\\:")
    return choice


def _escape_zsh_description(text: str) -> str:
    """Escape special characters in description text for zsh.

    Parameters
    ----------
    text : str
        Cleaned description text.

    Returns
    -------
    str
        Escaped description safe for zsh completion.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("$", "\\$")
    text = text.replace('"', '\\"')
    text = text.replace("'", r"'\''")
    text = text.replace(":", r"\:")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    return text


def _generate_keyword_specs(argument: "Argument") -> list[str]:
    """Generate zsh _arguments specs for a keyword argument.

    Parameters
    ----------
    argument : Argument
        Argument object from ArgumentCollection.

    Returns
    -------
    list[str]
        List of zsh argument specs.
    """
    specs = []
    desc = _get_description_from_argument(argument)

    flag = is_flag_argument(argument)

    # Determine completion action
    action = ""
    choices = argument.get_choices()
    if choices:
        escaped_choices = [_escape_completion_choice(c) for c in choices]
        choices_str = " ".join(escaped_choices)
        action = f"({choices_str})"
        flag = False
    else:
        action = _map_completion_action_to_zsh(get_completion_action(argument.hint))

    # Generate specs for each name
    for name in argument.names:
        if not name.startswith("-"):
            continue
        if flag and not action:
            spec = f"'{name}[{desc}]'"
        elif action:
            spec = f"'{name}[{desc}]:{name.lstrip('-')}:{action}'"
        else:
            spec = f"'{name}[{desc}]:{name.lstrip('-')}'"
        specs.append(spec)

    return specs


def _generate_positional_spec(argument: "Argument") -> str:
    """Generate zsh _arguments spec for a positional argument.

    Parameters
    ----------
    argument : Argument
        Positional argument object.

    Returns
    -------
    str
        Zsh positional argument spec.
    """
    desc = _get_description_from_argument(argument)
    action = _map_completion_action_to_zsh(get_completion_action(argument.hint))

    if argument.is_var_positional():
        # Variadic positional (*args)
        return f"'*:{desc}:{action}'" if action else f"'*:{desc}'"

    # Regular positional - zsh uses 1-based indexing
    if argument.index is None:
        raise ValueError(f"Positional-only argument {argument.names} missing index")
    pos = argument.index + 1
    return f"'{pos}:{desc}:{action}'" if action else f"'{pos}:{desc}'"


def _generate_keyword_specs_for_command(cmd_app: "App") -> list[str]:
    """Generate zsh _arguments specs for a command that looks like a flag.

    Parameters
    ----------
    cmd_app : App
        Command app with flag-like names.

    Returns
    -------
    list[str]
        List of zsh argument specs.
    """
    specs = []
    desc = _safe_get_description_from_app(cmd_app)

    for name in cmd_app.name:
        if name.startswith("-"):
            spec = f"'{name}[{desc}]'"
            specs.append(spec)

    return specs


def _map_completion_action_to_zsh(action: CompletionAction) -> str:
    """Map shell-agnostic completion action to zsh-specific completion command.

    Parameters
    ----------
    action : CompletionAction
        Shell-agnostic completion action.

    Returns
    -------
    str
        Zsh completion command (e.g., "_files", "_directories", or "").
    """
    if action == CompletionAction.FILES:
        return "_files"
    elif action == CompletionAction.DIRECTORIES:
        return "_directories"
    return ""


def _get_description_from_argument(argument: "Argument") -> str:
    """Extract plain text description from Argument, escaping zsh special chars.

    Parameters
    ----------
    argument : Argument
        Argument object with parameter help text.

    Returns
    -------
    str
        Escaped plain text description (truncated to 80 chars).
    """
    text = clean_description_text(argument.parameter.help or "")
    return _escape_zsh_description(text)


def _safe_get_description_from_app(cmd_app: "App") -> str:
    """Extract plain text description from App, escaping zsh special chars.

    Parameters
    ----------
    cmd_app : App
        Command app with help text.

    Returns
    -------
    str
        Escaped plain text description (truncated to 80 chars).
    """
    if not cmd_app.help:
        return ""

    try:
        parsed = docstring_parse(cmd_app.help, "plaintext")
        text = parsed.short_description or ""
    except Exception:
        text = str(cmd_app.help)

    text = clean_description_text(text)
    return _escape_zsh_description(text)
