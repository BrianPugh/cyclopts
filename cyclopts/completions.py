from abc import abstractmethod
from typing import TYPE_CHECKING, List, Tuple

from attrs import define, field
from autoregistry import Registry

from cyclopts.exceptions import InvalidCommandError
from cyclopts.help import docstring_parse

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class Element:
    names: Tuple[str, ...]
    description: str = ""


@define
class Command(Element):
    parameters: List[Element] = field(factory=list)
    commands: List["Command"] = field(factory=list)


def _unique_commands(app) -> List[List[str]]:
    unique_commands = {}
    for cmd_name in app:
        cmd_id = id(app[cmd_name])
        unique_commands.setdefault(cmd_id, [])
        unique_commands[cmd_id].append(cmd_name)
    return list(unique_commands.values())


class ShellComplete(Registry, suffix="Complete"):
    def __init__(self, app):
        self.app = app
        self.components = []

    def _generate(self, command_chain: Tuple[str, ...], name: Tuple[str, ...]) -> Command:
        """Private Recursive."""
        parameters = []
        if name:
            command_chain = command_chain + (name[0],)

        app = self.app
        for command_token in command_chain:
            app = app[command_token]

        try:
            resolved_command = self.app._resolve_command(command_chain)
        except InvalidCommandError:
            pass
        else:
            for cli_name, (iparam, _) in resolved_command.cli2parameter.items():
                if iparam.kind not in (iparam.KEYWORD_ONLY, iparam.POSITIONAL_OR_KEYWORD):
                    continue
                cparam = resolved_command.iparam_to_cparam[iparam]
                if not cparam.show:
                    continue
                parameters.append(Element((cli_name,), cparam.help))

        # TODO: if a "choice" option is currently being completed, we should handle choice completions.

        out = Command(
            name or (self.app.name[0],),
            docstring_parse(app.help).short_description or "",
            parameters=parameters,
            commands=[self._generate(command_chain, tuple(names)) for names in _unique_commands(app)],
        )
        return out

    def generate(self) -> str:
        cmd = self._generate((), ())
        return self.generate_script(cmd)

    @abstractmethod
    def generate_script(self, root_cmd: Command) -> str:
        pass


class ZshComplete(ShellComplete):
    """ZSH Shell Completion Script Generation.

    ZSH completion script modeled after:

        https://www.dolthub.com/blog/2021-11-15-zsh-completions-with-subcommands/
    """

    def generate_script(self, root_cmd) -> str:
        def sanitize_name(s: str) -> str:
            return s.replace(".", "_").replace("-", "_")

        def generate_argument(element: Element) -> str:
            name = ",".join(element.names)
            return f'        "{name}[{element.description}]"'

        def generate_value(element: Element) -> str:
            name = ",".join(element.names)
            return f'                "{name}[{element.description}]" \\'

        def generate_line_case(cmd: Command, target: str) -> List[str]:
            out = []
            for name in cmd.names:
                out.append(f"                {name})")
                out.append(f"                    {target}")
                out.append("                    ;;")
            return out

        def generate_function(command_chain: Tuple[str, ...], command: Command) -> List[str]:
            fscript = []
            command_chain = command_chain + (command.names[0],)
            sanitized_name = "_" + sanitize_name("_".join(command_chain))
            fscript.append(f"{sanitized_name}()")
            fscript.append("{")

            if command.commands:
                fscript.append("    local line state")
                fscript.append("    _arguments -C \\")
                fscript.append('        "1: :->cmds" \\')
                for argument in command.parameters:
                    fscript.append(generate_argument(argument) + " \\")
                fscript.append('        "*::arg->args"')
                fscript.append('    case "$state" in')
                fscript.append("        cmds)")
                fscript.append(f'            _values "{sanitized_name} command" \\')
                for subcommand in command.commands:
                    fscript.append(generate_value(subcommand))
                fscript.append("            ;;")
                fscript.append("        args)")
                fscript.append("            case $line[1] in")
                for subcommand in command.commands:
                    target = sanitized_name + "_" + sanitize_name(subcommand.names[0])
                    fscript.extend(generate_line_case(subcommand, target))
                fscript.append("            esac")
                fscript.append("            ;;")
                fscript.append("    esac")
            else:
                command_arguments = [generate_argument(x) for x in command.parameters]
                if command_arguments:
                    fscript.append("    _arguments -s \\")
                    fscript.append(" \\\n".join(command_arguments))

            fscript.append("}")
            fscript.append("")

            for subcmd in command.commands:
                fscript.extend(generate_function(command_chain, subcmd))

            return fscript

        complete_script = []
        sanitized_root_name = sanitize_name(root_cmd.names[0])
        complete_script.append(f"#compdef _{sanitized_root_name} {sanitized_root_name}")
        complete_script.append("")
        complete_script.extend(generate_function((), root_cmd))
        # TODO: Not sure this is necessary
        complete_script.append(f"compdef _{sanitized_root_name} {sanitized_root_name}")

        return "\n".join(complete_script)
