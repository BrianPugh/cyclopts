import os
import re
from pathlib import Path
from textwrap import dedent

from cyclopts.completion.base import Command, CompletionGenerator, Option, ValueType


class ZshCompletionGenerator(CompletionGenerator):
    _SUBCMD_FMT = dedent(
        """
        _{cmd}() {{
            local line state

            _arguments -C \\
                       "1: :->cmds" \\
                       "*::arg:->args"
            case "$state" in
                cmds)
                    _values "{cmd} command" \\
        {subcmds}
                    ;;
                args)
                    case $line[1] in
        {subargs}
                    esac
                    ;;
            esac
        }}
        """
    )

    _LEAF_CMD_FMT = dedent(
        """
        _{cmd}() {{
            _arguments -s \\
        {args}{positional}
        }}
        """
    )

    _NO_OPT_CMD_FMT = dedent(
        """
        _{cmd}() {{
        }}
        """
    )

    _LINE_JOINER = " \\\n"
    _CMD_VALUE_FMT = '                    "{name}[{desc}]"'
    _ARG_SWITCH_FMT = "                {name})\n                    _{full_name}\n                    ;;"
    _markdown_regex = re.compile(r"\{\{[\.a-zA-Z]+\}\}")

    _VALUE_TYPE_COMPLETIONS = {
        ValueType.FILE: "_files",
        ValueType.DIRECTORY: "_dirs",
        ValueType.CHOICE: "_values",
        ValueType.STRING: "_guard '[^-]#'",  # Allows any string not starting with -
        ValueType.INTEGER: "_guard '[0-9]#'",  # Allows only numbers
        ValueType.FLOAT: "_guard '[0-9.]#'",  # Allows numbers and decimal point
    }

    def _install(self) -> Path:
        completion_dir = self._get_completion_dir()
        completion_dir.mkdir(parents=True, exist_ok=True)
        script_path = completion_dir / f"_{self.name}"
        with script_path.open("w") as f:
            f.write(self.generate())

        # Add to fpath if needed
        zshrc_path = Path.home() / ".zshrc"
        fpath_line = f"\nfpath=({completion_dir} $fpath)\n"
        if zshrc_path.exists():
            content = zshrc_path.read_text()
            if str(completion_dir) not in content:
                with zshrc_path.open("a") as f:
                    f.write(fpath_line)
                    f.write("autoload -Uz compinit && compinit\n")

        return script_path

    def generate(self) -> str:
        """Generate Zsh completion script for the given command structure.

        Args:
            command: Root command structure
            output_file: Optional path to output file (defaults to stdout)
        """
        self._out = [f"#compdef _{self.name} {self.name}"]
        self._dump_zsh(self.root_command.name, self.root_command.subcommands)
        return "".join(self._out)

    def _get_completion_dir(self) -> Path:
        home = Path.home()
        candidates = [
            Path("/usr/share/zsh/site-functions"),  # System-wide
            home / ".zsh/completions",  # Common user-specific
            home / ".local/share/zsh/site-functions",  # XDG user-specific
        ]
        user_dirs = [d for d in candidates if d.is_dir() and os.access(d.parent, os.W_OK)]
        if user_dirs:
            return user_dirs[0]
        else:
            # If no existing dirs are found, create a user-specific directory
            new_dir = home / ".local/share/zsh/site-functions"
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            return new_dir

    def _dump_zsh(self, cmd_str: str, subcommands: list[Command]) -> None:
        subcmds, subargs = [], []

        for subcmd in subcommands:
            if not subcmd.hidden:
                subcmds.append(self._CMD_VALUE_FMT.format(name=subcmd.name, desc=subcmd.description))

                full_name = f"{cmd_str}_{subcmd.name}"
                subargs.append(self._ARG_SWITCH_FMT.format(name=subcmd.name, full_name=full_name))

                if subcmd.subcommands:
                    self._dump_zsh(full_name, subcmd.subcommands)
                else:
                    self._dump_zsh_leaf(full_name, subcmd)

        self._out.append(
            self._SUBCMD_FMT.format(
                cmd=cmd_str,
                subcmds=self._LINE_JOINER.join(subcmds),
                subargs="".join(subargs),
            )
        )

    def _dump_zsh_leaf(self, cmd_string: str, command: Command) -> None:
        if not command.options and not command.positional_args:
            self._out.append(self._NO_OPT_CMD_FMT.format(cmd=cmd_string))
            return

        args = [self._format_option(opt) for opt in command.options]

        # Handle positional arguments
        positional = ""
        if command.positional_args:
            for i, pos_arg in enumerate(command.positional_args, 1):
                completion = self._get_value_completion(pos_arg)
                desc = self._sanitize_desc(pos_arg.desc)
                required = "" if pos_arg.multiple else f":{desc}:{completion}"
                positional += f' \\\n               "{i}{required}"'

        self._out.append(
            self._LEAF_CMD_FMT.format(
                cmd=cmd_string, args=self._LINE_JOINER.join(args) if args else "", positional=positional
            )
        )

    def _get_value_completion(self, opt: Option) -> str:
        """Get the appropriate completion function for an option's value type."""
        if not opt.value_type:
            return ""

        completion_func = self._VALUE_TYPE_COMPLETIONS[opt.value_type]

        if opt.value_type == ValueType.CHOICE and opt.choices:
            choices = " ".join(f'"{c}"' for c in opt.choices)
            return f"{completion_func} '{choices}'"

        return completion_func

    def _format_option(self, opt: Option) -> str:
        """Format a command option for the completion script."""
        completion = self._get_value_completion(opt)

        # Handle options that take values
        value_spec = f":{opt.val_desc or opt.desc}:{completion}" if completion else ""

        # Handle required/optional arguments
        if opt.required:
            value_spec = f":{opt.val_desc or opt.desc}:{completion}"
        elif completion:
            value_spec = f"::{completion}"

        # Handle multiple values
        if opt.multiple and completion:
            value_spec = f"*{value_spec}"

        if opt.abbrev and opt.name:
            format_string = f"{'-' + opt.abbrev},--{opt.name}"
            return f"               '{format_string}[{self._sanitize_desc(opt.desc)}]{value_spec}'"
        elif opt.name:
            format_string = f"--{opt.name}"
            return f"               '({format_string}){format_string}[{self._sanitize_desc(opt.desc)}]{value_spec}'"
        elif opt.abbrev:
            format_string = f"-{opt.abbrev}"
            return f"               '({format_string}){format_string}[{self._sanitize_desc(opt.desc)}]{value_spec}'"
        else:
            raise ValueError("Option must have either name or abbreviation")

    def _sanitize_desc(self, desc: str) -> str:
        """Sanitize option description text."""
        if not desc:
            return ""

        desc = desc.replace("'", "''")
        desc = self._markdown_regex.sub("", desc)

        if "\n" in desc:
            desc = desc[: desc.index("\n")]

        return desc
