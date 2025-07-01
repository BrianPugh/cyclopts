import inspect
import os
import sys
import traceback
from collections.abc import Coroutine, Iterable, Iterator
from contextlib import suppress
from copy import copy
from enum import Enum
from functools import lru_cache, partial
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    TypeVar,
    Union,
    overload,
)

from attrs import define, field

from cyclopts.annotations import resolve_annotated
from cyclopts.argument import ArgumentCollection
from cyclopts.bind import create_bound_arguments, is_option_like, normalize_tokens
from cyclopts.config._env import Env
from cyclopts.exceptions import (
    CommandCollisionError,
    CycloptsError,
    InvalidCommandError,
    UnknownOptionError,
    UnusedCliTokensError,
    ValidationError,
)
from cyclopts.group import Group, sort_groups
from cyclopts.group_extractors import groups_from_app, inverse_groups_from_app
from cyclopts.help import (
    CycloptsPanel,
    HelpPanel,
    InlineText,
    create_parameter_help_panel,
    format_command_entries,
    format_doc,
    format_usage,
    resolve_help_format,
    resolve_version_format,
)
from cyclopts.parameter import Parameter, validate_command
from cyclopts.protocols import Dispatcher
from cyclopts.token import Token
from cyclopts.utils import (
    UNSET,
    default_name_transform,
    optional_to_tuple_converter,
    to_list_converter,
    to_tuple_converter,
)

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import assert_never
else:  # pragma: no cover
    from typing import assert_never

T = TypeVar("T", bound=Callable[..., Any])
V = TypeVar("V")


with suppress(ImportError):
    # By importing, makes things like the arrow-keys work.
    # Not available on windows
    import readline  # noqa: F401

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
        from importlib_metadata import PackageNotFoundError  # pyright: ignore[reportMissingImports]
        from importlib_metadata import version as importlib_metadata_version  # pyright: ignore[reportMissingImports]
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


def _combined_meta_command_mapping(
    app: Optional["App"], recurse_meta=True, recurse_parent_meta=True
) -> dict[str, "App"]:
    """Return a copied and combined mapping containing app and meta-app commands."""
    if app is None:
        return {}
    command_mapping = copy(app._commands)
    if recurse_meta:
        command_mapping.update(_combined_meta_command_mapping(app._meta))
    if recurse_parent_meta and app._meta_parent:
        command_mapping.update(_combined_meta_command_mapping(app._meta_parent, recurse_meta=False))
    return command_mapping


def _get_command_groups(parent_app: "App", child_app: "App"):
    """Extract out the command groups from the ``parent_app`` for a given ``child_app``."""
    return next(x for x in inverse_groups_from_app(parent_app) if x[0] is child_app)[1]


def resolve_default_parameter_from_apps(apps: Optional[Sequence["App"]]) -> Parameter:
    """The default_parameter resolution depends on the parent-child path traversed."""
    if not apps:
        return Parameter()

    cparams = []
    for parent_app, child_app in zip(apps[:-1], apps[1:]):
        # child_app could be a command of parent_app.meta
        if parent_app._meta and child_app in parent_app._meta.subapps:
            cparams = []  # meta-apps do NOT inherit from their parenting app.
            parent_app = parent_app._meta

        groups = _get_command_groups(parent_app, child_app)
        cparams.extend([group.default_parameter for group in groups])
        cparams.append(parent_app.default_parameter)

    cparams.append(apps[-1].default_parameter)

    return Parameter.combine(*cparams)


def _walk_metas(app: "App"):
    # Iterates from deepest to shallowest meta-apps
    meta_list = [app]  # shallowest to deepest
    meta = app
    while (meta := meta._meta) and meta.default_command:
        meta_list.append(meta)
    yield from reversed(meta_list)


