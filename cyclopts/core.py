import inspect
import os
import sys
import traceback
from contextlib import suppress
from copy import copy
from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from attrs import define, field

import cyclopts.utils
from cyclopts.bind import create_bound_arguments, normalize_tokens
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    InvalidCommandError,
    UnusedCliTokensError,
    ValidationError,
    format_cyclopts_error,
)
from cyclopts.group import Group, GroupConverter, sort_groups
from cyclopts.group_extractors import groups_from_app, inverse_groups_from_app
from cyclopts.help import (
    HelpPanel,
    create_parameter_help_panel,
    format_command_entries,
    format_doc,
    format_usage,
    resolve_help_format,
)
from cyclopts.parameter import Parameter, validate_command
from cyclopts.protocols import Dispatcher
from cyclopts.resolve import ResolvedCommand
from cyclopts.utils import (
    default_name_transform,
    optional_to_tuple_converter,
    to_list_converter,
    to_tuple_converter,
)

T = TypeVar("T", bound=Callable)


if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


with suppress(ImportError):
    # By importing, makes things like the arrow-keys work.
    import readline  # Not available on windows

if TYPE_CHECKING:
    from rich.console import Console


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
    import importlib

    if sys.version_info < (3, 10):  # pragma: no cover
        from importlib_metadata import PackageNotFoundError
        from importlib_metadata import version as importlib_metadata_version
    else:  # pragma: no cover
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as importlib_metadata_version

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


def _get_command_groups(parent_app, child_app):
    """Extract out the command groups from the ``parent_app`` for a given ``child_app``."""
    return next(x for x in inverse_groups_from_app(parent_app) if x[0] is child_app)[1]


def resolve_default_parameter_from_apps(apps) -> Parameter:
    """The default_parameter resolution depends on the parent-child path traversed."""
    cparams = []
    for parent_app, child_app in zip(apps[:-1], apps[1:]):
        # child_app could be a command of parent_app.meta
        if parent_app._meta and child_app in parent_app._meta._commands.values():
            cparams = []  # meta-apps do NOT inherit from their parenting app.
            parent_app = parent_app._meta

        groups = _get_command_groups(parent_app, child_app)
        cparams.extend([group.default_parameter for group in groups])
        cparams.append(parent_app.default_parameter)

    cparams.append(apps[-1].default_parameter)

    return Parameter.combine(*cparams)


def walk_metas(app):
    # Iterates from deepest to shallowest meta-apps
    meta_list = [app]  # shallowest to deepest
    meta = app
    while (meta := meta._meta) and meta.default_command:
        meta_list.append(meta)
    yield from reversed(meta_list)


