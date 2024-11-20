import os
import re
from pathlib import Path
from textwrap import dedent

from cyclopts.completion.base import Command, CompletionGenerator, Option


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
        {args}
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
        """Generate completion functions for a command and its subcommands."""
        subcmds, subargs = [], []

        for subcmd in subcommands:
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
        """Generate completion function for a leaf command (one without subcommands)."""
        if not command.options:
            self._out.append(self._NO_OPT_CMD_FMT.format(cmd=cmd_string))
            return

        args = [self._format_option(opt) for opt in command.options]
        self._out.append(self._LEAF_CMD_FMT.format(cmd=cmd_string, args=self._LINE_JOINER.join(args)))

    def _format_option(self, opt: Option) -> str:
        """Format a command option for the completion script."""
        if opt.abbrev and opt.name:
            format_string = f"-{opt.abbrev},--{opt.name}"
            template = "               {{{}}}'{} [{}]'" if opt.desc else "               {{{}}}'{} {}'"
            return template.format(format_string, format_string, self._sanitize_desc(opt.desc))
        elif opt.name:
            format_string = f"--{opt.name}"
            template = "               '({}){} [{}]'" if opt.desc else "               '({}){}'"
            return template.format(format_string, format_string, self._sanitize_desc(opt.desc))
        elif opt.abbrev:
            format_string = f"-{opt.abbrev}"
            template = "               '({}){} [{}]'" if opt.desc else "               '({}){}'"
            return template.format(format_string, format_string, self._sanitize_desc(opt.desc))
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
