import importlib
import inspect
import os
import sys
import traceback
from contextlib import suppress
from copy import copy
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import attrs
from attrs import define, field
from rich.console import Console

if sys.version_info < (3, 10):
    from importlib_metadata import PackageNotFoundError
    from importlib_metadata import version as importlib_metadata_version
else:  # pragma: no cover
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as importlib_metadata_version

from cyclopts.bind import create_bound_arguments, normalize_tokens
from cyclopts.coercion import optional_to_tuple_converter, to_list_converter, to_tuple_converter
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    InvalidCommandError,
    UnusedCliTokensError,
    ValidationError,
    format_cyclopts_error,
)
from cyclopts.group import Group, to_group_converter
from cyclopts.group_extractors import groups_from_app, inverse_groups_from_app
from cyclopts.help import (
    create_panel_table_commands,
    format_command_rows,
    format_doc,
    format_group_parameters,
    format_usage,
)
from cyclopts.parameter import Parameter, validate_command
from cyclopts.protocols import Dispatcher
from cyclopts.resolve import ResolvedCommand

with suppress(ImportError):
    # By importing, makes things like the arrow-keys work.
    import readline  # Not available on windows


def _format_name(name: str):
    return name.lower().replace("_", "-").strip("-")


class _CannotDeriveCallingModuleNameError(Exception):
    pass


def _get_root_module_name():
    """Get the calling package name from the call-stack."""
    for elem in inspect.stack():
        module = inspect.getmodule(elem.frame)
        if module is None:
            continue
        root_module_name = module.__name__.split(".")[0]
        if root_module_name == "cyclopts":
            continue
        return root_module_name

    raise _CannotDeriveCallingModuleNameError  # pragma: no cover


def _default_version(default="0.0.0") -> str:
    """Attempts to get the calling code's version.

    Returns
    -------
    version: str
        ``default`` if it cannot determine version.
    """
    try:
        root_module_name = _get_root_module_name()
    except _CannotDeriveCallingModuleNameError:  # pragma: no cover
        return default

    # Attempt to get the Distribution Package’s version number.
    try:
        return importlib_metadata_version(root_module_name)
    except PackageNotFoundError:
        pass

    # Attempt packagename.__version__
    # Not sure if this is redundant with ``importlib.metadata``,
    # but there's no real harm in checking.
    try:
        module = importlib.import_module(root_module_name)
        return module.__version__
    except (ImportError, AttributeError):
        pass

    # Final fallback
    return default


def _validate_default_command(x):
    if isinstance(x, App):
        raise TypeError("Cannot register a sub-App to default.")
    return x


def _combined_meta_command_mapping(app):
    """Return a copied and combined mapping containing app and meta-app commands."""
    command_mapping = copy(app._commands)
    while (app := app._meta) and app._commands:
        command_mapping.update(app._commands)
    return command_mapping


def _remove_duplicates(seq: List) -> List:
    seen, out = set(), []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@define
