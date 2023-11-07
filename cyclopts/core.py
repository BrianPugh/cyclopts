import importlib
import inspect
import os
import shlex
import sys
import typing
from functools import partial
from typing import Callable, Dict, Iterable, List, NewType, Optional, Union

import attrs
from attrs import Factory, define, field

from cyclopts.bind import create_bound_arguments
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    MissingTypeError,
    UnsupportedTypeHintError,
    UnusedCliTokensError,
)
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


def _normalize_tokens(tokens: Union[None, str, Iterable[str]]) -> List[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


@define(kw_only=True)
class App(HelpMixin):
    # Name of the Program
    name: str = field(default=sys.argv[0])

    version: str = field(factory=_default_version)
    version_flags: Iterable[str] = field(factory=lambda: ["--version"])

    ######################
    # Private Attributes #
    ######################
    _default_command: Callable = field(
        init=False,
        default=Factory(lambda self: self.help_print, takes_self=True),
    )

    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, Callable] = field(init=False, factory=dict)

    _meta: "MetaApp" = field(init=False, default=None)

    ###########
    # Methods #
    ###########
    def version_print(self):
        print(self.version)

    def __getitem__(self, key: str) -> Callable:
        return self._commands[key]

    @property
    def meta(self) -> "MetaApp":
        if self._meta is None:
            self._meta = MetaApp(
                help_print=self.help_print,
                help_panel_title="Session Parameters",
            )
        return self._meta

    def register(self, obj: Optional[Callable] = None, *, name: str = "", **kwargs) -> Callable:
        """Decorator to register a function as a CLI command."""
        if obj is None:  # Called ``@app.command``
            return partial(
                self.register,
            )  # Pass the rest of params here

        if isinstance(obj, App):  # Registering a sub-App
            name = obj.name
            obj._help_usage_prefixes.append(self.name)
        else:
            for parameter in inspect.signature(obj).parameters.values():
                _validate_type_supported(parameter)
            name = name or _format_name(obj.__name__)

        if name in self._commands:
            raise CommandCollisionError(f'Command "{name}" previously registered as {self._commands[name]}')

        self._commands[name] = obj
        return obj

    def register_default(self, obj=None, **kwargs):
        if obj is None:  # Called ``@app.default_command``
            return partial(self.register_default, **kwargs)  # Pass the rest of params here

        if isinstance(obj, App):  # Registering a sub-App
            raise CycloptsError("Cannot register a sub App to default.")

        if self._default_command != self.help_print:
            raise CommandCollisionError(f"Default command previously set to {self._default_command}.")
        self._default_command = obj

        for parameter in inspect.signature(obj).parameters.values():
            _validate_type_supported(parameter)

        return obj

    def parse_known_args(self, tokens: Union[None, str, Iterable[str]] = None):
        """Interpret arguments into a function, BoundArguments, and any remaining unknown arguments.

        Parameter
        ---------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        """
        tokens = _normalize_tokens(tokens)

        # Extract out the command-string
        if tokens and tokens[0] in self._commands:
            command, tokens = self[tokens[0]], tokens[1:]
        else:
            command = self._default_command

        if isinstance(command, App):
            return command.parse_known_args(tokens)

        if any(flag in tokens for flag in self.help_flags):
            if command is self.help_print:
                command = None
            command = partial(self.help_print, function=command)
            bound = inspect.signature(command).bind()
            remaining_tokens = []
        elif any(flag in tokens for flag in self.version_flags):
            command = self.version_print
            bound = inspect.signature(command).bind()
            remaining_tokens = []
        else:
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


@define(kw_only=True)
class MetaApp(App):
    @property
    def meta(self):
        raise CycloptsError("Cannot nest meta apps.")

    def register(self, *args, **kwargs):
        raise CycloptsError("Cannot register commands to a meta app.")
