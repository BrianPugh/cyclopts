"""Zsh completion script generator.

Generates static zsh completion scripts using the compsys framework.
No runtime Python dependency.
"""

import re
from textwrap import dedent
from textwrap import indent as textwrap_indent
from typing import TYPE_CHECKING

from cyclopts.annotations import is_iterable_type
from cyclopts.completion._base import (
    CompletionAction,
    CompletionData,
    clean_choice_text,
    escape_for_shell_pattern,
    extract_completion_data,
    get_completion_action,
    strip_markup,
)
from cyclopts.help.help import docstring_parse

if TYPE_CHECKING:
    from cyclopts import App
    from cyclopts.argument import Argument, ArgumentCollection
    from cyclopts.command_spec import CommandSpec


def generate_completion_script(app: "App", prog_name: str) -> str:
    """Generate zsh completion script.

    Parameters
    ----------
    app : App
        The Cyclopts application to generate completion for.
    prog_name : str
        Program name (alphanumeric with hyphens/underscores).

    Returns
    -------
    str
        Complete zsh completion script.

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

    lines.extend(
        _generate_completion_for_path(
            completion_data,
            (),
            prog_name=prog_name,
            help_flags=tuple(app.help_flags) if app.help_flags else (),
            version_flags=tuple(app.version_flags) if app.version_flags else (),
        )
    )

    lines.extend(
        [
            "}",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def _generate_run_command_completion(
    arguments: "ArgumentCollection",
    indent_str: str,
    prog_name: str,
) -> list[str]:
    """Generate dynamic completion for the 'run' command.

    Parameters
    ----------
    arguments : ArgumentCollection
        Arguments for run command.
    indent_str : str
        Indentation string.
    prog_name : str
        Program name.

    Returns
    -------
    list[str]
        Zsh completion code lines.
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


def _generate_nested_positional_specs(
    positional_args: list["Argument"],
    help_format: str,
) -> list[str]:
    """Generate positional argument specs for nested command context.

    In nested contexts (after *::arg:->args), word indexing is shifted:
    - words[1] = subcommand name
    - words[2] = first positional argument
    - words[3] = second positional argument, etc.

    Parameters
    ----------
    positional_args : list[Argument]
        Positional arguments to generate specs for.
    help_format : str
        Help text format.

    Returns
    -------
    list[str]
        List of zsh positional argument specs.
    """
    specs = []

    # Check if we have variadic positionals (including collection types like list[X])
    variadic_args = [arg for arg in positional_args if arg.is_var_positional() or is_iterable_type(arg.hint)]
    non_variadic_args = [
        arg for arg in positional_args if not arg.is_var_positional() and not is_iterable_type(arg.hint)
    ]

    def _build(arg, position: str) -> str:
        choices = arg.get_choices(force=True)
        if choices:
            escaped_choices = [_escape_choice_for_dq_spec(clean_choice_text(c)) for c in choices]
            choices_str = " ".join(escaped_choices)
            action = f"({choices_str})"
            desc = _escape_zsh_description_dq(_description_text(arg, help_format))
            quote = '"'
        else:
            action = _map_completion_action_to_zsh(get_completion_action(arg.hint))
            desc = _get_description_from_argument(arg, help_format)
            quote = "'"
        return f"{quote}{position}:{desc}:{action}{quote}" if action else f"{quote}{position}:{desc}{quote}"

    # Generate specs for non-variadic positionals
    for arg in non_variadic_args:
        # Position in nested context: After *::arg:->args, $words[1] is the subcommand
        # So positionals start at position 1 (not 2)
        # Use 1-based indexing: first positional is '1:', second is '2:', etc.
        pos = 1 + (arg.index or 0)
        specs.append(_build(arg, str(pos)))

    # Emit at most one rest-arg (``*:``) spec. zsh's ``_arguments`` errors
    # with "doubled rest argument definition" if more than one is present.
    # When a function has multiple iterable positional-or-keyword params
    # (e.g. several ``list[X]`` defaults), only the first can realistically
    # be filled positionally — the others remain available via their
    # ``--name`` keyword forms emitted elsewhere.
    chosen = next((a for a in variadic_args if a.is_var_positional()), None)
    if chosen is None and variadic_args:
        chosen = variadic_args[0]
    if chosen is not None:
        specs.append(_build(chosen, "*"))

    return specs