class App:
    _name: Optional[Tuple[str, ...]] = field(default=None, alias="name", converter=optional_to_tuple_converter)

    help: Optional[str] = field(default=None)

    # Everything below must be kw_only

    default_command: Optional[Callable] = field(default=None, converter=_validate_default_command, kw_only=True)
    _default_parameter: Optional[Parameter] = field(default=None, alias="default_parameter", kw_only=True)

    version: Union[None, str, Callable] = field(factory=_default_version, kw_only=True)
    version_flags: Tuple[str, ...] = field(
        default=["--version"],
        on_setattr=attrs.setters.frozen,
        converter=to_tuple_converter,
        kw_only=True,
    )

    help_flags: Tuple[str, ...] = field(
        default=["--help", "-h"],
        on_setattr=attrs.setters.frozen,
        converter=to_tuple_converter,
        kw_only=True,
    )

    group: Tuple[Union[Group, str], ...] = field(default=None, converter=to_tuple_converter, kw_only=True)

    group_arguments: Group = field(
        default=None,
        converter=to_group_converter(Group.create_default_arguments()),
        kw_only=True,
    )
    group_parameters: Group = field(
        default=None,
        converter=to_group_converter(Group.create_default_parameters()),
        kw_only=True,
    )
    group_commands: Group = field(
        default=None,
        converter=to_group_converter(Group.create_default_commands()),
        kw_only=True,
    )

    converter: Optional[Callable] = field(default=None, kw_only=True)
    validator: List[Callable] = field(default=None, converter=to_list_converter, kw_only=True)

    ######################
    # Private Attributes #
    ######################
    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, "App"] = field(init=False, factory=dict)

    _parents: List["App"] = field(init=False, factory=list)

    _meta: "App" = field(init=False, default=None)
    _meta_parent: "App" = field(init=False, default=None)

    def __attrs_post_init__(self):
        if self.help_flags:
            self.command(
                self.help_print,
                name=self.help_flags,
                help_flags=[],
                version_flags=[],
                help="Display this message and exit.",
            )
        if self.version_flags:
            self.command(
                self.version_print,
                name=self.version_flags,
                help_flags=[],
                version_flags=[],
                help="Display application version.",
            )

    ###########
    # Methods #
    ###########
    @property
    def default_parameter(self) -> Parameter:
        """Parameter value defaults for all functions' Parameters.

        The ``default_parameter`` is treated as a hierarchical configuration, inheriting from parenting :class:`App` s.

        Usually, an :class:`App` has at most one parent.
        In the event of multiple parents, they are evaluated in reverse-registered order,
        where each ``default_parameter`` attributes overwrites the previous.
        I.e. the first registered parent has the highest-priority of the parents.
        The specified ``default_parameter`` for this :class:`App` object has higher priority over parents.
        """
        return Parameter.combine(*(x.default_parameter for x in reversed(self._parents)), self._default_parameter)

    @default_parameter.setter
    def default_parameter(self, value: Optional[Parameter]):
        self._default_parameter = value

    @property
    def name(self) -> Tuple[str, ...]:
        """Application name(s). Dynamically derived if not previously set."""
        if self._name:
            return self._name
        elif self.default_command is None:
            name = Path(sys.argv[0]).name
            if name == "__main__.py":
                name = _get_root_module_name()
            return (name,)
        else:
            return (_format_name(self.default_command.__name__),)

    @property
    def help_(self) -> str:
        if self.help is not None:
            return self.help
        elif self.default_command is None:
            # Try and fallback to a meta-app docstring.
            if self._meta is None:
                return ""
            else:
                return self.meta.help_
        elif self.default_command.__doc__ is None:
            return ""
        else:
            return self.default_command.__doc__

    def version_print(self) -> None:
        """Print the application version."""
        print(self.version() if callable(self.version) else self.version)

    def __getitem__(self, key: str) -> "App":
        """Get the subapp from a command string.

        All commands get registered to Cyclopts as subapps.
        The actual function handler is at ``app[key].default_command``.
        """
        if self._meta:
            with suppress(KeyError):
                return self.meta[key]
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
                group_arguments=Group("Session Arguments"),
                group_parameters=Group("Session Parameters"),
            )
            self._meta._meta_parent = self
        return self._meta

    def _parse_command_chain(self, tokens):
        command_chain = []
        app = self
        apps = [app]
        unused_tokens = tokens

        command_mapping = _combined_meta_command_mapping(app)

        for i, token in enumerate(tokens):
            if token in self.help_flags:
                # app = self
                break
            try:
                app = command_mapping[token]
                apps.append(app)
                unused_tokens = tokens[i + 1 :]
            except KeyError:
                break
            command_chain.append(token)
            command_mapping = _combined_meta_command_mapping(app)

        return command_chain, apps, unused_tokens

    def command(
        self,
        obj: Optional[Callable] = None,
        name: Union[None, str, Iterable[str]] = None,
        **kwargs,
    ) -> Callable:
        """Decorator to register a function as a CLI command.

        Parameters
        ----------
        obj: Optional[Callable]
            Function or :class:`App` to be registered as a command.
        name: Union[None, str, Iterable[str]]
            Name(s) to register the ``obj`` to.
            If not provided, defaults to:

            * If registering an :class:`App`, then the app's name.
            * If registering a function, then the function's name.
        `**kwargs`
            Any argument that :class:`App` can take.
        """
        if obj is None:  # Called ``@app.command(...)``
            return partial(self.command, name=name, **kwargs)

        if isinstance(obj, App):
            app = obj

            if app._name is None and name is None:
                raise ValueError("Sub-app MUST have a name specified.")

            if kwargs:
                raise ValueError("Cannot supplied additional configuration when registering a sub-App.")
        else:
            validate_command(obj)
            kwargs.setdefault("help_flags", [])
            kwargs.setdefault("version_flags", [])
            app = App(default_command=obj, **kwargs)
            # app.name will default to name of the function ``obj``.

        if name is None:
            name = app.name
        else:
            app._name = name

        for n in to_tuple_converter(name):
            if n in self:
                raise CommandCollisionError(f'Command "{n}" already registered.')

            # Warning: app._name may not align with command name
            self._commands[n] = app

        app._parents.append(self)

        return obj

    def default(
        self,
        obj=None,
        *,
        converter=None,
        validator=None,
    ):
        """Decorator to register a function as the default action handler."""
        if obj is None:  # Called ``@app.default_command(...)``
            return partial(self.default, converter=converter, validator=validator)

        if isinstance(obj, App):  # Registering a sub-App
            raise TypeError("Cannot register a sub-App to default.")

        if self.default_command is not None:
            raise CommandCollisionError(f"Default command previously set to {self.default_command}.")

        validate_command(obj)
        self.default_command = obj
        if converter:
            self.converter = converter
        if validator:
            self.validator = validator
        return obj

    def parse_known_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional[Console] = None,
    ) -> Tuple[Callable, inspect.BoundArguments, List[str]]:
        """Interpret arguments into a function, ``BoundArguments``, and any remaining unknown tokens.

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

        command_chain, apps, unused_tokens = self._parse_command_chain(tokens)
        app = apps[-1]

        try:
            parent_app = apps[-2]
        except IndexError:
            parent_app = None

        try:
            if app.default_command:
                command = app.default_command
                resolved_command = ResolvedCommand(
                    command,
                    app.default_parameter,
                    app.group_arguments,
                    app.group_parameters,
                    parse_docstring=False,
                )
                # We want the resolved group that ``app`` belongs to.
                if parent_app is None:
                    command_groups = []
                else:
                    command_groups = next(x for x in inverse_groups_from_app(parent_app) if x[0] is app)[1]

                bound, unused_tokens = create_bound_arguments(resolved_command, unused_tokens)
                try:
                    if app.converter:
                        bound.arguments = app.converter(**bound.arguments)
                    for command_group in command_groups:
                        if command_group.converter:
                            bound.arguments = command_group.converter(**bound.arguments)
                    for validator in app.validator:
                        validator(**bound.arguments)
                    for command_group in command_groups:
                        for validator in command_group.validator:
                            validator(**bound.arguments)
                except (AssertionError, ValueError, TypeError) as e:
                    new_exception = ValidationError(value=e.args[0])
                    raise new_exception from e

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
        """Interpret arguments into a function and ``BoundArguments``.

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
            If not provided, defaults to ``sys.argv``.
        """
        tokens = normalize_tokens(tokens)

        if console is None:
            console = Console()

        command_chain, apps, _ = self._parse_command_chain(tokens)
        app = apps[-1]

        # Print the:
        #    my-app command COMMAND [ARGS] [OPTIONS]
        console.print(format_usage(self, command_chain))

        # Print the App/Command's Doc String.
        console.print(format_doc(self, app))

        def walk_apps():
            # Iterates from deepest to shallowest meta-apps
            meta_list = []  # shallowest to deepest
            meta_list.append(app)
            meta = app
            while (meta := meta._meta) and meta.default_command:
                meta_list.append(meta)
            yield from reversed(meta_list)

        command_rows, command_descriptions = {}, {}
        for subapp in walk_apps():
            # Print default_command argument/parameter groups
            if subapp.default_command:
                command = ResolvedCommand(
                    subapp.default_command,
                    subapp.default_parameter,
                    subapp.group_arguments,
                    subapp.group_parameters,
                )
                for group, iparams in command.groups_iparams:
                    if not group.show:
                        continue
                    cparams = [command.iparam_to_cparam[x] for x in iparams]
                    console.print(format_group_parameters(group, iparams, cparams))

            # Print command groups
            for group, elements in groups_from_app(subapp):
                if not group.show:
                    continue

                command_descriptions.setdefault(group.name, group.help)
                command_rows.setdefault(group.name, [])
                command_rows[group.name].extend(format_command_rows(elements))

        # Rely on dictionary insertion order for panel-order.
        for title, rows in command_rows.items():
            if not rows:
                continue
            panel, table, text = create_panel_table_commands(title=title)
            description = command_descriptions[title]
            if description:
                text.append(description + "\n\n")
            rows = _remove_duplicates(rows)
            rows.sort(key=lambda x: (x[0].startswith("-"), x[0]))  # sort by command name
            for row in rows:
                table.add_row(*row)
            console.print(panel)

    def interactive_shell(
        self,
        prompt: str = "$ ",
        quit: Union[None, str, Iterable[str]] = None,
        dispatcher: Optional[Dispatcher] = None,
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
        dispatcher: Optional[Dispatcher]
            Optional function that subsequently invokes the command.
            The ``dispatcher`` function must have signature:

            .. code-block:: python

                def dispatcher(command: Callable, bound: inspect.BoundArguments) -> Any:
                    return command(*bound.args, **bound.kwargs)

            The above is the default dispatcher implementation.
        `**kwargs`
            Get passed along to :meth:`parse_args`.
        """
        if os.name == "posix":
            print("Interactive shell. Press Ctrl-D to exit.")
        else:  # Windows
            print("Interactive shell. Press Ctrl-Z followed by Enter to exit.")

        if quit is None:
            quit = ["q", "quit"]
        if isinstance(quit, str):
            quit = [quit]

        def default_dispatcher(command, bound):
            return command(*bound.args, **bound.kwargs)

        if dispatcher is None:
            dispatcher = default_dispatcher

        kwargs.setdefault("exit_on_error", False)

        while True:
            try:
                user_input = input(prompt)
            except EOFError:
                break

            tokens = normalize_tokens(user_input)
            if not tokens:
                continue
            if tokens[0] in quit:
                break

            try:
                command, bound = self.parse_args(tokens, **kwargs)
                dispatcher(command, bound)
            except CycloptsError:
                # Upstream ``parse_args`` already printed the error
                pass
            except Exception:
                print(traceback.format_exc())

    def __repr__(self):
        """Only shows non-default values."""
        non_defaults = {}
        for a in self.__attrs_attrs__:  # pyright: ignore[reportGeneralTypeIssues]
            if not a.init:
                continue
            v = getattr(self, a.name)
            if v != a.default:
                non_defaults[a.alias] = v

        signature = ", ".join(f"{k}={v!r}" for k, v in non_defaults.items())
        return f"{type(self).__name__}({signature})"
