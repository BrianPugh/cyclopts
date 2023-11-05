import argparse as builtin_argparse
import inspect
import os
import shlex
import sys
import typing
from functools import partial
from typing import Callable, Dict, Iterable, List, Optional, Union

from attrs import Factory, define, field

from cyclopts.bind import create_bound_arguments
from cyclopts.exceptions import CommandCollisionError, MissingTypeError, UnsupportedTypeHintError, UnusedCliTokensError
from cyclopts.help import HelpMixin
from cyclopts.parameter import get_hint_parameter


def _validate_type_supported(p: inspect.Parameter):
    # get_hint_parameter internally does some validation
    get_hint_parameter(p)
    if p.annotation is p.empty:
        raise MissingTypeError(p.name)
    if p.kind == p.POSITIONAL_ONLY:
        if typing.get_origin(p.annotation) is list:
            raise UnsupportedTypeHintError("Positional-only parameter cannot be of type 'list'.")


def _format_name(name: str):
    return name.lower().replace("_", "-")


@define
class App(HelpMixin):
    # Name of the Program
    name: str = field(default=sys.argv[0])

    # Argument Parser that may be helpful for global options if command chaining.
    # Part of ``App`` so that we can assimilate the parsing data into ``display_help``.
    argparse: builtin_argparse.ArgumentParser = field(factory=builtin_argparse.ArgumentParser)

    ######################
    # Private Attributes #
    ######################
    _default_command: Callable = field(
        init=False,
        default=Factory(lambda self: self.display_help, takes_self=True),
    )

    _commands: Dict[str, Callable] = field(init=False, factory=dict)

    _help_command_prefixes: List[str] = field(init=False, factory=list)

    ###########
    # Methods #
    ###########

    def __getitem__(self, key: str) -> Callable:
        return self._commands[key]

    def register(self, obj: Optional[Callable] = None, **kwargs) -> Callable:
        """Decorator to register a function as a CLI command."""
        if obj is None:  # Called ``app.command``
            return partial(
                self.register,
            )  # Pass the rest of params here

        if isinstance(obj, App):  # Registering a sub-App
            name = obj.name
            # Help String Prefix
            obj._help_command_prefixes.append(self.name)
        else:
            for parameter in inspect.signature(obj).parameters.values():
                _validate_type_supported(parameter)
            # TODO: command should take in optional ``name``
            name = _format_name(obj.__name__)

        # TODO: collision check
        self._commands[name] = obj
        return obj

    def register_default(self, f=None):
        if f is None:  # Called ``app.default_command``
            return partial(
                self.register_default,
            )  # Pass the rest of params here
        if self._default_command is not self.display_help:
            raise CommandCollisionError(f"Default command previously set to {self._default_command}.")
        return self.register(obj=f)

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

        # Extract out the command-string
        if tokens and tokens[0] in self._commands:
            # This is a valid command
            command = self[tokens[0]]
            tokens = tokens[1:]
        else:
            command = self._default_command

        if isinstance(command, App):
            return command.parse_known_args(tokens)

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
