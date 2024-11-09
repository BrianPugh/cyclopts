import os
import textwrap
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Set

from attrs import Factory, define, field


class ParamType(Enum):
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    FILE = auto()
    DIRECTORY = auto()
    CHOICE = auto()


class Shell(Enum):
    BASH = "bash"
    ZSH = "zsh"
    UNKNOWN = "unknown"


@define
class Parameter:
    name: str = field()
    param_type: ParamType = field()
    description: str = field()
    choices: List[str] | None = field(default=None)
    is_required: bool = field(default=False)
    short_flag: str | None = field(default=None)
    long_flag: str | None = field(default=None)


@define
class Command:
    name: str = field()
    description: str = field()
    parameters: List[Parameter] = field(factory=list)
    subcommands: Dict[str, "Command"] = field(factory=dict)
    aliases: Set[str] = field(factory=set)


@define
class CompletionGenerator:
    program_name: str = field()
    description: str = field()
    root_command: Command = field(
        init=False,
        default=Factory(lambda x: Command(x.program_name, x.description), takes_self=True),
    )

    def detect_shell(self) -> Shell:
        """Detect the currently running shell."""
        # First check the SHELL environment variable
        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            shell_name = os.path.basename(shell_path).lower()
            if "bash" in shell_name:
                return Shell.BASH
            elif "zsh" in shell_name:
                return Shell.ZSH

        # If SHELL isn't set or is unknown, try checking process tree
        try:
            # On Linux/Unix, we can check the parent process name
            ppid = os.getppid()
            with open(f"/proc/{ppid}/comm") as f:
                parent_name = f.read().strip().lower()
                if "bash" in parent_name:
                    return Shell.BASH
                elif "zsh" in parent_name:
                    return Shell.ZSH
        except:
            pass

        return Shell.UNKNOWN

    def get_completion_dir(self, shell: Shell) -> Path:
        """Get the appropriate completion directory for the given shell."""
        home = Path.home()

        if shell == Shell.BASH:
            # Check common Bash completion directories
            candidates = [
                Path("/etc/bash_completion.d"),  # System-wide
                home / ".local/share/bash-completion/completions",  # User-specific
                home / ".bash_completion.d",  # Legacy user-specific
            ]
        elif shell == Shell.ZSH:
            # Check common Zsh completion directories
            candidates = [
                Path("/usr/share/zsh/site-functions"),  # System-wide
                home / ".zsh/completions",  # Common user-specific
                home / ".local/share/zsh/site-functions",  # XDG user-specific
            ]
        else:
            raise ValueError(f"Unsupported shell: {shell}")

        # Return the first writable directory, preferring user-specific locations
        user_dirs = [d for d in candidates if d.is_dir() and os.access(d.parent, os.W_OK)]
        if not user_dirs:
            # If no existing dirs are found, create a user-specific directory
            if shell == Shell.BASH:
                new_dir = home / ".local/share/bash-completion/completions"
            else:  # ZSH
                new_dir = home / ".local/share/zsh/site-functions"
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            return new_dir
        return user_dirs[0]

    def install_completion(self) -> None:
        """
        Detect the current shell and install the appropriate completion script.
        Raises RuntimeError if the shell is not supported or if installation fails.
        """
        shell = self.detect_shell()
        if shell == Shell.UNKNOWN:
            raise RuntimeError(
                "Unable to detect shell. Please manually install completion scripts " "using save_completion_scripts()."
            )

        try:
            completion_dir = self.get_completion_dir(shell)
            completion_dir.mkdir(parents=True, exist_ok=True)

            if shell == Shell.BASH:
                script_path = completion_dir / f"{self.program_name}"
                with open(script_path, "w") as f:
                    f.write(self.generate_bash_completion())

                # Add source line to .bashrc if not already present
                bashrc_path = Path.home() / ".bashrc"
                source_line = f"\n# {self.program_name} completion\nsource {script_path}\n"

                if bashrc_path.exists():
                    with open(bashrc_path) as f:
                        content = f.read()
                    if str(script_path) not in content:
                        with open(bashrc_path, "a") as f:
                            f.write(source_line)

            elif shell == Shell.ZSH:
                script_path = completion_dir / f"_{self.program_name}"
                with open(script_path, "w") as f:
                    f.write(self.generate_zsh_completion())

                # Add to fpath if needed
                zshrc_path = Path.home() / ".zshrc"
                fpath_line = f"\nfpath=({completion_dir} $fpath)\n"
                if zshrc_path.exists():
                    with open(zshrc_path) as f:
                        content = f.read()
                    if str(completion_dir) not in content:
                        with open(zshrc_path, "a") as f:
                            f.write(fpath_line)
                            f.write("autoload -Uz compinit && compinit\n")
            else:
                raise ValueError

            # Make the script executable
            script_path.chmod(0o755)

            print(f"Installed completion script for {shell.value} at {script_path}")
            print("Please restart your shell or source your shell's rc file to enable completions.")

        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to install completion script: {e}")

    def add_parameter(self, param: Parameter, command_path: List[str] | None = None) -> None:
        """Add a parameter to a specific command (or root if no path specified)."""
        target_command = self._get_command_by_path(command_path)
        target_command.parameters.append(param)

    def add_command(self, command: Command, parent_path: List[str] | None = None) -> None:
        """Add a command at the specified path in the command tree."""
        parent = self._get_command_by_path(parent_path)
        parent.subcommands[command.name] = command
        for alias in command.aliases:
            parent.subcommands[alias] = command

    def _get_command_by_path(self, path: List[str] | None = None) -> Command:
        """Get a command object by its path in the command tree."""
        if not path:
            return self.root_command

        current = self.root_command
        for component in path:
            current = current.subcommands.get(component)
            if not current:
                raise ValueError(f"Invalid command path: {path}")
        return current

    def _generate_bash_param_completion(self, param: Parameter) -> str:
        """Generate bash completion code for a single parameter."""
        completion = []
        flags = []

        if param.short_flag:
            flags.append(param.short_flag)
        if param.long_flag:
            flags.append(param.long_flag)

        flags_str = "|".join(flags)

        if param.param_type == ParamType.FILE:
            completion.append('COMPREPLY+=($(compgen -f -- "$cur"))')
        elif param.param_type == ParamType.DIRECTORY:
            completion.append('COMPREPLY+=($(compgen -d -- "$cur"))')
        elif param.param_type == ParamType.CHOICE and param.choices:
            choices_str = " ".join(param.choices)
            completion.append(f'COMPREPLY+=($(compgen -W "{choices_str}" -- "$cur"))')

        return f"""
            {flags_str})
                {" ".join(completion)}
                return 0
                ;;
        """

    def _generate_bash_command_completion(self, command: Command, path: List[str] | None = None) -> str:
        """Generate bash completion code for a command and its subcommands."""
        if path is None:
            path = []

        current_path = " ".join(path)
        subcommands = " ".join(command.subcommands.keys())

        completion_code = []

        # Add completion for current command's parameters
        if command.parameters:
            param_completions = [self._generate_bash_param_completion(param) for param in command.parameters]
            completion_code.extend(param_completions)

        # Add subcommand handling
        if command.subcommands:
            completion_code.append(
                f"""
                "")
                    if [ "$cword" = "{len(path) + 1}" ]; then
                        COMPREPLY=($(compgen -W "{subcommands}" -- "$cur"))
                        return 0
                    fi
                    ;;
            """
            )

            # Generate completion for each subcommand
            for subcmd_name, subcmd in command.subcommands.items():
                if subcmd_name in subcmd.aliases:
                    continue  # Skip alias entries
                new_path = path + [subcmd_name]
                completion_code.append(self._generate_bash_command_completion(subcmd, new_path))

        return "\n".join(completion_code)

    def generate_bash_completion(self) -> str:
        """Generate bash completion script."""
        completion_function = f"""
__{self.program_name}_completion()
{{
    local cur prev words cword
    _init_completion || return

    # Get the current command path
    local cmd_path=()
    local i
    for ((i=1; i < cword; i++)); do
        case "${{words[i]}}" in
            -*) continue ;;
            *) cmd_path+=("${{words[i]}}") ;;
        esac
    done

    case "$prev" in
        {self._generate_bash_command_completion(self.root_command)}
        *)
            local opts=""
            for param in "${{parameters[@]}}"; do
                [[ -n "${{param_short_flags[$param]}}" ]] && opts+=" ${{param_short_flags[$param]}}"
                [[ -n "${{param_long_flags[$param]}}" ]] && opts+=" ${{param_long_flags[$param]}}"
            done
            COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
            return 0
            ;;
    esac
}}

complete -F __{self.program_name}_completion {self.program_name}
"""
        return textwrap.dedent(completion_function)

    def _generate_zsh_param_completion(self, param: Parameter) -> str:
        """Generate zsh completion code for a single parameter."""
        completion = []

        if param.short_flag or param.long_flag:
            flags = []
            if param.short_flag:
                flags.append(param.short_flag.lstrip("-"))
            if param.long_flag:
                flags.append(param.long_flag.lstrip("-"))

            description = param.description.replace("'", "''")

            if param.param_type == ParamType.FILE:
                completion.append(f"'{','.join(flags)}::{description}:_files'")
            elif param.param_type == ParamType.DIRECTORY:
                completion.append(f"'{','.join(flags)}::{description}:_directories'")
            elif param.param_type == ParamType.CHOICE and param.choices:
                choices_str = " ".join(param.choices)
                completion.append(f"'{','.join(flags)}::{description}:({choices_str})'")
            else:
                completion.append(f"'{','.join(flags)}::{description}'")

        return "\n        ".join(completion)

    def _generate_zsh_command_completion(self, command: Command, path: List[str] | None = None) -> str:
        """Generate zsh completion code for a command and its subcommands."""
        if path is None:
            path = []

        completion_code = []

        # Add current command's parameters
        for param in command.parameters:
            completion_code.append(self._generate_zsh_param_completion(param))

        # Add subcommands
        if command.subcommands:
            subcmds = {}
            for name, cmd in command.subcommands.items():
                if name not in cmd.aliases:  # Skip alias entries
                    subcmds[name] = cmd.description

            subcommand_str = " ".join(f"{name}:{desc}" for name, desc in subcmds.items())
            current_path = " ".join(path)

            if current_path:
                completion_code.append(f"'1: :{current_path} command:({subcommand_str})'")
            else:
                completion_code.append(f"'1:command:({subcommand_str})'")

            # Generate completion for each subcommand
            for subcmd_name, subcmd in command.subcommands.items():
                if subcmd_name in subcmd.aliases:
                    continue
                new_path = path + [subcmd_name]
                completion_code.append(self._generate_zsh_command_completion(subcmd, new_path))

        return "\n        ".join(completion_code)

    def generate_zsh_completion(self) -> str:
        """Generate zsh completion script."""
        completion_function = f"""#compdef {self.program_name}

_arguments -C \\
        {self._generate_zsh_command_completion(self.root_command)}
"""
        return textwrap.dedent(completion_function)

    def save_completion_scripts(self, bash_output_path: str, zsh_output_path: str) -> None:
        """Save generated completion scripts to files."""
        with open(bash_output_path, "w") as f:
            f.write(self.generate_bash_completion())

        with open(zsh_output_path, "w") as f:
            f.write(self.generate_zsh_completion())