@define
class App:
    # This can ONLY ever be Tuple[str, ...] due to converter.
    # The other types is to make mypy happy for Cyclopts users.
    _name: Union[None, str, Tuple[str, ...]] = field(default=None, alias="name", converter=optional_to_tuple_converter)

    _help: Optional[str] = field(default=None, alias="help")

    usage: Optional[str] = field(default=None)

    # Everything below must be kw_only

    default_command: Optional[Callable] = field(default=None, converter=_validate_default_command, kw_only=True)
    default_parameter: Optional[Parameter] = field(default=None, kw_only=True)

    version: Union[None, str, Callable] = field(factory=_default_version, kw_only=True)
    # This can ONLY ever be a Tuple[str, ...]
    _version_flags: Union[str, Iterable[str]] = field(
        default=["--version"],
        converter=to_tuple_converter,
        alias="version_flags",
        kw_only=True,
    )

    show: bool = field(default=True, kw_only=True)

    console: Optional["Console"] = field(default=None, kw_only=True)

    # This can ONLY ever be a Tuple[str, ...]
    _help_flags: Union[str, Iterable[str]] = field(
        default=["--help", "-h"],
        converter=to_tuple_converter,
        alias="help_flags",
        kw_only=True,
    )
    help_format: Optional[
        Literal[
            "markdown",
            "md",
            "plaintext",
            "restructuredtext",
            "rst",
            "rich",
        ]
    ] = field(default=None, kw_only=True)

    # This can ONLY ever be Tuple[Union[Group, str], ...] due to converter.
    # The other types is to make mypy happy for Cyclopts users.
    group: Union[Group, str, Tuple[Union[Group, str], ...]] = field(
        default=None, converter=to_tuple_converter, kw_only=True
    )

    group_arguments: Group = field(
        default=None,
        converter=GroupConverter(Group.create_default_arguments()),
        kw_only=True,
    )
    group_parameters: Group = field(
        default=None,
        converter=GroupConverter(Group.create_default_parameters()),
        kw_only=True,
    )
    group_commands: Group = field(
        default=None,
        converter=GroupConverter(Group.create_default_commands()),
        kw_only=True,
    )

    converter: Optional[Callable] = field(default=None, kw_only=True)
    validator: List[Callable] = field(default=None, converter=to_list_converter, kw_only=True)

    _name_transform: Optional[Callable[[str], str]] = field(
        default=None,
        alias="name_transform",
        kw_only=True,
    )

    ######################
    # Private Attributes #
    ######################
    # Maps CLI-name of a command to a function handle.
    _commands: Dict[str, "App"] = field(init=False, factory=dict)

    _parents: List["App"] = field(init=False, factory=list)

    _meta: "App" = field(init=False, default=None)
    _meta_parent: "App" = field(init=False, default=None)

    def __attrs_post_init__(self):
        # Trigger the setters
        self.help_flags = self._help_flags
        self.version_flags = self._version_flags

    ###########
    # Methods #
    ###########
    def _delete_commands(self, commands: Iterable[str], default=None):
        """Safely delete commands.

        Will **not** raise an exception if command(s) do not exist.

        Parameters
        ----------
        commands: Iterable[str, ...]
            Strings of commands to delete.
        """
        # Remove all the old version-flag commands.
        for command in commands:
            with suppress(KeyError):
                if default:
                    if self[command].default == self.version_print:
                        del self[command]
                else:
                    del self[command]

    @property
    def version_flags(self):
        return self._version_flags

    @version_flags.setter
    def version_flags(self, value):
        self._version_flags = value
        self._delete_commands(self._version_flags, default=self.version_print)
        if self._version_flags:
            self.command(
                self.version_print,
                name=self._version_flags,
                help_flags=[],
                version_flags=[],
                help="Display application version.",
            )

    @property
    def help_flags(self):
        return self._help_flags

    @help_flags.setter
    def help_flags(self, value):
        self._help_flags = value
        self._delete_commands(self._help_flags, default=self.help_print)
        if self._help_flags:
            self.command(
                self.help_print,
                name=self._help_flags,
                help_flags=[],
                version_flags=[],
                help="Display this message and exit.",
            )

    @property
    def name(self) -> Tuple[str, ...]:
        """Application name(s). Dynamically derived if not previously set."""
        if self._name:
            return self._name  # pyright: ignore[reportReturnType]
        elif self.default_command is None:
            name = Path(sys.argv[0]).name
            if name == "__main__.py":
                name = _get_root_module_name()
            return (name,)
        else:
            return (self.name_transform(self.default_command.__name__),)

    @property
    def help(self) -> str:
        if self._help is not None:
            return self._help
        elif self.default_command is None:
            # Try and fallback to a meta-app docstring.
            if self._meta is None:
                return ""
            else:
                return self.meta.help
        elif self.default_command.__doc__ is None:
            return ""
        else:
            return self.default_command.__doc__

    @help.setter
    def help(self, value):
        self._help = value

    @property
    def name_transform(self):
        return self._name_transform if self._name_transform else default_name_transform

    @name_transform.setter
    def name_transform(self, value):
        self._name_transform = value

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

    def __delitem__(self, key: str):
        del self._commands[key]

    def __contains__(self, k: str) -> bool:
        if k in self._commands:
            return True
        if self._meta_parent:
            return k in self._meta_parent
        return False

    def __iter__(self) -> Iterator[str]:
        """Iterate over command & meta command names."""
        for k in self._commands:
            yield k
        if self._meta_parent:
            for k in self._meta_parent:
                yield k

    @property
    def meta(self) -> "App":
        if self._meta is None:
            self._meta = type(self)(
                help_flags=copy(self.help_flags),
                version_flags=copy(self.version_flags),
                group_commands=copy(self.group_commands),
                group_arguments=copy(self.group_arguments),
                group_parameters=copy(self.group_parameters),
            )
            self._meta._meta_parent = self
        return self._meta

    def parse_commands(self, tokens: Union[None, str, Iterable[str]] = None):
        """Extract out the command tokens from a command.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``

        Returns
        -------
        List[str]
            Tokens that are interpreted as a valid command chain.
        List[App]
            The associated :class:`App` object with each of those tokens.
        List[str]
            The remaining non-command tokens.
        """
        tokens = normalize_tokens(tokens)

        command_chain = []
        app = self
        apps = [app]
        unused_tokens = tokens

        command_mapping = _combined_meta_command_mapping(app)

        for i, token in enumerate(tokens):
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
        obj: Optional[T] = None,
        name: Union[None, str, Iterable[str]] = None,
        **kwargs,
    ) -> T:
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
            return partial(self.command, name=name, **kwargs)  # pyright: ignore[reportReturnType]

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
            if "group_commands" not in kwargs:
                kwargs["group_commands"] = copy(self.group_commands)
            if "group_parameters" not in kwargs:
                kwargs["group_parameters"] = copy(self.group_parameters)
            if "group_arguments" not in kwargs:
                kwargs["group_arguments"] = copy(self.group_arguments)
            app = App(default_command=obj, **kwargs)
            # app.name is handled below

        if app._name_transform is None:
            app.name_transform = self.name_transform

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

        return obj  # pyright: ignore[reportReturnType]

    def default(
        self,
        obj: Optional[T] = None,
        *,
        converter=None,
        validator=None,
    ) -> T:
        """Decorator to register a function as the default action handler."""
        if obj is None:  # Called ``@app.default_command(...)``
            return partial(self.default, converter=converter, validator=validator)  # pyright: ignore[reportReturnType]

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
        console: Optional["Console"] = None,
    ) -> Tuple[Callable, inspect.BoundArguments, List[str]]:
        """Interpret arguments into a function, :class:`~inspect.BoundArguments`, and any remaining unknown tokens.

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

        meta_parent = self

        command_chain, apps, unused_tokens = self.parse_commands(tokens)
        command_app = apps[-1]

        try:
            parent_app = apps[-2]
        except IndexError:
            parent_app = None

        # Special flags (help/version) get intercepted by the root app.
        # Special flags are allows to be **anywhere** in the token stream.

        for help_flag in self.help_flags:
            try:
                help_flag_index = tokens.index(help_flag)
                break
            except ValueError:
                pass
        else:
            help_flag_index = None

        if help_flag_index is not None:
            tokens.pop(help_flag_index)
            command = self.help_print
            while meta_parent := meta_parent._meta_parent:
                command = meta_parent.help_print
            bound = cyclopts.utils.signature(command).bind(tokens, console=console)
            unused_tokens = []
        elif any(flag in tokens for flag in self.version_flags):
            # Version
            command = self.version_print
            while meta_parent := meta_parent._meta_parent:
                command = meta_parent.version_print
            bound = cyclopts.utils.signature(command).bind()
            unused_tokens = []
        else:
            try:
                if command_app.default_command:
                    command = command_app.default_command
                    resolved_command = self._resolve_command(
                        tokens,
                        parse_docstring=False,
                    )
                    # We want the resolved group that ``app`` belongs to.
                    if parent_app is None:
                        command_groups = []
                    else:
                        command_groups = _get_command_groups(parent_app, command_app)

                    bound, unused_tokens = create_bound_arguments(resolved_command, unused_tokens)
                    try:
                        if command_app.converter:
                            bound.arguments = command_app.converter(**bound.arguments)
                        for command_group in command_groups:
                            if command_group.converter:
                                bound.arguments = command_group.converter(**bound.arguments)
                        for validator in command_app.validator:
                            validator(**bound.arguments)
                        for command_group in command_groups:
                            for validator in command_group.validator:  # pyright: ignore
                                validator(**bound.arguments)
                    except (AssertionError, ValueError, TypeError) as e:
                        raise ValidationError(
                            value=e.args[0] if e.args else "",
                            group=command_group,  # pyright: ignore[reportPossiblyUnboundVariable]
                        ) from e

                else:
                    if unused_tokens:
                        raise InvalidCommandError(unused_tokens=unused_tokens)
                    else:
                        # Running the application with no arguments and no registered
                        # ``default_command`` will default to ``help_print``.
                        command = self.help_print
                        bound = cyclopts.utils.signature(command).bind(tokens=tokens, console=console)
                        unused_tokens = []
            except CycloptsError as e:
                e.app = command_app
                if command_chain:
                    e.command_chain = command_chain
                if e.console is None:
                    e.console = self._resolve_console(tokens, console)
                raise

        return command, bound, unused_tokens

    def parse_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        verbose: bool = False,
    ) -> Tuple[Callable, inspect.BoundArguments]:
        """Interpret arguments into a function and :class:`~inspect.BoundArguments`.

        Raises
        ------
        UnusedCliTokensError
            If any tokens remain after parsing.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        console: rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
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

        # Normal parsing
        try:
            command, bound, unused_tokens = self.parse_known_args(tokens, console=console)
            if unused_tokens:
                raise UnusedCliTokensError(
                    target=command,
                    unused_tokens=unused_tokens,
                )
        except CycloptsError as e:
            e.verbose = verbose
            e.root_input_tokens = tokens

            if e.console is None:
                e.console = self._resolve_console(tokens, console)
            if print_error:
                assert e.console
                e.console.print(format_cyclopts_error(e))
            if exit_on_error:
                sys.exit(1)
            raise

        return command, bound

    def __call__(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        verbose: bool = False,
    ):
        """Interprets and executes a command.

        Parameters
        ----------
        tokens : Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        console: rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
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
        return_value: Any
            The value the parsed command handler returns.
        """
        tokens = normalize_tokens(tokens)
        command, bound = self.parse_args(
            tokens,
            console=console,
            print_error=print_error,
            exit_on_error=exit_on_error,
            verbose=verbose,
        )
        try:
            if inspect.iscoroutinefunction(command):
                import asyncio

                return asyncio.run(command(*bound.args, **bound.kwargs))
            else:
                return command(*bound.args, **bound.kwargs)
        except Exception as e:
            try:
                from pydantic import ValidationError as PydanticValidationError
            except ImportError:
                PydanticValidationError = None  # noqa: N806

            if PydanticValidationError is not None and isinstance(e, PydanticValidationError):
                if print_error:
                    console = self._resolve_console(tokens, console)
                    console.print(format_cyclopts_error(e))

                if exit_on_error:
                    sys.exit(1)
            raise

    def _resolve_console(
        self, tokens: Union[None, str, Iterable[str]], console: Optional["Console"] = None
    ) -> "Console":
        if console is not None:
            return console
        _, apps, _ = self.parse_commands(tokens)
        for app in reversed(apps):
            if app.console:
                return app.console
        from rich.console import Console

        return Console()

    def help_print(
        self,
        tokens: Annotated[Union[None, str, Iterable[str]], Parameter(show=False)] = None,
        *,
        console: Annotated[Optional["Console"], Parameter(parse=False)] = None,
    ) -> None:
        """Print the help page.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Tokens to interpret for traversing the application command structure.
            If not provided, defaults to ``sys.argv``.
        console: rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        """
        tokens = normalize_tokens(tokens)

        command_chain, apps, _ = self.parse_commands(tokens)
        executing_app = apps[-1]

        console = self._resolve_console(tokens, console)

        # Print the:
        #    my-app command COMMAND [ARGS] [OPTIONS]
        if executing_app.usage is None:
            console.print(format_usage(self, command_chain))
        elif executing_app.usage:  # i.e. skip empty-string.
            console.print(executing_app.usage + "\n")

        # Print the App/Command's Doc String.
        help_format = resolve_help_format(apps)
        console.print(format_doc(self, executing_app, help_format))

        for help_panel in self._assemble_help_panels(tokens, help_format):
            console.print(help_panel)

    def _resolve_command(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        parse_docstring: bool = True,
    ) -> ResolvedCommand:
        _, apps, _ = self.parse_commands(tokens)

        if not apps[-1].default_command:
            raise InvalidCommandError

        resolved_command = ResolvedCommand(
            apps[-1].default_command,
            resolve_default_parameter_from_apps(apps),
            apps[-1].group_arguments,
            apps[-1].group_parameters,
            parse_docstring=parse_docstring,
        )
        return resolved_command

    def _assemble_help_panels(
        self,
        tokens: Union[None, str, Iterable[str]],
        help_format,
    ) -> List[HelpPanel]:
        from rich.console import Group as RichGroup
        from rich.console import NewLine

        _, apps, _ = self.parse_commands(tokens)

        help_format = resolve_help_format(apps)

        panels: Dict[str, Tuple[Group, HelpPanel]] = {}
        # Handle commands first; there's an off chance they may be "upgraded"
        # to an argument/parameter panel.
        for subapp in walk_metas(apps[-1]):
            # Handle Commands
            for group, elements in groups_from_app(subapp):
                if not group.show:
                    continue

                try:
                    _, command_panel = panels[group.name]
                except KeyError:
                    command_panel = HelpPanel(
                        format="command",
                        title=group.name,
                    )
                    panels[group.name] = (group, command_panel)

                if group.help:
                    import cyclopts.help

                    group_help = cyclopts.help._format(group.help, format=help_format)

                    if command_panel.description:
                        command_panel.description = RichGroup(command_panel.description, NewLine(), group_help)
                    else:
                        command_panel.description = group_help

                command_panel.entries.extend(format_command_entries(elements, format=help_format))

        # Handle Arguments/Parameters
        for subapp in walk_metas(apps[-1]):
            if not subapp.default_command:
                continue
            command = ResolvedCommand(
                subapp.default_command,
                resolve_default_parameter_from_apps(apps),
                subapp.group_arguments,
                subapp.group_parameters,
            )
            for group, iparams in command.groups_iparams:
                if not group.show:
                    continue
                cparams = [command.iparam_to_cparam[x] for x in iparams]
                try:
                    _, existing_panel = panels[group.name]
                except KeyError:
                    existing_panel = None
                new_panel = create_parameter_help_panel(group, iparams, cparams, help_format)

                if existing_panel:
                    # An imperfect merging process
                    existing_panel.format = "parameter"
                    existing_panel.entries = new_panel.entries + existing_panel.entries  # Commands go last
                    if new_panel.description:
                        if existing_panel.description:
                            existing_panel.description = RichGroup(
                                existing_panel.description, NewLine(), new_panel.description
                            )
                        else:
                            existing_panel.description = new_panel.description
                else:
                    panels[group.name] = (group, new_panel)

        groups = [x[0] for x in panels.values()]
        help_panels = [x[1] for x in panels.values()]

        out = []
        for help_panel in sort_groups(groups, help_panels)[1]:
            help_panel.remove_duplicates()
            if help_panel.format == "command":
                # don't sort format == "parameter" because order may matter there!
                help_panel.sort()
            out.append(help_panel)
        return out

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
        for a in self.__attrs_attrs__:  # pyright: ignore[reportAttributeAccessIssue]
            if not a.init:
                continue
            v = getattr(self, a.name)
            # Compare types first because of some weird attribute issues.
            if type(v) != type(a.default) or v != a.default:  # noqa: E721
                non_defaults[a.alias] = v

        signature = ", ".join(f"{k}={v!r}" for k, v in non_defaults.items())
        return f"{type(self).__name__}({signature})"