def _generate_describe_completion(
    argument: "Argument",
    help_format: str,
    indent_str: str,
) -> list[str]:
    """Generate _describe-based completion for a single positional argument.

    Parameters
    ----------
    argument : Argument
        Argument to generate completion for.
    help_format : str
        Help text format.
    indent_str : str
        Indentation string.

    Returns
    -------
    list[str]
        Zsh completion code lines.
    """
    lines = []
    desc = _get_description_from_argument(argument, help_format)

    # Check for choices (Literal/Enum types)
    choices = argument.get_choices(force=True)
    if choices:
        # Generate choices array with descriptions
        escaped_choices = [_escape_completion_choice(clean_choice_text(c)) for c in choices]
        lines.append(f"{indent_str}local -a choices")
        lines.append(f"{indent_str}choices=(")
        for choice in escaped_choices:
            lines.append(f"{indent_str}  '{choice}:{desc}'")
        lines.append(f"{indent_str})")
        lines.append(f"{indent_str}_describe 'argument' choices")
    else:
        # Use completion action (files, directories, or nothing)
        action = get_completion_action(argument.hint)
        if action == CompletionAction.FILES:
            lines.append(f"{indent_str}_files")
        elif action == CompletionAction.DIRECTORIES:
            lines.append(f"{indent_str}_directories")
        # For other types, provide no completion

    return lines


