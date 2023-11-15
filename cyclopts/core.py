import importlib
import inspect
import os
import shlex
import sys
from functools import partial
from typing import Callable, Dict, Iterable, Optional, Tuple, Union

from attrs import Factory, define, field, frozen
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


def _validate_default_command(x):
    if isinstance(x, App):
        raise TypeError("Cannot register a sub-App to default.")
    return x


@define(kw_only=True)
class App:
    # Name of the Program
    default_command: Optional[Callable] = field(default=None, converter=_validate_default_command)

    name: Optional[str] = None  # field(default=Factory(_default_name, takes_self=True))

    version: str = field(factory=_default_version)
    version_flags: Iterable[str] = field(factory=lambda: ["--version"])

    help: Optional[str] = None
    help_flags: Iterable[str] = field(factory=lambda: ["--help", "-h"])
    help_print_usage: bool = True
    help_print_options: bool = True
    help_print_commands: bool = True
    help_panel_title: str = "Parameters"

    ######################
    # Private Attributes #
    ######################

    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, Callable] = field(init=False, factory=dict)

    _meta: "App" = field(init=False, default=None)

    ###########
    # Methods #
    ###########
    @property
    def _name_derived(self) -> str:  # TODO: better name
        """Guaranteed to have a string name."""
        if self.name:
            return self.name
        elif self.default_command is None:
            return sys.argv[0]
        else:
            return _format_name(self.default_command.__name__)

    @property
    def _help_derived(self) -> str:  # TODO: better name
        if self.help is not None:
            return self.help
        if self.default_command is None:
            return ""
        if self.default_command.__doc__ is None:
            return ""
        return self.default_command.__doc__

    @property
    def _help_short_derived(self) -> str:  # TODO: better name
        help = self._help_derived
        return help.split("\n", 1)[0]

    def version_print(self) -> None:
        print(self.version)

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

    def command(self, obj: Optional[Callable] = None, **kwargs) -> Callable:
        """Decorator to register a function as a CLI command."""
        if obj is None:  # Called ``@app.command``
            return partial(self.command, **kwargs)

        if isinstance(obj, App):
            app = obj
            if kwargs:
                raise ValueError("Cannot supplied additional configuration when registering a sub-App.")
        else:
            app = App(default_command=obj, **kwargs)

        name = kwargs.get("name", app._name_derived)

        if name in self._commands:
            raise CommandCollisionError(f'Command "{name}" previously registered as {self._commands[name]}')

        self._commands[name] = app
        return obj

    def default(self, obj=None):
        if obj is None:  # Called ``@app.default_command``
            return self.default

        if isinstance(obj, App):  # Registering a sub-App
            raise TypeError("Cannot register a sub-App to default.")

        if self.default_command is not None:
            raise CommandCollisionError(f"Default command previously set to {self.default_command}.")

        self.default_command = obj

        return obj

    def parse_special_flags(self, tokens: Union[None, str, Iterable[str]] = None):
        """Parse/Execute special flags like ``help`` and ``version``.

        May not return.
        """
        tokens = normalize_tokens(tokens)

        # Handle special flags here
        if any(flag in tokens for flag in self.help_flags):
            self.help_print(tokens)
            sys.exit()
        elif any(flag in tokens for flag in self.version_flags):
            self.version_print()
            sys.exit()

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
        elif self.default_command:
            # We need to break the recursion here
            command = self.default_command
        else:
            command = self.help_print
            bound = inspect.signature(command).bind(tokens=tokens)
            return command, bound, []

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

    def help_print(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional[Console] = None,
    ) -> None:
        tokens = normalize_tokens(tokens)

        if console is None:
            console = Console()

        command_chain = []
        command_mapping = self._commands
        function_or_app = self
        for token in tokens:
            try:
                function_or_app = command_mapping[token].function
            except KeyError:
                break
            if isinstance(function_or_app, App):
                command_mapping = function_or_app._commands
            command_chain.append(token)

        # Print the:
        #    my-app command COMMAND [ARGS] [OPTIONS]
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

        # Print the App/Command's Doc String.
        console.print(format_doc(self, function_or_app))

        # Print the meta app's parameter, if available.
        if self.meta.default_command:
            console.print(format_parameters(self.meta.default_command, title=self.meta.help_panel_title))

        # If this is a subapp:
        #    * If there are subcommands, print them.
        #    * Otherwise, print the default app parameters.
        # Otherwise:
        #     * print the command's parameters.
        if isinstance(function_or_app, App):
            console.print(format_commands(function_or_app))
        else:
            console.print(format_parameters(function_or_app, title=self.help_panel_title))

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
