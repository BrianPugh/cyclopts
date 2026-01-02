"""Lazy-loadable command specification for deferred imports."""

import importlib
from itertools import chain
from typing import TYPE_CHECKING, Any

from attrs import Factory, define, field

from cyclopts.ast_utils import extract_docstring_from_import_path

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.group import Group


@define
class CommandSpec:
    """Specification for a command that will be lazily loaded on first access.

    This allows registering commands via import path strings (e.g., "myapp.commands:create")
    without importing them until they're actually used, improving CLI startup time.

    Parameters
    ----------
    import_path : str
        Import path in the format "module.path:attribute_name".
        The attribute should be either a function or an App instance.
    name : str | tuple[str, ...] | None
        CLI command name. If None, will be derived from the attribute name via name_transform.
        For function imports: used as the name of the wrapper App.
        For App imports: must match the App's internal name, or ValueError is raised at resolution.
    app_kwargs : dict
        Keyword arguments to pass to App() if wrapping a function.
        Raises ValueError if used with App imports (Apps should be configured in their own definition).

    Examples
    --------
    >>> from cyclopts import App
    >>> app = App()
    >>> # Lazy load - doesn't import myapp.commands until "create" is executed
    >>> app.command("myapp.commands:create_user", name="create")
    >>> app()
    """

    import_path: str
    name: str | tuple[str, ...] | None = None
    app_kwargs: dict[str, Any] = Factory(dict)

    _resolved_app: "App | None" = field(init=False, default=None, repr=False)
    _ast_docstring: str | None = field(init=False, default=None, repr=False)

    # Duck-typing properties shared with App.
    # Public: show, help, sort_key, group (user-facing command attributes)
    # Private: _is_resolved, _resolved_command (internal implementation details)

    @property
    def _is_resolved(self) -> bool:
        """Whether this lazy command has been resolved (imported)."""
        return self._resolved_app is not None

    @property
    def _resolved_command(self) -> "App | CommandSpec":
        """The resolved App if available, otherwise this CommandSpec."""
        return self._resolved_app if self._resolved_app is not None else self

    @property
    def group(self) -> "Group | str | tuple[Group | str, ...]":
        """Command groups for categorization in help output.

        For resolved commands, returns the App's group.
        For unresolved commands, returns empty tuple (placed in default group).
        """
        if self._resolved_app is not None:
            return self._resolved_app.group
        return ()

    @property
    def show(self) -> bool:
        """Whether this command should be shown in help.

        For resolved commands, returns the App's show value.
        For unresolved commands, returns app_kwargs.get("show", True).
        """
        if self._resolved_app is not None:
            return self._resolved_app.show
        return self.app_kwargs.get("show", True)

    @property
    def help(self) -> str:
        """Help text for this command.

        For resolved commands, returns the App's help property.
        For unresolved commands, uses AST-based extraction from the source file.

        Successful AST results are cached. Failures raise immediately and will
        retry on next call.

        Returns
        -------
        str
            The help text. Returns empty string if no help/docstring.

        Raises
        ------
        ValueError
            If unresolved and AST extraction fails (no source file, syntax error, etc.).
            The error message includes guidance on how to fix the issue.
        """
        # Explicit help is authoritative
        if (help_value := self.app_kwargs.get("help")) is not None:
            return str(help_value)

        # If resolved, use the App's help property
        if self._resolved_app is not None:
            return self._resolved_app.help or ""

        # Return cached AST result
        if self._ast_docstring is not None:
            return self._ast_docstring

        # Try AST extraction
        try:
            self._ast_docstring = extract_docstring_from_import_path(self.import_path)
            return self._ast_docstring
        except ValueError as e:
            raise ValueError(
                f"Cannot extract help text for lazy command {self.import_path!r}: {e}. "
                f"Provide explicit help via: app.command({self.import_path!r}, help='...')"
            ) from e

    @property
    def sort_key(self):
        """Sort key for ordering in help output.

        For resolved commands, returns the App's sort_key (with callables resolved).
        For unresolved commands, returns the raw value from app_kwargs since there's
        no app context to invoke callables.
        """
        if self._resolved_app is not None:
            return self._resolved_app.sort_key
        return self.app_kwargs.get("sort_key", None)

    def resolve(self, parent_app: "App") -> "App":
        """Import and resolve the command on first access.

        Parameters
        ----------
        parent_app : App
            Parent app to inherit defaults from (help_flags, version_flags, groups).
            Required to match the behavior of direct command registration.

        Returns
        -------
        App
            The resolved App instance, either imported directly or wrapping a function.

        Raises
        ------
        ValueError
            If import_path is not in the correct format "module.path:attribute_name".
        ImportError
            If the module cannot be imported.
        AttributeError
            If the attribute doesn't exist in the module.
        """
        if self._resolved_app is not None:
            return self._resolved_app

        # Parse import path
        module_path, _, attr_name = self.import_path.rpartition(":")
        if not module_path or not attr_name:
            raise ValueError(
                f"Invalid import path: {self.import_path!r}. Expected format: 'module.path:attribute_name'"
            )

        # Import the module and get the attribute
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Cannot import module {module_path!r} from {self.import_path!r}") from e

        try:
            target = getattr(module, attr_name)
        except AttributeError as e:
            raise AttributeError(
                f"Module {module_path!r} has no attribute {attr_name!r} (from import path {self.import_path!r})"
            ) from e

        # Wrap in App if needed
        from cyclopts.core import App

        if isinstance(target, App):
            # Validate that no kwargs were provided for App imports
            if self.app_kwargs:
                raise ValueError(
                    f"Cannot apply configuration to imported App. "
                    f"Import path {self.import_path!r} resolves to an App, "
                    f"but kwargs were specified: {self.app_kwargs!r}. "
                    f"Configure the App in its definition instead."
                )

            # Validate that the App's name matches the expected CLI command name
            # The name used for CLI registration is stored in self.name
            if self.name is not None and target.name[0] != self.name:
                raise ValueError(
                    f"Imported App name mismatch. "
                    f"Import path {self.import_path!r} resolves to an App with name={target.name[0]!r}, "
                    f"but it was registered with CLI command name={self.name!r}. "
                    f"Either use app.command('{self.import_path}', name='{target.name[0]}') "
                    f"or change the App's name to match."
                )

            # Copy parent groups if not set (matches direct App registration behavior)
            from cyclopts.core import _apply_parent_defaults_to_app

            _apply_parent_defaults_to_app(target, parent_app)

            self._resolved_app = target
        else:
            # It's a function - wrap it in an App with parent defaults
            # Match the behavior of direct function registration
            app_kwargs = dict(self.app_kwargs)  # Copy to avoid mutating

            from cyclopts.core import _apply_parent_groups_to_kwargs

            app_kwargs.setdefault("help_flags", parent_app.help_flags)
            app_kwargs.setdefault("version_flags", parent_app.version_flags)
            if "version" not in app_kwargs and parent_app.version is not None:
                app_kwargs["version"] = parent_app.version

            _apply_parent_groups_to_kwargs(app_kwargs, parent_app)

            self._resolved_app = App(name=self.name, **app_kwargs)
            self._resolved_app.default(target)

        # Hide help and version flags from subapp help output
        # This matches the behavior of direct App/function registration in core.py
        for flag in chain(self._resolved_app.help_flags, self._resolved_app.version_flags):
            self._resolved_app[flag].show = False

        return self._resolved_app
