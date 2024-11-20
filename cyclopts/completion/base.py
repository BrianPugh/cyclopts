import os
from abc import abstractmethod
from contextlib import suppress
from pathlib import Path

from attrs import define
from autoregistry import Registry


@define
class Option:
    name: str
    abbrev: str
    desc: str = ""
    val_desc: str = ""


@define
class Command:
    name: str
    description: str
    subcommands: list["Command"]
    options: list[Option]
    hidden: bool = False
    requires_repo: bool = True


class UnknownShellError(Exception):
    pass


class CompletionGenerator(Registry, suffix="CompletionGenerator"):
    def __new__(cls, *args, shell=None, **kwargs) -> "CompletionGenerator":
        """Detect the currently running shell and return the appropriate generator."""
        if shell is not None:
            return super().__new__(cls[shell], *args, **kwargs)

        # First check the SHELL environment variable
        shell_path = Path(os.environ.get("SHELL", ""))
        if shell_path:
            shell_name = shell_path.name.lower()
            for subclass in cls.values():
                if subclass.__registry__.name in shell_name:
                    return super().__new__(subclass, *args, **kwargs)

        # If SHELL isn't set or is unknown, try checking process tree
        # On Linux/Unix, we can check the parent process name
        with suppress(Exception):
            ppid = os.getppid()
            with Path(f"/proc/{ppid}/comm").open() as f:
                parent_name = f.read().strip().lower()
                for subclass in cls.values():
                    if subclass.__registry__.name in parent_name:
                        return super().__new__(subclass, *args, **kwargs)

        raise UnknownShellError

    def __init__(self, root_command: Command):
        self.root_command = root_command
        self._out = []  # Scratch pad for output

    def install(self) -> Path:
        """Install the completion script to the system.

        Returns
        -------
        Path
            Path to installed script.
        """
        script_path = self._install()
        # Make the script executable
        script_path.chmod(0o755)

        print(f"Installed completion script for {self.shell_name} at {script_path}")
        print("Please restart your shell or source your shell's rc file to enable completions.")

        return script_path

    @property
    def shell_name(self):
        return type(self).__registry__.name

    @property
    def name(self):
        return self.root_command.name

    @abstractmethod
    def _install(self) -> Path:
        """Private install completion script.

        Returns
        -------
        Path
            Path to installed script.
        """
        raise NotImplementedError

    @abstractmethod
    def generate(self) -> str:
        """Generate completion script.

        Returns
        -------
        str
            Completion script.
        """
        raise NotImplementedError
