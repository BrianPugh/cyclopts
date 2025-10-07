import importlib
import inspect
import os
import sys
import traceback
from collections.abc import Callable, Coroutine, Iterable, Iterator, Sequence
from contextlib import suppress
from copy import copy
from enum import Enum
from functools import lru_cache, partial
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

from attrs import Factory, define, field

from cyclopts.annotations import resolve_annotated
from cyclopts.app_stack import AppStack
from cyclopts.argument import ArgumentCollection
from cyclopts.bind import create_bound_arguments, is_option_like, normalize_tokens
from cyclopts.config._env import Env
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    UnknownCommandError,
    UnknownOptionError,
    UnusedCliTokensError,
    ValidationError,
)
from cyclopts.group import Group, sort_groups
from cyclopts.group_extractors import groups_from_app
from cyclopts.panel import CycloptsPanel
from cyclopts.parameter import Parameter, validate_command
from cyclopts.protocols import Dispatcher
from cyclopts.token import Token
from cyclopts.utils import (
    UNSET,
    default_name_transform,
    help_formatter_converter,
    optional_to_tuple_converter,
    sort_key_converter,
    to_list_converter,
    to_tuple_converter,
)

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import assert_never
else:  # pragma: no cover
    from typing import assert_never

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as importlib_metadata_version

with suppress(ImportError):
    # By importing, makes things like the arrow-keys work.
    # Not available on windows
    import readline  # noqa: F401

if TYPE_CHECKING:
    from rich.console import Console

    from cyclopts.docs.types import DocFormat
    from cyclopts.help import HelpPanel
    from cyclopts.help.protocols import HelpFormatter

T = TypeVar("T", bound=Callable[..., Any])
V = TypeVar("V")

_DEFAULT_FORMAT = "markdown"


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


def _validate_default_command(x):
    if isinstance(x, App):
        raise TypeError("Cannot register a sub-App to default.")
    return x


def _get_version_command(app):
    if callable(app.version) and inspect.iscoroutinefunction(app.version):
        return app._version_print_async
    else:
        return app.version_print


def _combined_meta_command_mapping(
    app: Optional["App"], recurse_meta=True, recurse_parent_meta=True
) -> dict[str, "App"]:
    """Return a mapping of command names to Apps, including meta app commands.

    Parameters
    ----------
    app : App | None
        The app to get commands from.
    recurse_meta : bool
        If True, include commands from the app's meta.
    recurse_parent_meta : bool
        If True, include commands from parent meta apps.

    Returns
    -------
    dict[str, App]
        Mapping of command names to :class:`App` s.
    """
    if app is None:
        return {}
    command_mapping = copy(app._commands)
    if recurse_meta and app._meta:
        command_mapping.update(_combined_meta_command_mapping(app._meta))
    if recurse_parent_meta and app._meta_parent:
        meta_parent_commands = _combined_meta_command_mapping(app._meta_parent, recurse_meta=False)
        command_mapping.update(meta_parent_commands)
    return command_mapping


def _run_maybe_async_command(
    command: Callable,
    bound: inspect.BoundArguments | None = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
):
    """Run a command, handling both sync and async cases.

    If the command is async, an async context will be created to run it.

    Parameters
    ----------
    command : Callable
        The command to execute.
    bound : inspect.BoundArguments | None
        Bound arguments for the command. If None, command is called with no arguments.
    backend : Literal["asyncio", "trio"]
        The async backend to use if the command is async.

    Returns
    -------
    return_value: Any
        The value the command function returns.
    """
    if not inspect.iscoroutinefunction(command):
        # Synchronous command
        if bound is None:
            return command()
        else:
            return command(*bound.args, **bound.kwargs)

    # Async command - create event loop
    # We don't use anyio to avoid the dependency for non-async users.
    # anyio can auto-select the backend when you're already in an async context,
    # but here we're creating the top-level event loop & must select ourselves.
    if backend == "asyncio":
        import asyncio

        if bound is None:
            return asyncio.run(command())
        else:
            return asyncio.run(command(*bound.args, **bound.kwargs))
    elif backend == "trio":
        import trio

        if bound is None:
            return trio.run(command)
        else:
            return trio.run(partial(command, *bound.args, **bound.kwargs))
    else:  # pragma: no cover
        assert_never(backend)


def _walk_metas(app: "App"):
    """Typically the result looks like [app] or [meta_app, app].

    Iterates from deepest to shallowest meta-app (and app).
    """
    meta_list = [app]  # shallowest to deepest
    meta = app
    while (meta := meta._meta) and meta.default_command:
        meta_list.append(meta)
    yield from reversed(meta_list)


def _group_converter(input_value: None | str | Group) -> Group | None:
    if input_value is None:
        return None
    elif isinstance(input_value, str):
        return Group(input_value)
    elif isinstance(input_value, Group):
        return input_value
    else:
        raise TypeError


