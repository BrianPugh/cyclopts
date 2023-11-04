import inspect
import os
import shlex
import sys
import typing
from functools import partial
from typing import Callable, Iterable, Optional, Union

from attrs import define, field
from autoregistry import Registry

from cyclopts.bind import create_bound_arguments
from cyclopts.exceptions import CommandCollisionError, MissingTypeError, UnsupportedTypeHintError, UnusedCliTokensError
from cyclopts.help import display_help
from cyclopts.parameter import get_hint_parameter


def _validate_type_supported(p: inspect.Parameter):
    # get_hint_parameter internally does some validation
    hint, parameter = get_hint_parameter(p)
    if p.annotation is p.empty:
        raise MissingTypeError(p.name)
    if p.kind == p.POSITIONAL_ONLY:
        if typing.get_origin(p.annotation) is list:
            raise UnsupportedTypeHintError("Positional-only parameter cannot be of type 'list'.")


@define
class App:
    registry: Registry = field(factory=partial(Registry, hyphen=True, case_sensitive=True))
    _default_command: Callable = field(default=display_help)

    def __getitem__(self, key: str) -> Callable:
        return self.registry[key]

    def command(self, f: Optional[Callable] = None, **kwargs) -> Callable:
        """Decorator to register a function as a CLI command."""
        if f is None:  # Called ``app.command``
            return partial(
                self.command,
            )  # Pass the rest of params here
        for parameter in inspect.signature(f).parameters.values():
            _validate_type_supported(parameter)
        self.registry(f, **kwargs)
        return f

    def default_command(self, f=None):
        if f is None:  # Called ``app.default_command``
            return partial(
                self.default_command,
            )  # Pass the rest of params here
        if self._default_command is not display_help:
            raise CommandCollisionError(f"Default command previously set to {self._default_command}.")
        return self.command(f=f)

    def parse_known_args(self, tokens: Union[None, str, Iterable[str]] = None):
        """Interpret arguments into a function, BoundArguments, and any remaining unknown arguments.

        Parameter
        ---------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        """
        if tokens is None:
            tokens = sys.argv[1:]  # Remove the executable
        elif isinstance(tokens, str):
            tokens = shlex.split(tokens)
        else:
            tokens = list(tokens)

        if not tokens:
            return self._default_command()

        if tokens[0] in self.registry:
            # This is a valid command
            command = self[tokens[0]]
            tokens = tokens[1:]
        else:
            command = self._default_command

        bound, remaining_tokens = create_bound_arguments(command, tokens)
        remaining_tokens = list(remaining_tokens)
        return command, bound, remaining_tokens

    def parse_args(self, tokens: Union[None, str, Iterable[str]] = None):
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
        command, bound = self.parse_args(tokens)
        return command(*bound.args, **bound.kwargs)

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
