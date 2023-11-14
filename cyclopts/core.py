import importlib
import inspect
import os
import shlex
import sys
from functools import partial
from typing import Callable, Dict, Iterable, NoReturn, Optional, Tuple, Union

from attrs import define, field
from rich.console import Console

from cyclopts.bind import create_bound_arguments, normalize_tokens
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    UnusedCliTokensError,
)
from cyclopts.help import format_commands, format_doc, format_parameters, format_usage


def _format_name(name: str):
    return name.lower().replace("_", "-")


def _default_version(default="0.0.0") -> str:
    """Attempts to get the calling code's ``module.__version__``.

    Returns ``default`` if it cannot find ``__version__``.
    """
    stack = inspect.stack()
    calling_frame = stack[2]  # Assumes ``App`` is calling this
    if (module := inspect.getmodule(calling_frame.frame)) is None:
        return default

    root_module_name = module.__name__.split(".")[0]
    try:
        module = importlib.import_module(root_module_name)
    except ImportError:
        return default
    return getattr(module, "__version__", default)


@define(kw_only=True)
class App:
    # Name of the Program
    name: str = field(default=sys.argv[0])

    version: str = field(factory=_default_version)
    version_flags: Iterable[str] = field(factory=lambda: ["--version"])

    help: str = ""
    help_flags: Iterable[str] = field(factory=lambda: ["--help", "-h"])
    help_print_usage: bool = True
    help_print_options: bool = True
    help_print_commands: bool = True
    help_panel_title: str = "Parameters"

    ######################
    # Private Attributes #
    ######################
    _default_command: Optional[Callable] = field(init=False, default=None)

    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, Callable] = field(init=False, factory=dict)

    _meta: "App" = field(init=False, default=None)

    ###########
    # Methods #
    ###########
    def version_print(self) -> NoReturn:
        print(self.version)
        sys.exit()

    def __getitem__(self, key: str) -> Callable:
        return self._commands[key]

    @property
    def meta(self) -> "App":
        if self._meta is None:
            self._meta = type(self)(
                help_flags=[],
                version_flags=[],
                help_panel_title="Session Parameters",
            )
        return self._meta

    def command(self, obj: Optional[Callable] = None, *, name: str = "") -> Callable:
        """Decorator to register a function as a CLI command."""
        if obj is None:  # Called ``@app.command``
            return partial(
                self.command,
                name=name,
            )  # All input keyword args must be passed here.

        if isinstance(obj, App):  # Registering a sub-App
            name = obj.name
        else:
            name = name or _format_name(obj.__name__)

        if name in self._commands:
            raise CommandCollisionError(f'Command "{name}" previously registered as {self._commands[name]}')

        self._commands[name] = obj
        return obj

    def default(self, obj=None):
        if obj is None:  # Called ``@app.default_command``
            return partial(self.default)  # All input keyword args must be passed here.

        if isinstance(obj, App):  # Registering a sub-App
            raise CycloptsError("Cannot register a sub-App to default.")

        if self._default_command is not None:
            raise CommandCollisionError(f"Default command previously set to {self._default_command}.")
        self._default_command = obj

        return obj

    def parse_special_flags(self, tokens: Union[None, str, Iterable[str]] = None):
        """Parse/Execute special flags like ``help`` and ``version``.

        May not return.
        """
        tokens = normalize_tokens(tokens)

        # Handle special flags here
        if any(flag in tokens for flag in self.help_flags):
            self.help_print(tokens)
        elif any(flag in tokens for flag in self.version_flags):
            self.version_print()

    def parse_known_args(self, tokens: Union[None, str, Iterable[str]] = None) -> Tuple:
        """Interpret arguments into a function, BoundArguments, and any remaining unknown arguments.

        Does **NOT** handle special flags.

        Parameter
        ---------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        """
        tokens = normalize_tokens(tokens)

        # Extract out the command-string
        if tokens and tokens[0] in self._commands:
            command, tokens = self[tokens[0]], tokens[1:]
        else:
            command = self._default_command

        if isinstance(command, App):
            return command.parse_known_args(tokens)

        bound, remaining_tokens = create_bound_arguments(command, tokens)
        return command, bound, remaining_tokens

    def parse_args(self, tokens: Union[None, str, Iterable[str]] = None) -> Tuple[Callable, inspect.BoundArguments]:
        """Interpret arguments into a function and BoundArguments.

        Does **NOT** handle special flags.

        Raises
        ------
        UnusedCliTokensError
            If any tokens remain after parsing.
        """
        command, bound, remaining_tokens = self.parse_known_args(tokens)
        if remaining_tokens:
            raise UnusedCliTokensError(remaining_tokens)
        return command, bound

    def __call__(self, tokens: Union[None, str, Iterable[str]] = None):
        """Interprets and executes a command.

        Parameter
        ---------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        """
        self.parse_special_flags(tokens)
        command, bound = self.parse_args(tokens)
        return command(*bound.args, **bound.kwargs)

    def help_print(self, tokens: Union[None, str, Iterable[str]] = None) -> NoReturn:
        tokens = normalize_tokens(tokens)

        console = Console()

        command_chain = []
        command_mapping = self._commands
        function_or_app = self
        for token in tokens:
            try:
                function_or_app = command_mapping[token]
            except KeyError:
                break
            if isinstance(function_or_app, App):
                command_mapping = function_or_app._commands
            command_chain.append(token)

        if self.help_print_usage:
            console.print(
                format_usage(
                    self.name,
                    command_chain,
                    command=bool(self._commands),
                    options=not bool(self._commands),  # TODO
                    args=False,  # TODO
                )
            )

        console.print(format_doc(self, function_or_app))

        if self.meta._default_command:
            console.print(format_parameters(self.meta._default_command, title=self.meta.help_panel_title))

        if isinstance(function_or_app, App):
            console.print(format_commands(function_or_app))
        else:
            console.print(format_parameters(function_or_app, title=self.help_panel_title))

        sys.exit()

    def interactive_shell(
        self,
        prompt: str = "$ ",
        quit: Iterable[str] = ["q", "quit"],
    ) -> None:
        """Create a blocking, interactive shell.

        Parameters
        ----------
        prompt: str
            Shell prompt. Defaults to ``"$ "``.
        quit: Iterable[str]
            List of strings that will cause the shell to exit and this method to return.
            Defaults to ``["q", "quit"]``
        """
        if os.name == "posix":
            print("Interactive shell. Press Ctrl-D to exit.")
        else:  # Windows
            print("Interactive shell. Press Ctrl-Z followed by Enter to exit.")

        while True:
            try:
                user_input = input(prompt)
            except EOFError:
                break

            split_user_input = shlex.split(user_input)
            if not split_user_input:
                continue
            if split_user_input[0] in quit:
                break

            try:
                self(split_user_input)
            except Exception as e:
                print(e)