@define
class App:
    # This can ONLY ever be Tuple[str, ...] due to converter.
    # The other types is to make mypy happy for Cyclopts users.
    _name: None | str | tuple[str, ...] = field(default=None, alias="name", converter=optional_to_tuple_converter)

    _help: str | None = field(default=None, alias="help")

    usage: str | None = field(default=None)

    # Everything below must be kw_only

    alias: None | str | tuple[str, ...] = field(
        default=None,
        converter=to_tuple_converter,
        kw_only=True,
    )

    default_command: Callable[..., Any] | None = field(default=None, converter=_validate_default_command, kw_only=True)
    default_parameter: Parameter | None = field(default=None, kw_only=True)

    # This can ONLY ever be None or Tuple[Callable, ...]
    _config: (
        None
        | Callable[[list["App"], tuple[str, ...], ArgumentCollection], Any]
        | Iterable[Callable[[list["App"], tuple[str, ...], ArgumentCollection], Any]]
    ) = field(
        default=None,
        alias="config",
        converter=optional_to_tuple_converter,
        kw_only=True,
    )

    version: None | str | Callable[..., str] | Callable[..., Coroutine[Any, Any, str]] = field(
        default=None, kw_only=True
    )
    # This can ONLY ever be a Tuple[str, ...]
    _version_flags: str | Iterable[str] = field(
        default=["--version"],
        converter=to_tuple_converter,
        alias="version_flags",
        kw_only=True,
    )

    show: bool = field(default=True, kw_only=True)

    _console: Optional["Console"] = field(default=None, kw_only=True, alias="console")

    # This can ONLY ever be a Tuple[str, ...]
    _help_flags: str | Iterable[str] = field(
        default=["--help", "-h"],
        converter=to_tuple_converter,
        alias="help_flags",
        kw_only=True,
    )
    help_format: Literal["markdown", "md", "plaintext", "restructuredtext", "rst", "rich"] | None = field(
        default=None, kw_only=True
    )
    help_on_error: bool | None = field(default=None, kw_only=True)

    version_format: Literal["markdown", "md", "plaintext", "restructuredtext", "rst", "rich"] | None = field(
        default=None, kw_only=True
    )

    # This can ONLY ever be Tuple[Union[Group, str], ...] due to converter.
    # The other types is to make mypy happy for Cyclopts users.
    group: Group | str | tuple[Group | str, ...] = field(default=None, converter=to_tuple_converter, kw_only=True)

    # This can ONLY ever be a Group or None
    _group_arguments: Group | str | None = field(
        alias="group_arguments",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )
    # This can ONLY ever be a Group or None
    _group_parameters: Group | str | None = field(
        alias="group_parameters",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )
    # This can ONLY ever be a Group or None
    _group_commands: Group | str | None = field(
        alias="group_commands",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )

    validator: list[Callable[..., Any]] = field(default=None, converter=to_list_converter, kw_only=True)

    _name_transform: Callable[[str], str] | None = field(
        default=None,
        alias="name_transform",
        kw_only=True,
    )

    _sort_key: Any = field(
        default=None,
        alias="sort_key",
        converter=sort_key_converter,
        kw_only=True,
    )

    end_of_options_delimiter: str | None = field(default=None, kw_only=True)

    print_error: bool | None = field(default=None, kw_only=True)

    exit_on_error: bool | None = field(default=None, kw_only=True)

    verbose: bool | None = field(default=None, kw_only=True)

    suppress_keyboard_interrupt: bool = field(default=True, kw_only=True)

    backend: Literal["asyncio", "trio"] | None = field(default=None, kw_only=True)

    help_formatter: Union[None, Literal["default", "plain"], "HelpFormatter"] = field(
        default=None, converter=help_formatter_converter, kw_only=True
    )

    ######################
    # Private Attributes #
    ######################
    # `init=False` tells attrs not to include it in the generated __init__

    # Maps CLI-name of a command to a function handle.
    _commands: dict[str, "App"] = field(init=False, factory=dict)

    _meta: Optional["App"] = field(init=False, default=None)
    _meta_parent: Optional["App"] = field(init=False, default=None)

    # We will populate this attribute ourselves after initialization
    _instantiating_module: ModuleType | None = field(init=False, default=None)

    _fallback_console: Optional["Console"] = field(init=False, default=None)

    app_stack: AppStack = field(init=False, default=Factory(AppStack, takes_self=True))

    def __attrs_post_init__(self):
        # Trigger the setters
        self.help_flags = self._help_flags
        self.version_flags = self._version_flags

        # inspect.stack()[2] is needed in attrs class because the call stack is deeper:
        # [0]: __attrs_post_init__
        # [1]: the attrs-generated __init__
        # [2]: the caller who created the instance
        try:
            # self._instantiating_module = inspect.getmodule(inspect.stack()[2])
            self._instantiating_module = inspect.getmodule(sys._getframe(2))
        except IndexError:
            # Fallback in case the stack is not as deep as expected
            self._instantiating_module = None

    ###########
    # Methods #
    ###########
    def _delete_commands(self, commands: Iterable[str]):
        """Safely delete commands.

        Will **not** raise an exception if command(s) do not exist.

        Parameters
        ----------
        commands: Iterable[str, ...]
            Strings of commands to delete.
        """
        # Remove all the old version-flag commands.
        for command in commands:
            try:
                del self[command]
            except KeyError:
                pass

    @property
    def version_flags(self):
        return self._version_flags

    @version_flags.setter
    def version_flags(self, value):
        self._version_flags = value
        self._delete_commands(self._version_flags)
        if self._version_flags:
            self.command(
                self.version_print,
                name=self._version_flags,
                help_flags=[],
                version_flags=[],
                version=self.version,
                help="Display application version.",
            )

    @property
    def help_flags(self):
        return self._help_flags

    @help_flags.setter
    def help_flags(self, value):
        self._help_flags = value
        self._delete_commands(self._help_flags)
        if self._help_flags:
            self.command(
                self.help_print,
                name=self._help_flags,
                help_flags=[],
                version_flags=[],
                version=self.version,
                help="Display this message and exit.",
            )

    @property
    def name(self) -> tuple[str, ...]:
        """Application name(s). Dynamically derived if not previously set."""
        if self._name:
            return self._name + self.alias  # pyright: ignore
        elif self.default_command is None:
            name = Path(sys.argv[0]).name
            if name == "__main__.py":
                name = _get_root_module_name()
            return (name,) + self.alias  # pyright: ignore
        else:
            try:
                func_name = self.default_command.__name__
            except AttributeError:
                # This could happen if default_command is wrapped in a functools.partial
                func_name = self.default_command.func.__name__  # pyright: ignore[reportFunctionMemberAccess]
            return (self.name_transform(func_name),) + self.alias  # pyright: ignore

    @property
    def group_arguments(self):
        if self._group_arguments is None:
            return Group.create_default_arguments()
        return self._group_arguments

    @group_arguments.setter
    def group_arguments(self, value):
        self._group_arguments = value

    @property
    def group_parameters(self):
        if self._group_parameters is None:
            return Group.create_default_parameters()
        return self._group_parameters

    @group_parameters.setter
    def group_parameters(self, value):
        self._group_parameters = value

    @property
    def group_commands(self):
        if self._group_commands is None:
            return Group.create_default_commands()
        return self._group_commands

    @group_commands.setter
    def group_commands(self, value):
        self._group_commands = value

    @property
    def config(self):
        return self.app_stack.resolve("_config")

    @config.setter
    def config(self, value):
        self._config = value

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
        else:
            # Try to handle a potential partial function
            if "functools" in sys.modules:
                from functools import partial

                if isinstance(self.default_command, partial):
                    doc = self.default_command.func.__doc__
                else:
                    doc = self.default_command.__doc__
            else:
                doc = self.default_command.__doc__

            if doc is None:
                return ""
            else:
                return doc

    @help.setter
    def help(self, value):
        self._help = value

    @property
    def name_transform(self):
        return self._name_transform if self._name_transform else default_name_transform

    @name_transform.setter
    def name_transform(self, value):
        self._name_transform = value

    @property
    def sort_key(self):
        return None if self._sort_key is UNSET else self._sort_key

    @sort_key.setter
    def sort_key(self, value):
        self._sort_key = sort_key_converter(value)

    @property
    def _registered_commands(self) -> dict[str, "App"]:
        """Commands that are not help or version commands."""
        out = {}
        for x in self:
            if x in self.help_flags or x in self.version_flags:
                continue
            out[x] = self[x]
        return out

    @property
    def console(self) -> "Console":
        result = self.app_stack.resolve("_console")
        if result is not None:
            return result

        # We always want to return back the same console object,
        # but if someone manually overrides `console`, then
        # we want to return that.
        if self._fallback_console is None:
            from rich.console import Console

            self._fallback_console = Console()

        return self._fallback_console

    @console.setter
    def console(self, console: Optional["Console"]):
        self._console = console

    def _get_fallback_version_string(self, default: str = "0.0.0") -> str:
        """Get the version string with multiple fallback strategies.

        First tries to derive from the instantiating module, then tries to get it
        from the calling code's module, and finally falls back to a default.

        Parameters
        ----------
        default : str
            Default version to use if no version can be determined.

        Returns
        -------
        str
            Version string.
        """
        if self._instantiating_module is not None:
            full_module_name = self._instantiating_module.__name__
            root_module_name = full_module_name.split(".")[0]
            try:
                return importlib_metadata_version(root_module_name)
            except PackageNotFoundError:
                pass

            try:
                return self._instantiating_module.__version__  # type: ignore[attr-defined]
            except AttributeError:
                pass

        try:
            root_module_name = _get_root_module_name()
        except _CannotDeriveCallingModuleNameError:  # pragma: no cover
            return default

        try:
            return importlib_metadata_version(root_module_name)
        except PackageNotFoundError:
            pass

        # Attempt packagename.__version__
        # Not sure if this is redundant with ``importlib.metadata``,
        # but there's no real harm in checking.
        try:
            module = importlib.import_module(root_module_name)
            return module.__version__  # type: ignore[attr-defined]
        except (ImportError, AttributeError):
            pass

        return default

    def _format_and_print_version(self, version_raw: str, console: Optional["Console"]) -> None:
        """Format and print the version string.

        Parameters
        ----------
        version_raw : str
            Raw version string to format and print.
        console : ~rich.console.Console
            Console to print to.
        """
        from cyclopts.help import InlineText

        version_format = self.app_stack.resolve("version_format")
        if version_format is None:
            version_format = self.app_stack.resolve("help_format", fallback=_DEFAULT_FORMAT)
        version_formatted = InlineText.from_format(version_raw, format=version_format)
        (console or self.console).print(version_formatted)

    def version_print(
        self,
        console: Optional["Console"] = None,
    ) -> None:
        """Print the application version.

        Parameters
        ----------
        console: ~rich.console.Console
            Console to print version string to.
            If not provided, follows the resolution order defined in :attr:`App.console`.

        """
        if self.version is not None:
            if callable(self.version):
                # Note: async version callables are handled by _version_print_async
                if inspect.iscoroutinefunction(self.version):
                    raise ValueError("async version handler detected. Use App.run_async within an async context.")
                version_raw = cast(str, self.version())
            else:
                version_raw = self.version
        else:
            version_raw = self._get_fallback_version_string()

        self._format_and_print_version(version_raw, console)

    async def _version_print_async(
        self,
        console: Optional["Console"] = None,
    ) -> None:
        """Async version of version_print for handling async version callables.

        Parameters
        ----------
        console: ~rich.console.Console
            Console to print version string to.
            If not provided, follows the resolution order defined in :attr:`App.console`.

        """
        if self.version is not None:
            if callable(self.version):
                if inspect.iscoroutinefunction(self.version):
                    version_raw = await self.version()
                else:
                    # This should never happen, since if ``self.version`` is callable
                    # and not async, then we would be using ``App.version_print``.
                    # This is only here for completeness.
                    version_raw = cast(str, self.version())
            else:
                version_raw = self.version
        else:
            version_raw = self._get_fallback_version_string()

        self._format_and_print_version(version_raw, console)

    @property
    def subapps(self):
        for k in self:
            yield self[k]

    def __getitem__(self, key: str) -> "App":
        """Get the subapp from a command string.

        All commands get registered to Cyclopts as subapps.
        The actual function handler is at ``app[key].default_command``.

        Example usage:

        .. code-block:: python

            from cyclopts import App

            app = App()
            app.command(App(name="foo"))


            @app["foo"].command
            def bar():
                print("Running bar.")


            app()
        """
        return self._get_item(key)

    def _get_item(self, key, recurse_meta=True) -> "App":
        if recurse_meta and self._meta:
            with suppress(KeyError):
                return self.meta[key]
        if self._meta_parent:
            with suppress(KeyError):
                return self._meta_parent._get_item(key, recurse_meta=False)
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
        """Iterate over command & meta command names.

        Example usage:

        .. code-block:: python

            from cyclopts import App

            app = App()


            @app.command
            def foo():
                pass


            @app.command
            def bar():
                pass


            # help and version flags are treated as commands.
            assert list(app) == ["--help", "-h", "--version", "foo", "bar"]
        """
        commands = list(self._commands)
        yield from commands
        commands = set(commands)
        if self._meta_parent:
            for command in self._meta_parent:
                if command not in commands:
                    yield command

    @property
    def meta(self) -> "App":
        if self._meta is None:
            self._meta = type(self)(
                help_flags=self.help_flags,
                version_flags=self.version_flags,
                group_commands=copy(self._group_commands),
                group_arguments=copy(self._group_arguments),
                group_parameters=copy(self._group_parameters),
            )
            self._meta._meta_parent = self
        return self._meta

    def parse_commands(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        include_parent_meta=True,
    ) -> tuple[tuple[str, ...], tuple["App", ...], list[str]]:
        """Extract out the command tokens from a command.

        You are probably actually looking for :meth:`parse_args`.

        Parameters
        ----------
        tokens: None | str | Iterable[str]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        include_parent_meta: bool
            Controls whether parent meta apps are included in the execution path.

            When True (default):
            - Parent meta apps (i.e. the "normal" app ) are added to the apps list.
            - Meta app options are consumed while parsing commands.
            - Used for getting the inheritance hierarchy.

            When False:
            - Meta app options are treated as regular arguments.
            - Used for getting the execution hierarchy.

            This parameter is primarily for internal use.

        Returns
        -------
        tuple[str, ...]
            Strings that are interpreted as a valid command chain.
        tuple[App, ...]
            The execution path - apps that will be invoked in order.
        list[str]
            The remaining non-command tokens.
        """
        tokens = normalize_tokens(tokens)

        command_chain = []
        app = self
        apps: list[App] = []
        unused_tokens = tokens

        def add_parent_metas(app):
            """If ``app`` is a meta-app, also add it's "normal" app.

            We assume that ``app._meta`` will always invoke the ``app``.
            """
            if not include_parent_meta:
                return
            meta_parents = []
            meta_parent = app
            while (meta_parent := meta_parent._meta_parent) is not None:
                meta_parents.append(meta_parent)
            # The "root" non-meta app gets highest priority (first)
            apps.extend(meta_parents[::-1])

        add_parent_metas(app)
        apps.append(app)
        command_mapping = _combined_meta_command_mapping(app, recurse_parent_meta=include_parent_meta)

        unused_tokens = tokens
        while unused_tokens:
            token = unused_tokens[0]
            try:
                app = command_mapping[token]
            except KeyError:
                # Token is not a command. Try to consume it as a meta app parameter.
                # This is only relevant when ``include_parent_meta==True``, because
                # otherwise it will be handled by the natural parsing process.
                if include_parent_meta:
                    remaining = self._consume_leading_meta_options(apps, unused_tokens)
                    if len(remaining) < len(unused_tokens):
                        # Some meta parameters were consumed, continue looking for commands
                        unused_tokens = remaining
                        continue
                # Not a command or meta parameter, stop parsing commands
                break

            # Found a command - add it to the chain
            add_parent_metas(app)
            apps.append(app)
            command_mapping = _combined_meta_command_mapping(app, recurse_parent_meta=include_parent_meta)
            command_chain.append(token)
            unused_tokens = unused_tokens[1:]

        return tuple(command_chain), tuple(apps), unused_tokens

    def _get_resolution_context(self, execution_path: Sequence["App"]) -> list["App"]:
        """Get all apps that contribute to parameter resolution for the given execution path.

        This includes parent meta apps and the meta app of the final command app.

        Parameters
        ----------
        execution_path : Sequence[App]
            The execution path returned from parse_commands.

        Returns
        -------
        list[App]
            All apps that contribute configuration and parameters, ordered by priority.
        """
        apps = []

        # For the last app in execution path, include it and its meta
        if execution_path:
            last_app = execution_path[-1]
            # Include all metas from walk_metas (includes the app itself)
            for app in _walk_metas(last_app):
                if app not in apps:
                    apps.append(app)

            # Include parent metas from the stack if they exist
            if last_app.app_stack.stack:
                for app in last_app.app_stack.stack[-1]:
                    # Include the app's meta if it exists and isn't already in the list
                    if app._meta and app._meta not in apps:
                        # Check if last_app is a command from the meta app
                        is_meta_command = last_app in app._meta._commands.values()
                        if not is_meta_command:
                            apps.append(app._meta)

        return apps

    def _consume_leading_meta_options(self, apps: list["App"], tokens: list[str]) -> list[str]:
        """Consume meta app options from the beginning of the token stream.

        This is used to skip over meta app parameters when looking for commands.

        Limitation: positional parameters for the meta app are NOT skipped.
        This is because we do not know which meta-parameters are for the
        meta-app itself vs which it will pass along to the normal app.

        Parameters
        ----------
        apps: list[App]
            Current app stack including parent meta apps.
        tokens: list[str]
            Tokens to try parsing, starting from current position.

        Returns
        -------
        list[str]
            The remaining unused tokens after consuming any leading meta options.
        """
        if not apps or not tokens:
            return tokens

        from cyclopts.bind import _parse_kw_and_flags

        # Resolve end_of_options_delimiter from the partially-resolved app stack
        with self.app_stack(apps):
            end_of_options_delimiter = self.app_stack.resolve("end_of_options_delimiter", fallback="--")

        # Collect meta apps that could have parameters
        # We need both:
        # 1. Meta apps in the current stack (apps that ARE meta apps)
        # 2. The meta app of the current context (if it exists)
        meta_apps_to_try = [app for app in apps if app._meta_parent is not None and app.default_command]

        # Add the current app's meta if it exists
        if apps[-1]._meta and apps[-1]._meta.default_command:
            meta_apps_to_try.append(apps[-1]._meta)

        # Try to parse with each meta app's parameters
        unused_tokens = tokens
        for meta_app in meta_apps_to_try:
            try:
                argument_collection = meta_app.assemble_argument_collection()

                # Try to consume tokens with this meta app's parameters
                # stop_at_first_unknown=True ensures we only consume contiguous leading options
                unused_tokens = _parse_kw_and_flags(
                    argument_collection,
                    unused_tokens,
                    end_of_options_delimiter=end_of_options_delimiter,
                    stop_at_first_unknown=True,
                )
            except Exception:
                # If parsing fails, try next meta app
                continue

        return unused_tokens

    # This overload is used in code like:
    #
    # @app.command
    # def my_command(foo: str):
    #   ...
    @overload
    def command(  # pragma: no cover
        self,
        obj: T,
        name: None | str | Iterable[str] = None,
        *,
        alias: None | str | Iterable[str] = None,
        **kwargs: object,
    ) -> T: ...

    # This overload is used in code like:
    #
    # @app.command(name="bar")
    # def my_command(foo: str):
    #   ...
    @overload
    def command(  # pragma: no cover
        self,
        obj: None = None,
        name: None | str | Iterable[str] = None,
        *,
        alias: None | str | Iterable[str] = None,
        **kwargs: object,
    ) -> Callable[[T], T]: ...

    def command(
        self,
        obj: T | None = None,
        name: None | str | Iterable[str] = None,
        *,
        alias: None | str | Iterable[str] = None,
        **kwargs: object,
    ) -> T | Callable[[T], T]:
        """Decorator to register a function as a CLI command.

        Example usage:

        .. code-block::

            from cyclopts import App

            app = App()

            @app.command
            def foo():
                print("foo!")

            @app.command(name="buzz")
            def bar():
                print("bar!")

            app()

        .. code-block:: console

            $ my-script foo
            foo!

            $ my-script buzz
            bar!

        Parameters
        ----------
        obj: Callable | None
            Function or :class:`App` to be registered as a command.
        name: None | str | Iterable[str]
            Name(s) to register the command to.
            If not provided, defaults to:

            * If registering an :class:`App`, then the app's name.
            * If registering a **function**, then the function's name after applying :attr:`name_transform`.
        `**kwargs`
            Any argument that :class:`App` can take.
        """
        if obj is None:  # Called ``@app.command(...)``
            return partial(self.command, name=name, alias=alias, **kwargs)  # pyright: ignore[reportReturnType]

        if isinstance(obj, App):
            app = obj

            if app._name is None and name is None:
                raise ValueError("Sub-app MUST have a name specified.")

            if kwargs:
                raise ValueError("Cannot supplied additional configuration when registering a sub-App.")

            if app._group_commands is None:
                app._group_commands = copy(self._group_commands)

            if app._group_parameters is None:
                app._group_parameters = copy(self._group_parameters)

            if app._group_arguments is None:
                app._group_arguments = copy(self._group_arguments)
        else:
            kwargs.setdefault("help_flags", self.help_flags)
            kwargs.setdefault("version_flags", self.version_flags)

            if "group_commands" not in kwargs:
                kwargs["group_commands"] = copy(self._group_commands)
            if "group_parameters" not in kwargs:
                kwargs["group_parameters"] = copy(self._group_parameters)
            if "group_arguments" not in kwargs:
                kwargs["group_arguments"] = copy(self._group_arguments)
            app = type(self)(**kwargs)  # pyright: ignore
            # directly call the default decorator, in case we do additional processing there.
            app.default(obj)

        for flag in chain(app.help_flags, app.version_flags):
            app[flag].show = False

        if app._name_transform is None:
            app.name_transform = self.name_transform

        if name is None:
            name = app.name
        else:
            name = app._name = to_tuple_converter(name)

        if alias is None:
            alias = ()
        else:
            app.alias = alias = to_tuple_converter(alias)

        for n in name + alias:  # pyright: ignore[reportOperatorIssue]
            if n in self:
                raise CommandCollisionError(f'Command "{n}" already registered.')

            # Warning: app._name may not align with command name
            self._commands[n] = app

        return obj  # pyright: ignore[reportReturnType]

    # This overload is used in code like:
    #
    # @app.default
    # def my_command(foo: str):
    #   ...
    @overload
    def default(  # pragma: no cover
        self,
        obj: T,
        *,
        validator: Callable[..., Any] | None = None,
    ) -> T: ...

    # This overload is used in code like:
    #
    # @app.default()
    # def my_command(foo: str):
    #   ...
    @overload
    def default(  # pragma: no cover
        self,
        obj: None = None,
        *,
        validator: Callable[..., Any] | None = None,
    ) -> Callable[[T], T]: ...

    def default(
        self,
        obj: T | None = None,
        *,
        validator: Callable[..., Any] | None = None,
    ) -> T | Callable[[T], T]:
        """Decorator to register a function as the default action handler.

        Example usage:

        .. code-block:: python

            from cyclopts import App

            app = App()


            @app.default
            def main():
                print("Hello world!")


            app()

        .. code-block:: console

            $ my-script
            Hello world!
        """
        if obj is None:  # Called ``@app.default_command(...)``
            return partial(self.default, validator=validator)  # pyright: ignore[reportReturnType]

        if isinstance(obj, App):  # Registering a sub-App
            raise TypeError("Cannot register a sub-App to default.")

        if self.default_command is not None:
            raise CommandCollisionError(f"Default command previously set to {self.default_command}.")

        validate_command(obj)

        self.default_command = obj
        if validator:
            self.validator = validator  # pyright: ignore[reportAttributeAccessIssue]
        return obj

    def assemble_argument_collection(
        self,
        *,
        default_parameter: Parameter | None = None,
        parse_docstring: bool = False,
    ) -> ArgumentCollection:
        """Assemble the argument collection for this app.

        Parameters
        ----------
        default_parameter: Parameter | None
            Default parameter with highest priority.
        parse_docstring: bool
            Parse the docstring of :attr:`default_command`.
            Set to :obj:`True` if we need help strings, otherwise set to :obj:`False` for performance reasons.

        Returns
        -------
        ArgumentCollection
            All arguments for this app.
        """
        return ArgumentCollection._from_callable(
            self.default_command,  # pyright: ignore
            Parameter.combine(self.app_stack.default_parameter, default_parameter),
            group_arguments=self._group_arguments,  # pyright: ignore
            group_parameters=self._group_parameters,  # pyright: ignore
            parse_docstring=parse_docstring,
        )

    def parse_known_args(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        console: Optional["Console"] = None,
        end_of_options_delimiter: str | None = None,
    ) -> tuple[Callable[..., Any], inspect.BoundArguments, list[str], dict[str, Any]]:
        """Interpret arguments into a registered function, :class:`~inspect.BoundArguments`, and any remaining unknown tokens.

        Parameters
        ----------
        tokens: None | str | Iterable[str]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        console: ~rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        end_of_options_delimiter: str | None
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If None, inherits from :attr:`App.end_of_options_delimiter`, eventually defaulting to POSIX-standard ``"--"``.
            Set to an empty string to disable.

        Returns
        -------
        command: Callable
            Bare function to execute.

        bound: inspect.BoundArguments
            Bound arguments for ``command``.

        unused_tokens: list[str]
            Any remaining CLI tokens that didn't get parsed for ``command``.

        ignored: dict[str, Any]
            A mapping of python-variable-name to annotated type of any
            parameter with annotation ``parse=False``.
            :obj:`~typing.Annotated` will be resolved.
            Intended to simplify :ref:`meta apps <Meta App>`.
        """
        overrides = {
            "console": console,
            "end_of_options_delimiter": end_of_options_delimiter,
        }
        with self.app_stack([], overrides=overrides):
            command, bound, unused_tokens, ignored, _ = self._parse_known_args(tokens)

        return command, bound, unused_tokens, ignored

    def _parse_known_args(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        raise_on_unused_tokens: bool = False,
    ) -> tuple[Callable[..., Any], inspect.BoundArguments, list[str], dict[str, Any], ArgumentCollection]:
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)

        meta_parent = self

        # We need both versions of the apps list:
        # 1. apps_for_context (with parent metas) - for setting up the app_stack context
        # 2. execution_apps (without parent metas) - for determining the actual execution command
        # These can differ when parse_commands is called from a meta app, so we must
        # call parse_commands twice. This is not inefficient since the parsing is fast.
        _, apps_for_context, _ = self.parse_commands(tokens, include_parent_meta=True)
        command_chain, execution_apps, unused_tokens = self.parse_commands(tokens, include_parent_meta=False)

        # We don't want the command_app to be the version/help handler; we handle those specially
        command_app = execution_apps[-1]
        with suppress(IndexError):
            if set(command_app.name) & set(execution_apps[-2].help_flags + execution_apps[-2].version_flags):  # pyright: ignore
                execution_apps = execution_apps[:-1]

        command_app = execution_apps[-1]
        del execution_apps  # Always use AppStack from here-on.

        ignored: dict[str, Any] = {}

        with self.app_stack(apps_for_context):
            config: tuple[Callable, ...] = command_app.app_stack.resolve("_config") or ()
            config = tuple(partial(x, command_app, command_chain) for x in config)
            end_of_options_delimiter = self.app_stack.resolve("end_of_options_delimiter", fallback="--")
            console = command_app.console

            # Special flags (help/version) get intercepted by the root app.
            # Special flags are allows to be **anywhere** in the token stream.

            help_flag_index = _get_help_flag_index(tokens, command_app.help_flags)

            try:
                if help_flag_index is not None:
                    tokens.pop(help_flag_index)

                    help_flag_index = _get_help_flag_index(unused_tokens, command_app.help_flags)
                    if help_flag_index is not None:
                        unused_tokens.pop(help_flag_index)

                    # Remove version flags when help is present to ensure help takes priority
                    for version_flag in command_app.version_flags:
                        with suppress(ValueError):
                            tokens.remove(version_flag)
                        with suppress(ValueError):
                            unused_tokens.remove(version_flag)

                    command = self.help_print
                    while meta_parent := meta_parent._meta_parent:
                        command = meta_parent.help_print
                    bound = inspect.signature(command).bind(tokens, console=console)
                    unused_tokens = []
                    argument_collection = ArgumentCollection()
                elif any(flag in tokens for flag in command_app.version_flags):
                    command = _get_version_command(self)
                    while meta_parent := meta_parent._meta_parent:
                        command = _get_version_command(meta_parent)

                    bound = inspect.signature(command).bind(console=console)
                    unused_tokens = []
                    argument_collection = ArgumentCollection()
                else:
                    if command_app.default_command:
                        command = command_app.default_command
                        validate_command(command)
                        argument_collection = command_app.assemble_argument_collection()
                        ignored: dict[str, Any] = {
                            argument.field_info.name: resolve_annotated(argument.field_info.annotation)
                            for argument in argument_collection.filter_by(parse=False)
                        }

                        bound, unused_tokens = create_bound_arguments(
                            command_app.default_command,
                            argument_collection,
                            unused_tokens,
                            config,
                            end_of_options_delimiter=end_of_options_delimiter,
                        )
                        try:
                            for validator in command_app.validator:
                                validator(**bound.arguments)
                        except (AssertionError, ValueError, TypeError) as e:
                            raise ValidationError(exception_message=e.args[0] if e.args else "", app=command_app) from e

                        try:
                            for command_group in command_app.app_stack.command_groups:
                                for validator in command_group.validator:  # pyright: ignore
                                    validator(**bound.arguments)
                        except (AssertionError, ValueError, TypeError) as e:
                            raise ValidationError(
                                exception_message=e.args[0] if e.args else "",
                                group=command_group,  # pyright: ignore
                            ) from e

                    else:
                        if unused_tokens:
                            raise UnknownCommandError(unused_tokens=unused_tokens)
                        else:
                            # Running the application with no arguments and no registered
                            # ``default_command`` will default to ``help_print``.
                            command = self.help_print
                            bound = inspect.signature(command).bind(tokens=tokens, console=console)
                            unused_tokens = []
                            argument_collection = ArgumentCollection()
                if raise_on_unused_tokens and unused_tokens:
                    for token in unused_tokens:
                        if is_option_like(token):
                            token = token.split("=")[0]
                            raise UnknownOptionError(
                                token=Token(keyword=token, source="cli"),
                                argument_collection=argument_collection,
                            )
                    raise UnusedCliTokensError(target=command, unused_tokens=unused_tokens)
            except CycloptsError as e:
                e.target = command_app.default_command
                e.app = command_app
                if command_chain:
                    e.command_chain = command_chain
                if e.console is None:
                    e.console = console
                raise

        return command, bound, unused_tokens, ignored, argument_collection

    def parse_args(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool | None = None,
        exit_on_error: bool | None = None,
        help_on_error: bool | None = None,
        verbose: bool | None = None,
        end_of_options_delimiter: str | None = None,
    ) -> tuple[Callable, inspect.BoundArguments, dict[str, Any]]:
        """Interpret arguments into a function and :class:`~inspect.BoundArguments`.

        Raises
        ------
        UnusedCliTokensError
            If any tokens remain after parsing.

        Parameters
        ----------
        tokens: None | str | Iterable[str]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        console: ~rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        print_error: bool | None
            Print a rich-formatted error on error.
            If :obj:`None`, inherits from :attr:`App.print_error`, eventually defaulting to :obj:`True`.
        exit_on_error: bool | None
            If there is an error parsing the CLI tokens invoke ``sys.exit(1)``.
            Otherwise, continue to raise the exception.
            If :obj:`None`, inherits from :attr:`App.exit_on_error`, eventually defaulting to :obj:`True`.
        help_on_error: bool | None
            Prints the help-page before printing an error.
            If :obj:`None`, inherits from :attr:`App.help_on_error`, eventually defaulting to :obj:`False`.
        verbose: bool | None
            Populate exception strings with more information intended for developers.
            If :obj:`None`, inherits from :attr:`App.verbose`, eventually defaulting to :obj:`False`.
        end_of_options_delimiter: str | None
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, inherits from :attr:`App.end_of_options_delimiter`, eventually defaulting to POSIX-standard ``"--"``.
            Set to an empty string to disable.

        Returns
        -------
        command: Callable
            Function associated with command action.

        bound: inspect.BoundArguments
            Parsed and converted ``args`` and ``kwargs`` to be used when calling ``command``.

        ignored: dict[str, Any]
            A mapping of python-variable-name to type-hint of any parameter with annotation ``parse=False``.
            :obj:`~typing.Annotated` will be resolved.
            Intended to simplify :ref:`meta apps <Meta App>`.
        """
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)

        # Store overrides for nested calls
        overrides = {
            k: v
            for k, v in {
                "_console": console,
                "print_error": print_error,
                "exit_on_error": exit_on_error,
                "help_on_error": help_on_error,
                "verbose": verbose,
                "end_of_options_delimiter": end_of_options_delimiter,
            }.items()
            if v is not None
        }

        # overrides isn't being propagated to subcommands because they aren't provided to the context manager here.
        with self.app_stack([], overrides=overrides):
            try:
                command, bound, _, ignored, _ = self._parse_known_args(
                    tokens,
                    raise_on_unused_tokens=True,
                )
            except CycloptsError as e:
                print_error = self.app_stack.resolve("print_error")
                exit_on_error = self.app_stack.resolve("exit_on_error")
                help_on_error = self.app_stack.resolve("help_on_error")
                verbose = self.app_stack.resolve("verbose")

                e.verbose = verbose if verbose is not None else False
                e.root_input_tokens = tokens
                assert e.console is not None
                if help_on_error if help_on_error is not None else False:
                    self.help_print(tokens, console=e.console)
                if print_error if print_error is not None else True:
                    e.console.print(CycloptsPanel(e))
                if exit_on_error if exit_on_error is not None else True:
                    sys.exit(1)
                raise

        return command, bound, ignored

    def __call__(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool | None = None,
        exit_on_error: bool | None = None,
        help_on_error: bool | None = None,
        verbose: bool | None = None,
        end_of_options_delimiter: str | None = None,
        backend: Literal["asyncio", "trio"] | None = None,
    ):
        """Interprets and executes a command.

        Parameters
        ----------
        tokens : None | str | Iterable[str]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        console: ~rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        print_error: bool | None
            Print a rich-formatted error on error.
            If :obj:`None`, inherits from :attr:`App.print_error`, eventually defaulting to :obj:`True`.
        exit_on_error: bool | None
            If there is an error parsing the CLI tokens invoke ``sys.exit(1)``.
            Otherwise, continue to raise the exception.
            If :obj:`None`, inherits from :attr:`App.exit_on_error`, eventually defaulting to :obj:`True`.
        help_on_error: bool | None
            Prints the help-page before printing an error.
            If :obj:`None`, inherits from :attr:`App.help_on_error`, eventually defaulting to :obj:`False`.
        verbose: bool | None
            Populate exception strings with more information intended for developers.
            If :obj:`None`, inherits from :attr:`App.verbose`, eventually defaulting to :obj:`False`.
        end_of_options_delimiter: str | None
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, inherits from :attr:`App.end_of_options_delimiter`, eventually defaulting to POSIX-standard ``"--"``.
            Set to an empty string to disable.
        backend: Literal["asyncio", "trio"] | None
            Override the async backend to use (if an async command is invoked).
            If :obj:`None`, inherits from :attr:`App.backend`, eventually defaulting to "asyncio".
            If passing backend="trio", ensure trio is installed via the extra: `cyclopts[trio]`.

        Returns
        -------
        return_value: Any
            The value the command function returns.
        """
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)

        overrides = {
            k: v
            for k, v in {
                "_console": console,
                "print_error": print_error,
                "exit_on_error": exit_on_error,
                "help_on_error": help_on_error,
                "verbose": verbose,
                "backend": backend,
            }.items()
            if v is not None
        }

        with self.app_stack(tokens, overrides):
            command, bound, _ = self.parse_args(
                tokens,
                console=console,
                end_of_options_delimiter=end_of_options_delimiter,
            )

            resolved_backend = cast(Literal["asyncio", "trio"], self.app_stack.resolve("backend", fallback="asyncio"))
            try:
                return _run_maybe_async_command(command, bound, resolved_backend)
            except KeyboardInterrupt:
                if self.suppress_keyboard_interrupt:
                    sys.exit(130)  # Use the same exit code as Python's default KeyboardInterrupt handling.
                else:
                    raise

    async def run_async(
        self,
        tokens: None | str | Iterable[str] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        help_on_error: bool | None = None,
        verbose: bool = False,
        end_of_options_delimiter: str | None = None,
    ):
        """Async equivalent of :meth:`__call__` for use within existing event loops.

        This method should be used when you're already in an async context
        (e.g., Jupyter notebooks, existing async applications) and need to
        execute a Cyclopts command without creating a new event loop.

        Parameters
        ----------
        tokens : None | str | Iterable[str]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``.
        console: ~rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        print_error: bool
            Print a rich-formatted error on error.
            Defaults to :obj:`True`.
        exit_on_error: bool
            If there is an error parsing the CLI tokens invoke ``sys.exit(1)``.
            Otherwise, continue to raise the exception.
            Defaults to ``True``.
        help_on_error: bool
            Prints the help-page before printing an error, overriding :attr:`App.help_on_error`.
            Defaults to :obj:`None` (interpret from :class:`.App`, eventually defaulting to :obj:`False`).
        verbose: bool
            Populate exception strings with more information intended for developers.
            Defaults to :obj:`False`.
        end_of_options_delimiter: str | None
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, fallback to :class:`App.end_of_options_delimiter`.
            If that is not set, it will default to POSIX-standard ``"--"``.

        Returns
        -------
        return_value: Any
            The value the command function returns.

        Examples
        --------
        .. code-block:: python

            import asyncio
            from cyclopts import App

            app = App()


            @app.command
            async def my_async_command():
                await asyncio.sleep(1)
                return "Done!"


            # In an async context (e.g., Jupyter notebook or existing async app):
            async def main():
                result = await app.run_async(["my-async-command"])
                print(result)  # Prints: Done!


            asyncio.run(main())
        """
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)

        overrides = {
            k: v
            for k, v in {
                "_console": console,
                "print_error": print_error,
                "exit_on_error": exit_on_error,
                "help_on_error": help_on_error,
                "verbose": verbose,
            }.items()
            if v is not None
        }

        with self.app_stack(tokens, overrides):
            command, bound, _ = self.parse_args(
                tokens,
                console=console,
                end_of_options_delimiter=end_of_options_delimiter,
            )

            try:
                if inspect.iscoroutinefunction(command):
                    return await command(*bound.args, **bound.kwargs)
                else:
                    return command(*bound.args, **bound.kwargs)
            except KeyboardInterrupt:
                if self.suppress_keyboard_interrupt:
                    sys.exit(130)  # Use the same exit code as Python's default KeyboardInterrupt handling.
                else:
                    raise

    def help_print(
        self,
        tokens: Annotated[None | str | Iterable[str], Parameter(show=False)] = None,
        *,
        console: Annotated[Optional["Console"], Parameter(parse=False)] = None,
    ) -> None:
        """Print the help page.

        Parameters
        ----------
        tokens: None | str | Iterable[str]
            Tokens to interpret for traversing the application command structure.
            If not provided, defaults to ``sys.argv``.
        console: ~rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        """
        from cyclopts.help import format_doc, format_usage
        from cyclopts.help.formatters import DefaultFormatter

        tokens = normalize_tokens(tokens)

        command_chain, apps, _ = self.parse_commands(tokens)
        executing_app = apps[-1]
        overrides = {"_console": console}
        with self.app_stack(apps, overrides=overrides):
            console = executing_app.console

            # Prepare usage
            if executing_app.usage is None:
                usage = format_usage(self, command_chain)
            elif executing_app.usage:  # i.e. skip empty-string.
                usage = executing_app.usage + "\n"
            else:
                usage = None

            # Prepare description
            help_format = executing_app.app_stack.resolve("help_format", fallback=_DEFAULT_FORMAT)
            description = format_doc(executing_app, help_format)

            # Prepare panels with their associated groups
            help_panels_with_groups = self._assemble_help_panels(tokens, help_format)

            # Render usage
            default_formatter = executing_app.app_stack.resolve("help_formatter", fallback=DefaultFormatter())
            if hasattr(default_formatter, "render_usage"):
                default_formatter.render_usage(console, console.options, usage)
            elif usage:
                console.print(usage)

            # Render description
            if hasattr(default_formatter, "render_description"):
                default_formatter.render_description(console, console.options, description)
            elif description:
                console.print(description)

            # Render each panel with its group's formatter (or default)
            for group, panel in help_panels_with_groups:
                formatter = group.help_formatter if group else None
                if formatter is None:
                    formatter = default_formatter
                formatter = cast("HelpFormatter", formatter)
                formatter(console, console.options, panel)

    def _assemble_help_panels(
        self,
        tokens: None | str | Iterable[str],
        help_format,
    ) -> list[tuple[Optional["Group"], "HelpPanel"]]:
        from rich.console import Group as RichGroup
        from rich.console import NewLine

        from cyclopts.help import (
            HelpPanel,
            InlineText,
            create_parameter_help_panel,
            format_command_entries,
        )

        command_chain, execution_path, _ = self.parse_commands(tokens)
        command_app = execution_path[-1]

        help_format = command_app.app_stack.resolve("help_format", help_format, _DEFAULT_FORMAT)

        panels: dict[str, tuple[Group, HelpPanel]] = {}
        # Handle commands first; there's an off chance they may be "upgraded"
        # to an argument/parameter panel.
        for subapp in _walk_metas(command_app):
            for group, subapps in groups_from_app(subapp):
                if not group.show:
                    continue

                # Fetch a group's help-panel, or create it if it does not yet exist.
                try:
                    _, command_panel = panels[group.name]
                except KeyError:
                    command_panel = HelpPanel(title=group.name, format="command")
                    panels[group.name] = (group, command_panel)

                if group.help:
                    group_help = InlineText.from_format(group.help, format=help_format, force_empty_end=True)

                    if command_panel.description:
                        command_panel.description = RichGroup(command_panel.description, NewLine(), group_help)
                    else:
                        command_panel.description = group_help

                # Add the command to the group's help panel.
                command_panel.entries.extend(format_command_entries(subapps, format=help_format))

        # Handle Arguments/Parameters
        # We have to combine all the help-pages of the command-app and it's meta apps.
        # Use get_resolution_context to get all apps that contribute parameters
        apps_for_params = self._get_resolution_context(execution_path)

        for subapp in apps_for_params:
            if not subapp.default_command:
                continue

            argument_collection = subapp.assemble_argument_collection(parse_docstring=True)

            # Special-case: add config.Env values to Parameter(env_var=)
            configs: tuple[Callable, ...] = subapp.app_stack.resolve("_config") or ()
            env_configs = tuple(x for x in configs if isinstance(x, Env) and x.show)
            for argument in argument_collection:
                for env_config in env_configs:
                    env_var = env_config._convert_argument(command_chain, argument)
                    assert isinstance(argument.parameter.env_var, tuple)
                    argument.parameter = Parameter.combine(
                        argument.parameter,
                        Parameter(env_var=(*argument.parameter.env_var, env_var)),
                    )

            for group in argument_collection.groups:
                if not group.show:
                    continue
                group_argument_collection = argument_collection.filter_by(group=group)
                if not group_argument_collection:
                    continue

                _, existing_panel = panels.get(group.name, (None, None))
                new_panel = create_parameter_help_panel(group, group_argument_collection, help_format)

                if existing_panel:
                    # An imperfect merging process
                    existing_panel.format = "parameter"
                    new_panel.entries = new_panel.entries + existing_panel.entries  # Commands go last
                    if new_panel.description:
                        if existing_panel.description:
                            new_panel.description = RichGroup(
                                existing_panel.description, NewLine(), new_panel.description
                            )
                    else:
                        new_panel.description = existing_panel.description

                panels[group.name] = (group, new_panel)

        groups = [x[0] for x in panels.values()]
        help_panels = [x[1] for x in panels.values()]

        out = []
        sorted_groups, sorted_panels = sort_groups(groups, help_panels)
        for group, help_panel in zip(sorted_groups, sorted_panels, strict=False):
            help_panel._remove_duplicates()
            if help_panel.format == "command":
                # don't sort format == "parameter" because order may matter there!
                help_panel._sort()
            out.append((group, help_panel))
        return out

    def generate_docs(
        self,
        output_format: "DocFormat" = "markdown",
        recursive: bool = True,
        include_hidden: bool = False,
        heading_level: int = 1,
        flatten_commands: bool = False,
    ) -> str:
        """Generate documentation for this CLI application.

        Parameters
        ----------
        output_format : DocFormat
            Output format for the documentation. Accepts "markdown"/"md", "html"/"htm",
            or "rst"/"rest"/"restructuredtext". Default is "markdown".
        recursive : bool
            If True, generate documentation for all subcommands recursively.
            Default is True.
        include_hidden : bool
            If True, include hidden commands/parameters in documentation.
            Default is False.
        heading_level : int
            Starting heading level for the main application title.
            Default is 1 (single # for markdown, = for RST).
        flatten_commands : bool
            If True, generate all commands at the same heading level instead of nested.
            Default is False.

        Returns
        -------
        str
            The generated documentation.

        Raises
        ------
        ValueError
            If an unsupported output format is specified.

        Examples
        --------
        >>> app = App(name="myapp", help="My CLI Application")
        >>> docs = app.generate_docs()  # Generate markdown as string
        >>> html_docs = app.generate_docs(output_format="html")  # Generate HTML
        >>> rst_docs = app.generate_docs(output_format="rst")  # Generate RST
        >>> # To write to file, caller can do:
        >>> # Path("docs/cli.md").write_text(docs)
        """
        from cyclopts.docs import (
            generate_markdown_docs,
            generate_rst_docs,
            normalize_format,
        )
        from cyclopts.docs.html import generate_html_docs

        output_format = normalize_format(output_format)

        if output_format == "markdown":
            doc = generate_markdown_docs(
                self,
                recursive=recursive,
                include_hidden=include_hidden,
                heading_level=heading_level,
                flatten_commands=flatten_commands,
            )
        elif output_format == "html":
            doc = generate_html_docs(
                self,
                recursive=recursive,
                include_hidden=include_hidden,
                heading_level=heading_level,
                flatten_commands=flatten_commands,
            )
        elif output_format == "rst":
            doc = generate_rst_docs(
                self,
                recursive=recursive,
                include_hidden=include_hidden,
                heading_level=heading_level,
                flatten_commands=flatten_commands,
                no_root_title=False,  # Default to False for direct API usage
            )

        return doc

    def generate_completion(
        self,
        *,
        prog_name: str | None = None,
        shell: Literal["zsh", "bash", "fish"] | None = None,
    ) -> str:
        """Generate shell completion script for this application.

        Parameters
        ----------
        prog_name : str | None
            Program name for completion. If None, uses first name from app.name.
        shell : Literal["zsh", "bash", "fish"] | None
            Shell type. If None, automatically detects current shell.
            Supported shells: "zsh", "bash", "fish".

        Returns
        -------
        str
            Complete shell completion script.

        Examples
        --------
        Auto-detect shell and generate completion:

        >>> app = App(name="myapp")
        >>> script = app.generate_completion()
        >>> Path("_myapp").write_text(script)

        Explicitly specify shell type:

        >>> script = app.generate_completion(shell="zsh")

        Raises
        ------
        ValueError
            If app has no name or shell type is unsupported.
        ShellDetectionError
            If shell is None and auto-detection fails.
        """
        if prog_name is None:
            if not self.name:
                raise ValueError("App must have a name to generate completion script")
            prog_name = self.name[0] if isinstance(self.name, tuple) else self.name

        if shell is None:
            from cyclopts.completion import detect_shell

            shell = detect_shell()

        if shell == "zsh":
            from cyclopts.completion.zsh import generate_completion_script

            return generate_completion_script(self, prog_name)
        elif shell == "bash":
            from cyclopts.completion.bash import generate_completion_script

            return generate_completion_script(self, prog_name)
        elif shell == "fish":
            from cyclopts.completion.fish import generate_completion_script

            return generate_completion_script(self, prog_name)
        else:
            raise ValueError(f"Unsupported shell: {shell}")

    def install_completion(
        self,
        *,
        shell: Literal["zsh", "bash", "fish"] | None = None,
        output: Path | None = None,
        add_to_startup: bool = True,
    ) -> Path:
        """Install shell completion script to appropriate location.

        Generates and writes the completion script to a shell-specific location.

        Parameters
        ----------
        shell : Literal["zsh", "bash", "fish"] | None
            Shell type for completion. If not specified, attempts to auto-detect current shell.
        output : Path | None
            Output path for the completion script. If not specified, uses shell-specific default:
            - zsh: ~/.zsh/completions/_<prog_name>
            - bash: ~/.local/share/bash-completion/completions/<prog_name>
            - fish: ~/.config/fish/completions/<prog_name>.fish
        add_to_startup : bool
            If True (default), adds source line to shell RC file to ensure completion is loaded.
            Set to False if completions are already configured to auto-load.

        Returns
        -------
        Path
            Path where the completion script was installed.

        Examples
        --------
        Auto-detect shell and install:

        >>> app = App(name="myapp")
        >>> path = app.install_completion()

        Install for specific shell:

        >>> path = app.install_completion(shell="zsh")

        Install to custom path:

        >>> path = app.install_completion(output=Path("/custom/path"))

        Install without modifying RC files:

        >>> path = app.install_completion(shell="bash", add_to_startup=False)

        Raises
        ------
        ShellDetectionError
            If shell is None and auto-detection fails.
        ValueError
            If shell type is unsupported.
        """
        from cyclopts.completion.detect import detect_shell

        if shell is None:
            shell = detect_shell()

        from cyclopts.completion.install import add_to_rc_file, get_default_completion_path

        script_content = self.generate_completion(shell=shell)

        if output is None:
            output = get_default_completion_path(shell, self.name[0])

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(script_content)

        # Fish does not need any startup script changes.
        if add_to_startup and shell in ("bash", "zsh"):
            add_to_rc_file(output, self.name[0], shell)

        return output

    def register_install_completion_command(
        self,
        name: str | Iterable[str] = "--install-completion",
        add_to_startup: bool = True,
        **kwargs,
    ) -> None:
        """Register a command for installing shell completion.

        This is a convenience method that creates a command which calls
        :meth:`install_completion`. For more control over the command
        implementation, users can manually define their own command.

        Parameters
        ----------
        name : str | Iterable[str]
            Command name(s) for the install completion command.
            Defaults to "--install-completion".
        add_to_startup : bool
            If True (default), adds source line to shell RC file to ensure completion is loaded.
            Set to False if completions are already configured to auto-load.
        **kwargs
            Additional keyword arguments to pass to :meth:`command`.
            Can be used to customize the command registration (e.g., group, help_flags, version_flags).

        Examples
        --------
        Register install-completion command:

        >>> app = App(name="myapp")
        >>> app.register_install_completion_command()
        >>> app()  # Now responds to: myapp --install-completion

        Use a custom command name:

        >>> app.register_install_completion_command(name="--setup-completion")

        Customize command registration:

        >>> app.register_install_completion_command(group="Setup", help_flags=[])

        Install without modifying RC files:

        >>> app.register_install_completion_command(add_to_startup=False)

        See Also
        --------
        install_completion : The underlying method that performs the installation.
        """

        def _install_completion_command(
            *,
            shell: Annotated[Literal["zsh", "bash", "fish"] | None, Parameter()] = None,
            output: Annotated[Path | None, Parameter(name=["-o", "--output"])] = None,
        ):
            """Install shell completion for this application.

            This command generates and installs the completion script to the appropriate
            location for your shell. After installation, you may need to restart your
            shell or source your shell configuration file.

            Parameters
            ----------
            shell : Literal["zsh", "bash", "fish"] | None
                Shell type for completion. If not specified, attempts to auto-detect current shell.
            output : Path | None
                Output path for the completion script. If not specified, uses shell-specific default.
            """
            from cyclopts.completion.detect import ShellDetectionError, detect_shell

            if shell is None:
                try:
                    shell = detect_shell()
                except ShellDetectionError:
                    print(
                        "Could not auto-detect shell. Please specify --shell explicitly.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

            install_path = self.install_completion(shell=shell, output=output, add_to_startup=add_to_startup)

            print(f"✓ Completion script installed to {install_path}")

            if shell == "zsh":
                if add_to_startup:
                    zshrc = Path.home() / ".zshrc"
                    print(f"✓ Added completion loader to {zshrc}")
                    print("\nRestart your shell or run: source ~/.zshrc")
                else:
                    completion_dir = install_path.parent
                    print(f"\nTo enable completions, ensure {completion_dir} is in your $fpath.")
                    print("Add this to your ~/.zshrc or ~/.zprofile if not already present:")
                    print(f"    fpath=({completion_dir} $fpath)")
                    print("    autoload -Uz compinit && compinit")
                    print("\nThen restart your shell or run: exec zsh")
            elif shell == "bash":
                if add_to_startup:
                    bashrc = Path.home() / ".bashrc"
                    print(f"✓ Added completion loader to {bashrc}")
                    print("\nRestart your shell or run: source ~/.bashrc")
                else:
                    print("\nCompletions will be automatically loaded by bash-completion.")
                    print("If completions don't work:")
                    print("  1. Ensure bash-completion is installed (v2.8+)")
                    print("  2. Restart your shell or run: exec bash")
                    print("\nNote: bash-completion is typically installed via:")
                    print("  - macOS: brew install bash-completion@2")
                    print("  - Debian/Ubuntu: apt install bash-completion")
                    print("  - Fedora/RHEL: dnf install bash-completion")
            elif shell == "fish":
                print("\nCompletions are automatically loaded in fish.")
                print("Restart your shell or run: source ~/.config/fish/config.fish")
            else:
                raise NotImplementedError

        self.command(_install_completion_command, name=name, **kwargs)

    def interactive_shell(
        self,
        prompt: str = "$ ",
        quit: None | str | Iterable[str] = None,
        dispatcher: Dispatcher | None = None,
        **kwargs,
    ) -> None:
        """Create a blocking, interactive shell.

        All registered commands can be executed in the shell.

        Parameters
        ----------
        prompt: str
            Shell prompt. Defaults to ``"$ "``.
        quit: str | Iterable[str]
            String or list of strings that will cause the shell to exit and this method to return.
            Defaults to ``["q", "quit"]``.
        dispatcher: Dispatcher | None
            Optional function that subsequently invokes the command.
            The ``dispatcher`` function must have signature:

            .. code-block:: python

                def dispatcher(command: Callable, bound: inspect.BoundArguments, ignored: dict[str, Any]) -> Any:
                    return command(*bound.args, **bound.kwargs)

            The above is the default dispatcher implementation.
        `**kwargs`
            Get passed along to :meth:`parse_args`.
        """
        if os.name == "posix":  # pragma: no cover
            # Mac/Linux
            print("Interactive shell. Press Ctrl-D to exit.")
        else:  # pragma: no cover
            # Windows
            print("Interactive shell. Press Ctrl-Z followed by Enter to exit.")

        if quit is None:
            quit = ["q", "quit"]
        if isinstance(quit, str):
            quit = [quit]

        def default_dispatcher(command, bound, _):
            return command(*bound.args, **bound.kwargs)

        if dispatcher is None:
            dispatcher = default_dispatcher

        kwargs.setdefault("exit_on_error", False)

        while True:
            try:
                user_input = input(prompt)
            except EOFError:  # pragma: no cover
                break

            tokens = normalize_tokens(user_input)
            if not tokens:
                continue
            if tokens[0] in quit:
                break

            try:
                command, bound, ignored = self.parse_args(tokens, **kwargs)
                dispatcher(command, bound, ignored)
            except CycloptsError:
                # Upstream ``parse_args`` already printed the error
                pass
            except Exception:
                print(traceback.format_exc())

    def update(self, app: "App"):
        """Copy over all commands from another :class:`App`.

        Commands from the meta app will **not** be copied over.

        Parameters
        ----------
        app: cyclopts.App
            All commands from this application will be copied over.
        """
        self._commands.update(app._commands)

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


def _get_help_flag_index(tokens, help_flags) -> int | None:
    for help_flag in help_flags:
        with suppress(ValueError):
            index = tokens.index(help_flag)
            break
    else:
        index = None

    return index


class TestFramework(str, Enum):
    UNKNOWN = ""
    PYTEST = "pytest"


@lru_cache  # Will always be the same for a given session.
def _detect_test_framework() -> TestFramework:
    """Detects if we are currently being ran in a test framework.

    Returns
    -------
    TestFramework
        Name of the testing framework. Returns an empty string if not testing
        framework discovered.
    """
    # Check if pytest is in sys.modules; PYTEST_VERSION can be set if
    # a cyclopts script is invoked via subprocess within a pytest unit-test.
    if "pytest" in sys.modules and os.environ.get("PYTEST_VERSION") is not None:
        # "PYTEST_VERSION" is set as of pytest v8.2.0 (Apr 27, 2024)
        return TestFramework.PYTEST
    else:
        return TestFramework.UNKNOWN


@lru_cache  # Prevent logging of multiple warnings
def _log_framework_warning(framework: TestFramework) -> None:
    """Log a warning message for a given testing framework.

    Intended to catch developers invoking their app during unit-tests
    without providing commands and erroneously reading from :obj:`sys.argv`.

    TO ONLY BE CALLED WITHIN A CYCLOPTS.APP METHOD.
    """
    if framework == TestFramework.UNKNOWN:
        return
    import warnings

    for elem in inspect.stack():
        frame = elem.frame
        f_back = frame.f_back
        calling_module = inspect.getmodule(f_back)
        if calling_module is None or f_back is None:
            continue
        calling_module_name = calling_module.__name__.split(".")[0]
        if calling_module_name == "cyclopts":
            continue

        # The "self" is within the Cyclopts codebase App.ANY_METHOD_HERE,
        # so this is a safe lookup.
        called_cyclopts_app_instance = frame.f_locals["self"]
        # Find the variable name in the previous frame that references this object
        candidate_variables = {**f_back.f_globals, **f_back.f_locals}
        matched_app_variables = []
        for var_name, var_instance in candidate_variables.items():
            if var_instance is called_cyclopts_app_instance:
                matched_app_variables.append(var_name)
        if len(matched_app_variables) != 1:
            # We could not determine the exact variable name; just call it app
            var_name = "app"
        else:
            var_name = matched_app_variables[0]

        message = f'Cyclopts application invoked without tokens under unit-test framework "{framework.value}". Did you mean "{var_name}([])"?'
        warnings.warn(UserWarning(message), stacklevel=3)
        break


@overload
def run(callable: Callable[..., Coroutine[None, None, V]], /) -> V: ...


@overload
def run(callable: Callable[..., V], /) -> V: ...


def run(callable, /):
    """Run the given callable as a CLI command and return its result.

    The callable may also be a coroutine function.
    This function is syntax sugar for very simple use cases, and is roughly equivalent to:

    .. code-block:: python

        from cyclopts import App

        app = App()
        app.default(callable)
        app()

    Example usage:

    .. code-block:: python

        import cyclopts


        def main(name: str, age: int):
            print(f"Hello {name}, you are {age} years old.")


        cyclopts.run(main)
    """
    app = App()
    app.default(callable)
    return app()
