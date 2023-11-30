import importlib
import inspect
import os
import sys
from functools import partial
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

from attrs import define, evolve, field
from rich.console import Console

from cyclopts.bind import create_bound_arguments, normalize_tokens
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    InvalidCommandError,
    UnusedCliTokensError,
    format_cyclopts_error,
)
from cyclopts.help import create_panel_table_commands, format_command_rows, format_doc, format_parameters, format_usage
from cyclopts.parameter import validate_command


def _format_name(name: str):
    return name.lower().replace("_", "-").strip("-")


def _default_version(default="0.0.0") -> str:
    """Attempts to get the calling code's ``module.__version__``.

    Returns
    -------
    version: str
        ``default`` if it cannot find ``__version__``.
    """
    stack = inspect.stack()
    calling_frame = stack[2]  # Assumes App is calling this
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
    """Cyclopts Application.

    Parameters
    ----------
    name: Optional[str]
        Name of application, or subcommand if registering to another application.
        If not provided, defaults to ``sys.argv[0]``.
    version: Optional[str]
        Version to be displayed when a token of ``version_flags`` is parsed.
        Defaults to attempting to use ``package.__version__`` from the package instantiating :class:`App`.
    version_flags: Union[str, Iterable[str]]
        Token(s) that trigger :meth:`version_print`.
        Set to an empty list to disable version feature.
        Defaults to ``["--version"]``.
    help: Optional[str]
        Text to display on help screen.
    help_flags: Union[str, Iterable[str]]
        Tokens that trigger :meth:`help_print`.
        Set to an empty list to disable help feature.
        Defaults to ``["--help", "-h"]``.
    help_title_commands: str
        Title for the "commands" help-panel.
        Defaults to ``"Commands"``.
    help_title_parameters: str
        Title for the "parameters" help-panel.
        Defaults to ``"Parameters"``.
    """

    default_command: Optional[Callable] = field(default=None, converter=_validate_default_command)

    _name: Optional[str] = field(default=None, alias="name")

    version: str = field(factory=_default_version)
    version_flags: Iterable[str] = field(factory=lambda: ["--version"])

    help: Optional[str] = field(default=None)
    help_flags: Iterable[str] = field(factory=lambda: ["--help", "-h"])
    help_title_commands: str = "Commands"
    help_title_parameters: str = "Parameters"

    ######################
    # Private Attributes #
    ######################
    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, "App"] = field(init=False, factory=dict)

    _meta: "App" = field(init=False, default=None)
    _meta_parent: "App" = field(init=False, default=None)

    ###########
    # Methods #
    ###########
    @property
    def name(self) -> str:
        """Application name. Dynamically derived if not previously set."""
        if self._name:
            return self._name
        elif self.default_command is None:
            return sys.argv[0]
        else:
            return _format_name(self.default_command.__name__)

    @property
    def help_(self) -> str:
        if self.help is not None:
            return self.help
        if self.default_command is None:
            return ""
        if self.default_command.__doc__ is None:
            return ""
        return self.default_command.__doc__

    def version_print(self) -> None:
        """Print the application version."""
        print(self.version)

    def __getitem__(self, key: str) -> "App":
        """Get the subapp from a command string.

        All commands get registered to Cyclopts as subapps.
        The actual function handler is at ``app[key].default_command``.
        """
        return self._commands[key]

    def __contains__(self, k: str) -> bool:
        if k in self._commands:
            return True
        if self._meta_parent:
            return k in self._meta_parent
        return False

    @property
    def meta(self) -> "App":
        if self._meta is None:
            self._meta = type(self)(
                help_title_parameters="Session Parameters",
            )
            self._meta._meta_parent = self
        return self._meta

    def _parse_command_chain(self, tokens):
        command_chain = []
        command_mapping = self._commands
        app = self
        unused_tokens = tokens
        for i, token in enumerate(tokens):
            try:
                app = command_mapping[token]
                unused_tokens = tokens[i + 1 :]
            except KeyError:
                break
            command_mapping = app._commands
            command_chain.append(token)
        return command_chain, app, unused_tokens

    def command(self, obj: Optional[Callable] = None, **kwargs) -> Callable:
        """Decorator to register a function as a CLI command.

        Parameters
        ----------
        obj: Optional[Callable]
            Function or :class:`App` to be registered as a command.
        `**kwargs`
            Any argument that :class:`App` can take.
            ``name`` and ``help`` are common arguments.
        """
        if obj is None:  # Called ``@app.command``
            return partial(self.command, **kwargs)

        name = None

        if isinstance(obj, App):
            app = obj

            if app._name is None:
                name = kwargs.pop("name", None)
                if name is None:
                    raise ValueError("Sub-app MUST have a name specified.") from None

            if kwargs:
                raise ValueError("Cannot supplied additional configuration when registering a sub-App.")
        else:
            validate_command(obj)
            kwargs.setdefault("name", None)
            kwargs.setdefault("help", None)
            kwargs.setdefault("help_flags", [])
            kwargs.setdefault("version_flags", [])
            app = evolve(self, default_command=obj, **kwargs)

        if name is None:
            name = app.name

        if name in self:
            raise CommandCollisionError(f'Command "{name}" already registered.')

        self._commands[name] = app
        return obj

    def default(self, obj=None):
        """Decorator to register a function as the default action handler."""
        if obj is None:  # Called ``@app.default_command``
            return self.default

        if isinstance(obj, App):  # Registering a sub-App
            raise TypeError("Cannot register a sub-App to default.")

        if self.default_command is not None:
            raise CommandCollisionError(f"Default command previously set to {self.default_command}.")

        validate_command(obj)
        self.default_command = obj
        return obj

    def parse_known_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional[Console] = None,
    ) -> Tuple[Callable, inspect.BoundArguments, List[str]]:
        """Interpret arguments into a function, BoundArguments, and any remaining unknown tokens.

        **Does NOT** handle special flags like "version" or "help".

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``

        Returns
        -------
        command: Callable
            Bare function to execute.

        bound: inspect.BoundArguments
            Bound arguments for ``command``.

        unused_tokens: List[str]
            Any remaining CLI tokens that didn't get parsed for ``command``.
        """
        tokens = normalize_tokens(tokens)

        command_chain, app, unused_tokens = self._parse_command_chain(tokens)

        try:
            if app is not self:
                return app.parse_known_args(unused_tokens)

            if self.default_command:
                command = self.default_command
                bound, unused_tokens = create_bound_arguments(command, unused_tokens)
                return command, bound, unused_tokens
            else:
                if unused_tokens:
                    raise InvalidCommandError(unused_tokens=unused_tokens)
                else:
                    # Running the application with no arguments and no registered
                    # ``default_command`` will default to ``help_print``.
                    command = self.help_print
                    bound = inspect.signature(command).bind(tokens=tokens, console=console)
                    return command, bound, []
        except CycloptsError as e:
            e.app = app
            if command_chain:
                e.command_chain = command_chain
            raise

        raise NotImplementedError("Should never get here.")

    def parse_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional[Console] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        verbose: bool = False,
    ) -> Tuple[Callable, inspect.BoundArguments]:
        """Interpret arguments into a function and BoundArguments.

        **Does** handle special flags like "version" or "help".

        Raises
        ------
        UnusedCliTokensError
            If any tokens remain after parsing.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        print_error: bool
            Print a rich-formatted error on error.
            Defaults to ``True``.
        exit_on_error: bool
            If there is an error parsing the CLI tokens invoke ``sys.exit(1)``.
            Otherwise, continue to raise the exception.
            Defaults to ``True``.
        verbose: bool
            Populate exception strings with more information intended for developers.
            Defaults to ``False``.

        Returns
        -------
        command: Callable
            Function associated with command action.

        bound: inspect.BoundArguments
            Parsed and converted ``args`` and ``kwargs`` to be used when calling ``command``.
        """
        tokens = normalize_tokens(tokens)

        meta_parent = self

        try:
            # Special flags (help/version) get bubbled up to the root app.
            # The root ``help_print`` will then traverse the meta app linked list.
            if any(flag in tokens for flag in self.help_flags):
                command = self.help_print
                while meta_parent := meta_parent._meta_parent:
                    command = meta_parent.help_print
                bound = inspect.signature(command).bind(tokens, console=console)
                unused_tokens = []
            elif any(flag in tokens for flag in self.version_flags):
                # Version
                command = self.version_print
                while meta_parent := meta_parent._meta_parent:
                    command = meta_parent.version_print
                bound = inspect.signature(command).bind()
                unused_tokens = []
            else:
                # Normal parsing
                command, bound, unused_tokens = self.parse_known_args(tokens, console=console)
                if unused_tokens:
                    raise UnusedCliTokensError(
                        target=command,
                        unused_tokens=unused_tokens,
                    )
        except CycloptsError as e:
            e.verbose = verbose
            e.root_input_tokens = tokens
            if print_error:
                if console is None:
                    console = Console()
                console.print(format_cyclopts_error(e))

            if exit_on_error:
                sys.exit(1)
            else:
                raise

        return command, bound

    def __call__(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        **kwargs,
    ):
        """Interprets and executes a command.

        Parameters
        ----------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        `**kwargs`
            Passed along to :meth:`parse_args`.

        Returns
        -------
        return_value: Any
            The value the parsed command handler returns.
        """
        tokens = normalize_tokens(tokens)
        command, bound = self.parse_args(tokens, **kwargs)
        return command(*bound.args, **bound.kwargs)

    def help_print(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional[Console] = None,
    ) -> None:
        """Print the help page.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Tokens to interpret for traversing the application command structure.
        """
        tokens = normalize_tokens(tokens)

        if console is None:
            console = Console()

        command_chain, app, _ = self._parse_command_chain(tokens)

        # Print the:
        #    my-app command COMMAND [ARGS] [OPTIONS]
        console.print(format_usage(self, command_chain))

        # Print the App/Command's Doc String.
        console.print(format_doc(self, app))

        def walk_apps():
            # Iterates from deepest to shallowest
            meta_list = [app]  # shallowest to deepest
            meta = self
            while (meta := meta._meta) and meta.default_command:
                meta_list.append(meta)
            yield from reversed(meta_list)

        show_special = True

        command_rows = {}
        for app in walk_apps():
            command_rows.setdefault(app.help_title_commands, [])
            command_rows[app.help_title_commands].extend(format_command_rows(app))

            console.print(
                format_parameters(
                    app,
                    app.help_title_parameters,
                    show_special=show_special,
                )
            )

            show_special = False

        # Rely on dictionary insertion order.
        for title, rows in command_rows.items():
            if not rows:
                continue
            rows.sort(key=lambda x: x[0])  # sort by command name
            panel, table = create_panel_table_commands(title=title)
            for row in rows:
                table.add_row(*row)
            console.print(panel)

    def interactive_shell(
        self,
        prompt: str = "$ ",
        quit: Union[None, str, Iterable[str]] = None,
        **kwargs,
    ) -> None:
        """Create a blocking, interactive shell.

        All registered commands can be executed in the shell.

        Parameters
        ----------
        prompt: str
            Shell prompt. Defaults to ``"$ "``.
        quit: Union[str, Iterable[str]]
            String or list of strings that will cause the shell to exit and this method to return.
            Defaults to ``["q", "quit"]``.
        `**kwargs`
            Get passed along to :meth:`__call__` (and, subsequently :meth:`parse_args`).
        """
        if os.name == "posix":
            print("Interactive shell. Press Ctrl-D to exit.")
        else:  # Windows
            print("Interactive shell. Press Ctrl-Z followed by Enter to exit.")

        if quit is None:
            quit = ["q", "quit"]
        if isinstance(quit, str):
            quit = [quit]

        kwargs.setdefault("exit_on_error", False)

        while True:
            try:
                user_input = input(prompt)
            except EOFError:
                break

            split_user_input = normalize_tokens(user_input)
            if not split_user_input:
                continue
            if split_user_input[0] in quit:
                break

            try:
                self(split_user_input, **kwargs)
            except CycloptsError:
                # Upstream __call__->parse_args already printed the error
                pass
            except Exception as e:
                print(e)