def _generate_completion_for_path(
    completion_data: dict[tuple[str, ...], CompletionData],
    command_path: tuple[str, ...],
    indent: int = 2,
    prog_name: str = "cyclopts",
    help_flags: tuple[str, ...] = (),
    version_flags: tuple[str, ...] = (),
) -> list[str]:
    """Generate completion code for a specific command path.

    Parameters
    ----------
    completion_data : dict
        Extracted completion data.
    command_path : tuple[str, ...]
        Command path.
    indent : int
        Indentation level.
    prog_name : str
        Program name.
    help_flags : tuple[str, ...]
        Help flags.
    version_flags : tuple[str, ...]
        Version flags.

    Returns
    -------
    list[str]
        Zsh code lines.
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
    positional_specs = []

    # Separate positional from keyword arguments
    # Include all arguments with an index (both positional-only and positional-or-keyword)
    positional_args = [arg for arg in arguments if arg.index is not None and arg.show]
    keyword_args = [arg for arg in arguments if not arg.is_positional_only() and arg.show]

    # Sort positionals by index (should never be None for positional-only args)
    positional_args.sort(key=lambda a: a.index or 0)

    # Generate keyword argument specs
    for argument in keyword_args:
        specs = _generate_keyword_specs(argument, data.help_format)
        args_specs.extend(specs)

    # Check for flag commands (commands that look like options)
    flag_command_names = set()
    for registered_command in commands:
        if any(name.startswith("-") for name in registered_command.names):
            specs = _generate_keyword_specs_for_command(
                registered_command.names, registered_command.app, data.help_format
            )
            args_specs.extend(specs)
            flag_command_names.update(registered_command.names)

    # Add help and version flags to all command paths (if not already added as flag commands)
    for flag in help_flags:
        if flag.startswith("-") and flag not in flag_command_names:
            spec = f"'{flag}[Display this message and exit.]'"
            args_specs.append(spec)

    for flag in version_flags:
        if flag.startswith("-") and flag not in flag_command_names:
            spec = f"'{flag}[Display application version.]'"
            args_specs.append(spec)

    has_non_flag_commands = any(
        not cmd_name.startswith("-") for registered_command in commands for cmd_name in registered_command.names
    )

    # Generate positional argument specs
    # Only add positionals if there are no subcommands (they conflict in zsh)
    if positional_args and not has_non_flag_commands:
        if command_path:
            # Nested context: use shifted positional indexing (words[1] is subcommand)
            positional_specs = _generate_nested_positional_specs(positional_args, data.help_format)
        else:
            # Root context: standard _arguments works fine. As in the
            # nested helper, only one rest-arg (``*:``) spec is allowed —
            # collapse multiple iterable positionals to the first one
            # (var-positional preferred). The other iterables remain
            # available via their ``--name`` keyword specs.
            seen_rest = False
            iterable_args = [a for a in positional_args if a.is_var_positional() or is_iterable_type(a.hint)]
            chosen_rest = next((a for a in iterable_args if a.is_var_positional()), None)
            if chosen_rest is None and iterable_args:
                chosen_rest = iterable_args[0]
            for argument in positional_args:
                is_rest = argument.is_var_positional() or is_iterable_type(argument.hint)
                if is_rest:
                    if argument is not chosen_rest or seen_rest:
                        continue
                    seen_rest = True
                spec = _generate_positional_spec(argument, data.help_format)
                positional_specs.append(spec)

        # Add positionals BEFORE options to prioritize them in completion
        args_specs = positional_specs + args_specs

    if has_non_flag_commands:
        args_specs.append("'1: :->cmds'")
        args_specs.append("'*::arg:->args'")

    # Eq-form pre-pass: zsh's ``_arguments`` only handles ``--opt=value``
    # value-completion when the spec name carries an ``=`` suffix, which
    # also forces ``=`` insertion on name TAB. We want the natural
    # ``--opt `` (trailing space) name TAB *and* ``--opt=value<TAB>``
    # value completion. Achieved with a pre-pass that intercepts
    # ``--opt=...`` patterns before ``_arguments`` runs and dispatches to
    # the same value action with the ``--opt=`` prefix consumed via
    # ``compset -P``. ``Parameter(requires_equals=True)`` already emits the
    # eq spec directly, so those options are skipped here.
    eq_prepass = _generate_eq_form_prepass(keyword_args, indent_str)
    lines.extend(eq_prepass)

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
        for registered_command in commands:
            for cmd_name in registered_command.names:
                if not cmd_name.startswith("-"):
                    desc = _safe_get_description_from_app(registered_command.app, data.help_format)
                    escaped_cmd_name = _escape_completion_choice(cmd_name)
                    cmd_list.append(f"'{escaped_cmd_name}:{desc}'")

        lines.append(f"{indent_str}    local -a commands")
        lines.append(f"{indent_str}    commands=(")
        for cmd in cmd_list:
            lines.append(f"{indent_str}      {cmd}")
        lines.append(f"{indent_str}    )")
        lines.append(f"{indent_str}    _describe -t commands 'command' commands")
        lines.append(f"{indent_str}    ;;")

        lines.append(f"{indent_str}  args)")
        lines.append(f"{indent_str}    case $words[1] in")

        for registered_command in commands:
            for cmd_name in registered_command.names:
                if cmd_name.startswith("-"):
                    continue

                sub_path = command_path + (cmd_name,)
                if sub_path in completion_data:
                    escaped_case_name = _escape_command_name_for_case(cmd_name)
                    lines.append(f"{indent_str}      {escaped_case_name})")
                    sub_lines = _generate_completion_for_path(
                        completion_data, sub_path, indent + 8, prog_name, help_flags, version_flags
                    )
                    lines.extend(sub_lines)
                    lines.append(f"{indent_str}        ;;")

        lines.append(f"{indent_str}    esac")
        lines.append(f"{indent_str}    ;;")
        lines.append(f"{indent_str}esac")

    return lines


def _shell_single_quote(s: str) -> str:
    r"""Wrap ``s`` in POSIX-safe single quotes for embedding as a shell argument.

    The only character that can't appear inside a single-quoted shell string
    is ``'`` itself, which is handled with the ``'\''`` end-and-restart
    trick. Everything else (spaces, parens, ``$``, backticks, etc.) is
    literal — no backslash-escaping is needed, and adding any would just
    surface as visible backslashes in the resulting argument.
    """
    return "'" + s.replace("'", "'\\''") + "'"


def _escape_completion_choice(choice: str) -> str:
    """Escape a choice value for embedding in a single-quoted shell context.

    Used for ``_describe`` array elements (``'value:desc'``) where the only
    parser the value passes through is the array-element parser, not the
    ``_arguments`` choice-list eval. Choice should already be cleaned via
    ``clean_choice_text()``.

    Parameters
    ----------
    choice : str
        Cleaned choice value.

    Returns
    -------
    str
        Escaped choice value safe for zsh completion.
    """
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


def _escape_choice_for_dq_spec(value: str) -> str:
    r"""Escape a choice value for ``_arguments``' parenthesized choice list.

    The value passes through *two* parsers:

    1. zsh's outer double-quoted-string parser, which interprets ``\``,
       ``"``, ``$`` and backtick.
    2. ``_arguments``' choice-list parser, which whitespace-tokenizes and
       reads ``\X`` as a literal X.

    A literal ``'`` cannot be embedded in a single-quoted spec string
    (``'\''`` ends/restarts the quoting and the parser then sees an
    unbalanced ``'``), so choice-bearing specs are emitted with a *double*-
    quoted outer string and routed through this helper.
    """
    # Layer 1: choice-list parser escapes. The parser eval-style processes
    # each token, so ``$`` and backtick must be escaped here even though
    # they're DQ-specials too — DQ stripping happens *first* and would
    # otherwise leave them bare for the parser. Backslash first to avoid
    # double-escaping the slashes the loop introduces.
    s = value.replace("\\", "\\\\")
    for ch in " '\"()[]:;|&$`":
        s = s.replace(ch, "\\" + ch)
    # Layer 2: outer double-quote escapes. Re-escape backslashes (preserves
    # all the layer-1 ones) and re-escape DQ-specials so each one survives
    # to the choice-list parser as ``\X``.
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("$", "\\$")
    s = s.replace("`", "\\`")
    return s


def _escape_zsh_description_dq(text: str) -> str:
    r"""Escape a description for embedding in a double-quoted spec string.

    Same as ``_escape_zsh_description`` but skips the ``'`` -> ``'\\''``
    substitution: ``'`` is literal in a double-quoted context.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("$", "\\$")
    text = text.replace('"', '\\"')
    text = text.replace(":", r"\:")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    return text


def _escape_command_name_for_case(name: str) -> str:
    """Escape special characters in command name for zsh case patterns.

    In zsh case patterns, glob characters need to be escaped to match literally.
    Colons also need escaping because zsh's completion system may treat them
    specially when populating the $words array after _describe completion.

    Parameters
    ----------
    name : str
        Command name.

    Returns
    -------
    str
        Escaped command name safe for zsh case patterns.
    """
    # zsh case patterns have more special chars than bash: includes ()|
    # Colons (:) also need escaping for completion $words matching (issue #715)
    return escape_for_shell_pattern(name, chars="*?[]()|:")


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


def _generate_eq_form_prepass(keyword_args: list, indent_str: str) -> list[str]:
    """Emit a ``--opt=value`` pattern dispatcher to run before ``_arguments``.

    For each keyword argument with a long name and a value action, emits a
    ``--opt=*)`` case branch that strips the ``--opt=`` prefix via
    ``compset -P`` and then dispatches to the value action (choice list,
    ``_files``, or ``_directories``). The natural-TAB experience on the
    option *name* is preserved by leaving the underlying ``_arguments``
    spec without an ``=`` suffix; this pre-pass only catches the user
    explicitly typing the eq form.

    Skipped for arguments whose ``Parameter.requires_equals`` is True —
    those already emit the ``=`` spec, which handles eq-form completion
    via ``_arguments``.

    Parameters
    ----------
    keyword_args : list
        Keyword argument objects from ArgumentCollection (already filtered
        to ``arg.show``).
    indent_str : str
        Leading indentation.

    Returns
    -------
    list[str]
        Zsh code lines (empty if no eligible options).
    """
    cases: list[tuple[str, str]] = []  # (option_name, completion_action_lines)
    for argument in keyword_args:
        if argument.is_flag() or argument.parameter.requires_equals:
            continue
        long_names = [name for name in (argument.parameter.name or []) if name.startswith("--")]
        if not long_names:
            continue

        choices = argument.get_choices(force=True)
        if choices:
            # ``compadd`` adds its arguments verbatim — no inner parser to
            # interpret backslash escapes — so we use POSIX single-quoting
            # rather than ``_escape_completion_choice`` (which is built for
            # ``_describe``'s inner parser).
            quoted = [_shell_single_quote(clean_choice_text(c)) for c in choices]
            action_line = "compadd -- " + " ".join(quoted)
        else:
            action = get_completion_action(argument.hint)
            zsh_action = _map_completion_action_to_zsh(action)
            if zsh_action == "_files":
                action_line = "_files"
            elif zsh_action == "_directories":
                action_line = "_directories"
            else:
                continue  # Nothing to dispatch to.

        for name in long_names:
            cases.append((name, action_line))

    if not cases:
        return []

    lines = [
        f"{indent_str}case ${{words[CURRENT]}} in",
    ]
    for opt_name, action_line in cases:
        lines.append(f"{indent_str}  {opt_name}=*)")
        lines.append(f"{indent_str}    compset -P '{opt_name}='")
        lines.append(f"{indent_str}    {action_line}")
        lines.append(f"{indent_str}    return")
        lines.append(f"{indent_str}    ;;")
    lines.append(f"{indent_str}esac")
    return lines


def _generate_keyword_specs(argument: "Argument", help_format: str) -> list[str]:
    """Generate zsh _arguments specs for a keyword argument.

    Parameters
    ----------
    argument : Argument
        Argument object from ArgumentCollection.
    help_format : str
        Help text format.

    Returns
    -------
    list[str]
        List of zsh argument specs.
    """
    specs = []
    flag = argument.is_flag()

    # Determine completion action. When choices are present we emit the spec
    # in a *double-quoted* outer string so a literal ``'`` inside a choice
    # can be backslash-escaped (single-quoted specs can't carry a literal
    # ``'`` past the inner ``_arguments`` choice-list eval).
    action = ""
    has_choices = False
    choices = argument.get_choices(force=True)
    if choices:
        has_choices = True
        escaped_choices = [_escape_choice_for_dq_spec(clean_choice_text(c)) for c in choices]
        choices_str = " ".join(escaped_choices)
        action = f"({choices_str})"
        flag = False
    else:
        action = _map_completion_action_to_zsh(get_completion_action(argument.hint))

    desc = (
        _escape_zsh_description_dq(_description_text(argument, help_format))
        if has_choices
        else _get_description_from_argument(argument, help_format)
    )

    quote = '"' if has_choices else "'"

    # Generate specs for positive names (from parameter.name).
    #
    # For options that take a value, prefix the spec with ``*`` so
    # ``_arguments`` allows the option to repeat (matches bash's behavior
    # and is required for collection-typed options like ``list[Path]`` where
    # ``--file a --file b`` is the natural usage). Bool flags stay
    # non-repeating per zsh convention.
    #
    # The ``=`` suffix on the option name is the *only* knob zsh exposes for
    # eq-form support, and it's load-bearing in two ways at once:
    #
    #   1. With ``=``, ``--opt=value`` value-completion works.
    #   2. With ``=``, TAB-completing the option *name* inserts ``--opt=``
    #      (no trailing space). Without ``=``, TAB inserts ``--opt`` plus a
    #      space — which most users prefer.
    #
    # Since most CLIs in the wild lean on the space form and users find a
    # forced ``=`` insertion surprising, the default (``requires_equals=False``)
    # emits the plain spec — accepting the cost that ``--opt=value<TAB>``
    # value-completion silently does nothing in zsh. When the parser is
    # configured to *require* the eq form (``requires_equals=True``), we
    # emit the ``=`` spec so completion mirrors what the parser will
    # accept. Bash is unaffected: its eq-form completion is driven by
    # ``_value_prev`` hopping over the ``=`` token, not by the spec.
    requires_eq = bool(argument.parameter.requires_equals)
    # An option "takes a value" iff it isn't a bool flag — independent of whether
    # zsh has a completion *action* for the value. Collection-typed options like
    # ``list[int]`` have no action (``get_completion_action`` only knows FILES /
    # DIRECTORIES) but still need ``*`` so ``_arguments`` allows repetition.
    takes_value = not flag
    for name in argument.parameter.name:  # pyright: ignore[reportOptionalIterable]
        if not name.startswith("-"):
            continue
        accepts_eq = requires_eq and name.startswith("--") and takes_value
        spec_name = f"{name}=" if accepts_eq else name
        repeat_prefix = "*" if takes_value else ""
        if flag and not action:
            spec = f"{quote}{repeat_prefix}{spec_name}[{desc}]{quote}"
        elif action:
            spec = f"{quote}{repeat_prefix}{spec_name}[{desc}]:{name.lstrip('-')}:{action}{quote}"
        else:
            spec = f"{quote}{repeat_prefix}{spec_name}[{desc}]:{name.lstrip('-')}{quote}"
        specs.append(spec)

    # Generate specs for negative names (always flags, consume no tokens).
    # No choice action, so single-quoted is fine and keeps the description
    # escaping consistent with the other flag specs.
    desc_sq = _get_description_from_argument(argument, help_format)
    for name in argument.negatives:
        if not name.startswith("-"):
            continue
        spec = f"'{name}[{desc_sq}]'"
        specs.append(spec)

    return specs


def _generate_positional_spec(argument: "Argument", help_format: str) -> str:
    """Generate zsh _arguments spec for a positional argument.

    Parameters
    ----------
    argument : Argument
        Positional argument object.
    help_format : str
        Help text format.

    Returns
    -------
    str
        Zsh positional argument spec.
    """
    # Check for choices first (Literal/Enum types). Choice-bearing specs use
    # double-quoted outer to allow embedding a literal ``'`` in a choice.
    choices = argument.get_choices(force=True)
    if choices:
        escaped_choices = [_escape_choice_for_dq_spec(clean_choice_text(c)) for c in choices]
        choices_str = " ".join(escaped_choices)
        action = f"({choices_str})"
        desc = _escape_zsh_description_dq(_description_text(argument, help_format))
        quote = '"'
    else:
        action = _map_completion_action_to_zsh(get_completion_action(argument.hint))
        desc = _get_description_from_argument(argument, help_format)
        quote = "'"

    if argument.is_var_positional() or is_iterable_type(argument.hint):
        # Variadic positional (*args) or collection type (list[X], set[X], etc.)
        return f"{quote}*:{desc}:{action}{quote}" if action else f"{quote}*:{desc}{quote}"

    # Regular positional - zsh uses 1-based indexing
    if argument.index is None:
        raise ValueError(f"Positional-only argument {argument.names} missing index")
    pos = argument.index + 1
    return f"{quote}{pos}:{desc}:{action}{quote}" if action else f"{quote}{pos}:{desc}{quote}"


def _generate_keyword_specs_for_command(
    names: tuple[str, ...], cmd_app: "App | CommandSpec", help_format: str
) -> list[str]:
    """Generate zsh _arguments specs for a command that looks like a flag.

    Parameters
    ----------
    names : tuple[str, ...]
        Registered names for the command.
    cmd_app : App | CommandSpec
        Command app or spec.
    help_format : str
        Help text format.

    Returns
    -------
    list[str]
        List of zsh argument specs.
    """
    specs = []
    desc = _safe_get_description_from_app(cmd_app, help_format)

    for name in names:
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


def _get_description_from_argument(argument: "Argument", help_format: str) -> str:
    """Extract plain text description from Argument, escaping zsh special chars.

    Parameters
    ----------
    argument : Argument
        Argument object with parameter help text.
    help_format : str
        Help text format.

    Returns
    -------
    str
        Escaped plain text description (truncated to 80 chars).
        Falls back to argument name if help text is empty, since zsh _arguments
        requires a non-empty description for positional specs to work correctly.
    """
    return _escape_zsh_description(_description_text(argument, help_format))


def _description_text(argument: "Argument", help_format: str) -> str:
    """Plain-text description for an argument with the empty-help fallback."""
    text = strip_markup(argument.parameter.help or "", format=help_format)
    if not text:
        # Use primary argument name as fallback - zsh _arguments requires non-empty
        # description for positional specs to provide completions
        text = argument.names[0] if argument.names else "argument"
    return text


def _safe_get_description_from_app(cmd_app: "App | CommandSpec", help_format: str) -> str:
    """Extract plain text description from App, escaping zsh special chars.

    Parameters
    ----------
    cmd_app : App | CommandSpec
        Command app or spec with help text.
    help_format : str
        Help text format.

    Returns
    -------
    str
        Escaped plain text description (truncated to 80 chars).
    """
    try:
        parsed = docstring_parse(cmd_app.help, "plaintext")
        text = parsed.short_description or ""
    except Exception:
        text = str(cmd_app.help or "")

    text = strip_markup(text, format=help_format)
    return _escape_zsh_description(text)