def _group_converter(input_value: Union[None, str, Group]) -> Optional[Group]:
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
    _name: Union[None, str, tuple[str, ...]] = field(default=None, alias="name", converter=optional_to_tuple_converter)

    _help: Optional[str] = field(default=None, alias="help")

    usage: Optional[str] = field(default=None)

    # Everything below must be kw_only

    alias: Union[None, str, tuple[str, ...]] = field(
        default=None,
        converter=to_tuple_converter,
        kw_only=True,
    )

    default_command: Optional[Callable[..., Any]] = field(
        default=None, converter=_validate_default_command, kw_only=True
    )
    default_parameter: Optional[Parameter] = field(default=None, kw_only=True)

    # This can ONLY ever be None or Tuple[Callable, ...]
    _config: Union[
        None,
        Callable[[list["App"], tuple[str, ...], ArgumentCollection], Any],
        Iterable[Callable[[list["App"], tuple[str, ...], ArgumentCollection], Any]],
    ] = field(
        default=None,
        alias="config",
        converter=optional_to_tuple_converter,
        kw_only=True,
    )

    version: Union[None, str, Callable[..., str]] = field(default=_default_version, kw_only=True)
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
    help_on_error: Optional[bool] = field(default=None, kw_only=True)

    version_format: Optional[
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
    group: Union[Group, str, tuple[Union[Group, str], ...]] = field(
        default=None, converter=to_tuple_converter, kw_only=True
    )

    # This can ONLY ever be a Group or None
    _group_arguments: Union[Group, str, None] = field(
        alias="group_arguments",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )
    # This can ONLY ever be a Group or None
    _group_parameters: Union[Group, str, None] = field(
        alias="group_parameters",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )
    # This can ONLY ever be a Group or None
    _group_commands: Union[Group, str, None] = field(
        alias="group_commands",
        default=None,
        converter=_group_converter,
        kw_only=True,
    )

    validator: list[Callable[..., Any]] = field(default=None, converter=to_list_converter, kw_only=True)

    _name_transform: Optional[Callable[[str], str]] = field(
        default=None,
        alias="name_transform",
        kw_only=True,
    )

    _sort_key: Any = field(
        default=None,
        alias="sort_key",
        converter=lambda x: UNSET if x is None else x,
        kw_only=True,
    )

    end_of_options_delimiter: Optional[str] = field(default=None, kw_only=True)

    suppress_keyboard_interrupt: bool = field(default=True, kw_only=True)

    ######################
    # Private Attributes #
    ######################
    # Maps CLI-name of a command to a function handle.
    _commands: dict[str, "App"] = field(init=False, factory=dict)

    _parents: list["App"] = field(init=False, factory=list)

    _meta: Optional["App"] = field(init=False, default=None)
    _meta_parent: Optional["App"] = field(init=False, default=None)

    def __attrs_post_init__(self):
        # Trigger the setters
        self.help_flags = self._help_flags
        self.version_flags = self._version_flags

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
    def config(self) -> tuple[str, ...]:
        return self._resolve(None, None, "_config")  # pyright: ignore[reportReturnType]

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
        self._sort_key = value

    @property
    def _registered_commands(self) -> dict[str, "App"]:
        """Commands that are not help or version commands."""
        out = {}
        for x in self:
            if x in self.help_flags or x in self.version_flags:
                continue
            out[x] = self[x]
        return out

    def version_print(
        self,
        console: Optional["Console"] = None,
    ) -> None:
        """Print the application version.

        Parameters
        ----------
        console: rich.console.Console
            Console to print version string to.
            If not provided, follows the resolution order defined in :attr:`App.console`.

        """
        console = self._resolve_console(None, console)
        version_format = resolve_version_format([self])

        version_raw = self.version() if callable(self.version) else self.version

        if version_raw is None:
            version_raw = "0.0.0"

        version_formatted = InlineText.from_format(version_raw, format=version_format)
        console.print(version_formatted)

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
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        include_parent_meta=True,
    ) -> tuple[tuple[str, ...], tuple["App", ...], list[str]]:
        """Extract out the command tokens from a command.

        You are probably actually looking for :meth:`parse_args`.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``

        Returns
        -------
        List[str]
            Strings that are interpreted as a valid command chain.
        List[App]
            The associated :class:`App` object for each element in the command chain.
        List[str]
            The remaining non-command tokens.
        """
        tokens = normalize_tokens(tokens)

        command_chain = []
        app = self
        apps: list[App] = [app]
        unused_tokens = tokens

        command_mapping = _combined_meta_command_mapping(app, recurse_parent_meta=include_parent_meta)

        for i, token in enumerate(tokens):
            try:
                app = command_mapping[token]
                apps.append(app)
                unused_tokens = tokens[i + 1 :]
            except KeyError:
                break
            command_chain.append(token)
            command_mapping = _combined_meta_command_mapping(app, recurse_parent_meta=include_parent_meta)

        return tuple(command_chain), tuple(apps), unused_tokens

    # This overload is used in code like:
    #
    # @app.command
    # def my_command(foo: str):
    #   ...
    @overload
    def command(  # pragma: no cover
        self,
        obj: T,
        name: Union[None, str, Iterable[str]] = None,
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
        name: Union[None, str, Iterable[str]] = None,
        **kwargs: object,
    ) -> Callable[[T], T]: ...

    def command(
        self,
        obj: Optional[T] = None,
        name: Union[None, str, Iterable[str]] = None,
        **kwargs: object,
    ) -> Union[T, Callable[[T], T]]:
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
        obj: Optional[Callable]
            Function or :class:`App` to be registered as a command.
        name: Union[None, str, Iterable[str]]
            Name(s) to register the command to.
            If not provided, defaults to:

            * If registering an :class:`App`, then the app's name.
            * If registering a **function**, then the function's name after applying :attr:`name_transform`.
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
            app._name = name  # pyright: ignore[reportAttributeAccessIssue]

        for n in to_tuple_converter(name):
            if n in self:
                raise CommandCollisionError(f'Command "{n}" already registered.')

            # Warning: app._name may not align with command name
            self._commands[n] = app

        app._parents.append(self)

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
        validator: Optional[Callable[..., Any]] = None,
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
        validator: Optional[Callable[..., Any]] = None,
    ) -> Callable[[T], T]: ...

    def default(
        self,
        obj: Optional[T] = None,
        *,
        validator: Optional[Callable[..., Any]] = None,
    ) -> Union[T, Callable[[T], T]]:
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

        self.default_command = obj
        if validator:
            self.validator = validator  # pyright: ignore[reportAttributeAccessIssue]
        return obj

    def assemble_argument_collection(
        self,
        *,
        apps: Optional[Sequence["App"]] = None,
        default_parameter: Optional[Parameter] = None,
        parse_docstring: bool = False,
    ) -> ArgumentCollection:
        """Assemble the argument collection for this app.

        Parameters
        ----------
        apps: Optional[Sequence[App]]
            List of parenting apps that lead to this app.
            If provided, will resolve ``default_parameter`` from the apps.
        default_parameter: Optional[Parameter]
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
            Parameter.combine(resolve_default_parameter_from_apps(apps), self.default_parameter, default_parameter),
            group_arguments=self._group_arguments,  # pyright: ignore
            group_parameters=self._group_parameters,  # pyright: ignore
            parse_docstring=parse_docstring,
        )

    def parse_known_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"] = None,
        end_of_options_delimiter: Optional[str] = None,
    ) -> tuple[Callable[..., Any], inspect.BoundArguments, list[str], dict[str, Any]]:
        """Interpret arguments into a registered function, :class:`~inspect.BoundArguments`, and any remaining unknown tokens.

        Parameters
        ----------
        tokens: Union[None, str, Iterable[str]]
            Either a string, or a list of strings to launch a command.
            Defaults to ``sys.argv[1:]``
        console: rich.console.Console
            Console to print help and runtime Cyclopts errors.
            If not provided, follows the resolution order defined in :attr:`App.console`.
        end_of_options_delimiter: Optional[str]
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, fallback to :class:`App.end_of_options_delimiter`.
            If that is not set, it will default to POSIX-standard ``"--"``.
            Set to an empty string to disable.

        Returns
        -------
        command: Callable
            Bare function to execute.

        bound: inspect.BoundArguments
            Bound arguments for ``command``.

        unused_tokens: List[str]
            Any remaining CLI tokens that didn't get parsed for ``command``.

        ignored: dict[str, Any]
            A mapping of python-variable-name to annotated type of any
            parameter with annotation ``parse=False``.
            :obj:`~typing.Annotated` will be resolved.
            Intended to simplify :ref:`meta apps <Meta App>`.
        """
        command, bound, unused_tokens, ignored, argument_collection = self._parse_known_args(
            tokens, console=console, end_of_options_delimiter=end_of_options_delimiter
        )
        return command, bound, unused_tokens, ignored

    def _parse_known_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"],
        end_of_options_delimiter: Optional[str],
    ) -> tuple[Callable[..., Any], inspect.BoundArguments, list[str], dict[str, Any], ArgumentCollection]:
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)

        meta_parent = self

        command_chain, apps, unused_tokens = self.parse_commands(tokens, include_parent_meta=False)
        command_app = apps[-1]

        ignored: dict[str, Any] = {}

        # We don't want the command_app to be the version/help handler.
        with suppress(IndexError):
            if set(command_app.name) & set(apps[-2].help_flags + apps[-2].version_flags):  # pyright: ignore
                apps = apps[:-1]
                command_app = apps[-1]

        try:
            parent_app = apps[-2]
        except IndexError:
            parent_app = None

        config: tuple[Callable, ...] = self._resolve(apps, None, "_config") or ()
        config = tuple(partial(x, apps, command_chain) for x in config)
        end_of_options_delimiter = self._resolve(apps, end_of_options_delimiter, "end_of_options_delimiter")
        if end_of_options_delimiter is None:
            end_of_options_delimiter = "--"

        # Special flags (help/version) get intercepted by the root app.
        # Special flags are allows to be **anywhere** in the token stream.

        help_flag_index = _get_help_flag_index(tokens, command_app.help_flags)

        try:
            if help_flag_index is not None:
                tokens.pop(help_flag_index)

                help_flag_index = _get_help_flag_index(unused_tokens, command_app.help_flags)
                if help_flag_index is not None:
                    unused_tokens.pop(help_flag_index)

                if unused_tokens and not command_app.default_command:
                    raise InvalidCommandError(unused_tokens=unused_tokens)

                command = self.help_print
                while meta_parent := meta_parent._meta_parent:
                    command = meta_parent.help_print
                bound = inspect.signature(command).bind(tokens, console=console)
                unused_tokens = []
                argument_collection = ArgumentCollection()
            elif any(flag in tokens for flag in command_app.version_flags):
                # Version
                command = self.version_print
                while meta_parent := meta_parent._meta_parent:
                    command = meta_parent.version_print
                bound = inspect.signature(command).bind()
                unused_tokens = []
                argument_collection = ArgumentCollection()
            else:
                if command_app.default_command:
                    command = command_app.default_command
                    validate_command(command)
                    argument_collection = command_app.assemble_argument_collection(apps=apps)
                    ignored: dict[str, Any] = {
                        argument.field_info.name: resolve_annotated(argument.field_info.annotation)
                        for argument in argument_collection.filter_by(parse=False)
                    }

                    # We want the resolved group that ``app`` belongs to.
                    command_groups = [] if parent_app is None else _get_command_groups(parent_app, command_app)

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
                        for command_group in command_groups:
                            for validator in command_group.validator:  # pyright: ignore
                                validator(**bound.arguments)
                    except (AssertionError, ValueError, TypeError) as e:
                        raise ValidationError(
                            exception_message=e.args[0] if e.args else "",
                            group=command_group,  # pyright: ignore
                        ) from e

                else:
                    if unused_tokens:
                        raise InvalidCommandError(unused_tokens=unused_tokens)
                    else:
                        # Running the application with no arguments and no registered
                        # ``default_command`` will default to ``help_print``.
                        command = self.help_print
                        bound = inspect.signature(command).bind(tokens=tokens, console=console)
                        unused_tokens = []
                        argument_collection = ArgumentCollection()
        except CycloptsError as e:
            e.target = command_app.default_command
            e.app = command_app
            if command_chain:
                e.command_chain = command_chain
            if e.console is None:
                e.console = self._resolve_console(tokens, console)
            raise

        return command, bound, unused_tokens, ignored, argument_collection

    def parse_args(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        help_on_error: Optional[bool] = None,
        verbose: bool = False,
        end_of_options_delimiter: Optional[str] = None,
    ) -> tuple[Callable, inspect.BoundArguments, dict[str, Any]]:
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
            Defaults to :obj:`True`.
        exit_on_error: bool
            If there is an error parsing the CLI tokens invoke ``sys.exit(1)``.
            Otherwise, continue to raise the exception.
            Defaults to :obj:`True`.
        help_on_error: bool
            Prints the help-page before printing an error, overriding :attr:`App.help_on_error`.
            Defaults to :obj:`None` (interpret from :class:`.App`, eventually defaulting to :obj:`False`).
        verbose: bool
            Populate exception strings with more information intended for developers.
            Defaults to :obj:`False`.
        end_of_options_delimiter: Optional[str]
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, fallback to :class:`App.end_of_options_delimiter`.
            If that is not set, it will default to POSIX-standard ``"--"``.
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
        help_on_error = self._resolve(tokens, help_on_error, "help_on_error") or False

        # Normal parsing
        try:
            command, bound, unused_tokens, ignored, argument_collection = self._parse_known_args(
                tokens, console=console, end_of_options_delimiter=end_of_options_delimiter
            )
            if unused_tokens:
                for token in unused_tokens:
                    if is_option_like(token):
                        token = token.split("=")[0]
                        raise UnknownOptionError(
                            token=Token(keyword=token, source="cli"), argument_collection=argument_collection
                        )
                raise UnusedCliTokensError(
                    target=command,
                    unused_tokens=unused_tokens,
                )
        except CycloptsError as e:
            e.verbose = verbose
            e.root_input_tokens = tokens

            if e.console is None:
                e.console = self._resolve_console(tokens, console)
            if help_on_error:
                assert e.console
                self.help_print(tokens, console=e.console)
            if print_error:
                assert e.console
                e.console.print(CycloptsPanel(e))
            if exit_on_error:
                sys.exit(1)
            raise

        return command, bound, ignored

    def __call__(
        self,
        tokens: Union[None, str, Iterable[str]] = None,
        *,
        console: Optional["Console"] = None,
        print_error: bool = True,
        exit_on_error: bool = True,
        help_on_error: Optional[bool] = None,
        verbose: bool = False,
        end_of_options_delimiter: Optional[str] = None,
        backend: Literal["asyncio", "trio"] = "asyncio",
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
        end_of_options_delimiter: Optional[str]
            All tokens after this delimiter will be force-interpreted as positional arguments.
            If :obj:`None`, fallback to :class:`App.end_of_options_delimiter`.
            If that is not set, it will default to POSIX-standard ``"--"``.
        backend: Literal["asyncio", "trio"]
            The async backend to use (if an async command is invoked).
            Defaults to asyncio.
            If passing backend="trio", ensure trio is installed via the extra: `cyclopts[trio]`.

        Returns
        -------
        return_value: Any
            The value the command function returns.
        """
        if tokens is None:
            _log_framework_warning(_detect_test_framework())

        tokens = normalize_tokens(tokens)
        command, bound, _ = self.parse_args(
            tokens,
            console=console,
            print_error=print_error,
            exit_on_error=exit_on_error,
            help_on_error=help_on_error,
            verbose=verbose,
            end_of_options_delimiter=end_of_options_delimiter,
        )

        try:
            if inspect.iscoroutinefunction(command):
                # We don't use anyio to avoid the dependency for non-async users.
                # anyio can auto-select the backend when you're already in an async context,
                # but here we're creating the top-level event loop & must select ourselves.
                if backend == "asyncio":
                    import asyncio

                    return asyncio.run(command(*bound.args, **bound.kwargs))
                elif backend == "trio":
                    import trio

                    return trio.run(partial(command, *bound.args, **bound.kwargs))
                else:  # pragma: no cover
                    assert_never(backend)
            else:
                return command(*bound.args, **bound.kwargs)
        except KeyboardInterrupt:
            if self.suppress_keyboard_interrupt:
                sys.exit(130)  # Use the same exit code as Python's default KeyboardInterrupt handling.
            else:
                raise

    def _resolve(self, tokens_or_apps: Optional[Sequence], override: Optional[V], attribute: str) -> Optional[V]:
        if override is not None:
            return override

        if not tokens_or_apps:
            apps = (self,)
        elif isinstance(tokens_or_apps[0], App):
            apps = tokens_or_apps
        else:
            _, apps, _ = self.parse_commands(tokens_or_apps)

        for app in reversed(apps):
            result = getattr(app, attribute)
            if result is not None:
                return result

            # Check parenting meta app(s)
            meta_app = app
            while (meta_app := meta_app._meta_parent) is not None:
                result = getattr(meta_app, attribute)
                if result is not None:
                    return result

        return None

    def _resolve_console(self, tokens_or_apps: Optional[Sequence], override: Optional["Console"] = None) -> "Console":
        result = self._resolve(tokens_or_apps, override, "console")
        if result is not None:
            return result
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
        console.print(format_doc(executing_app, help_format))

        for help_panel in self._assemble_help_panels(tokens, help_format):
            console.print(help_panel)

    def _assemble_help_panels(
        self,
        tokens: Union[None, str, Iterable[str]],
        help_format,
    ) -> list[HelpPanel]:
        from rich.console import Group as RichGroup
        from rich.console import NewLine

        command_chain, apps, _ = self.parse_commands(tokens)

        help_format = resolve_help_format(apps)

        panels: dict[str, tuple[Group, HelpPanel]] = {}
        # Handle commands first; there's an off chance they may be "upgraded"
        # to an argument/parameter panel.
        for subapp in _walk_metas(apps[-1]):
            for group, subapps in groups_from_app(subapp):
                if not group.show:
                    continue

                # Fetch a group's help-panel, or create it if it does not yet exist.
                try:
                    _, command_panel = panels[group.name]
                except KeyError:
                    command_panel = HelpPanel(
                        format="command",
                        title=group.name,
                    )
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
        for subapp in _walk_metas(apps[-1]):
            if not subapp.default_command:
                continue

            argument_collection = subapp.assemble_argument_collection(apps=apps, parse_docstring=True)

            # Special-case: add config.Env values to Parameter(env_var=)
            configs: tuple[Callable, ...] = self._resolve(apps, None, "_config") or ()
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

                try:
                    _, existing_panel = panels[group.name]
                except KeyError:
                    existing_panel = None

                new_panel = create_parameter_help_panel(group, group_argument_collection, help_format)

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


def _get_help_flag_index(tokens, help_flags) -> Optional[int]:
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
