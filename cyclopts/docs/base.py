"""Base utilities for documentation generation."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.help import HelpPanel

from cyclopts.command_spec import CommandSpec
from cyclopts.help import format_doc, format_usage


class BaseDocGenerator:
    """Base class for documentation generators with shared utilities."""

    @staticmethod
    def get_app_info(app: "App", command_chain: list[str] | None = None) -> tuple[str, str, str]:
        """Get app name, full command path, and title.

        Parameters
        ----------
        app : App
            The cyclopts App instance.
        command_chain : Optional[List[str]]
            Chain of parent commands leading to this app.

        Returns
        -------
        Tuple[str, str, str]
            (app_name, full_command, title)
        """
        if not command_chain:
            app_name = app.name[0]
            full_command = app_name
            title = app_name
        else:
            app_name = command_chain[0] if command_chain else app.name[0]
            full_command = " ".join(command_chain)
            title = full_command

        return app_name, full_command, title

    @staticmethod
    def build_command_chain(command_chain: list[str] | None, command_name: str, app_name: str) -> list[str]:
        """Build command chain for a subcommand.

        Parameters
        ----------
        command_chain : Optional[List[str]]
            Current command chain.
        command_name : str
            Name of the subcommand.
        app_name : str
            Name of the root app.

        Returns
        -------
        List[str]
            Updated command chain.
        """
        if command_chain:
            return command_chain + [command_name]
        else:
            return [app_name, command_name]

    @staticmethod
    def should_skip_command(command_name: str, subapp: "App", parent_app: "App", include_hidden: bool) -> bool:
        """Check if a command should be skipped.

        Parameters
        ----------
        command_name : str
            Name of the command.
        subapp : App
            The subcommand App instance.
        parent_app : App
            The parent App instance.
        include_hidden : bool
            Whether to include hidden commands.

        Returns
        -------
        bool
            True if command should be skipped.
        """
        if command_name in parent_app._help_flags or command_name in parent_app._version_flags:
            return True

        if not isinstance(subapp, type(parent_app)):
            return True

        if not include_hidden and not subapp.show:
            return True

        return False

    @staticmethod
    def filter_help_entries(panel: "HelpPanel", include_hidden: bool) -> list[Any]:
        """Filter help panel entries based on visibility settings.

        Parameters
        ----------
        panel : HelpPanel
            The help panel to filter.
        include_hidden : bool
            Whether to include hidden entries.

        Returns
        -------
        List[Any]
            Filtered panel entries.
        """
        if include_hidden:
            return panel.entries

        return [
            e
            for e in panel.entries
            if not (e.names and all(n.startswith("--help") or n.startswith("--version") or n == "-h" for n in e.names))
        ]

    @staticmethod
    def extract_description(app: "App", help_format: str) -> Any | None:
        """Extract app description.

        Parameters
        ----------
        app : App
            The App instance.
        help_format : str
            Help format type.

        Returns
        -------
        Optional[Any]
            The extracted description object, or None.
        """
        description = format_doc(app, help_format)
        return description

    @staticmethod
    def extract_usage(app: "App") -> Any | None:
        """Extract usage string.

        Parameters
        ----------
        app : App
            The App instance.

        Returns
        -------
        Optional[Any]
            The extracted usage object, or None.
        """
        if app.usage is not None:
            return app.usage if app.usage else None

        usage = format_usage(app, [])
        return usage

    @staticmethod
    def format_usage_line(usage_text: str, command_chain: list[str], prefix: str = "$") -> str:
        """Format usage line with proper command path.

        Parameters
        ----------
        usage_text : str
            Raw usage text.
        command_chain : List[str]
            Command chain for the app.
        prefix : str
            Prefix for the usage line (e.g., "$").

        Returns
        -------
        str
            Formatted usage line.
        """
        if not usage_text:
            return ""

        if "Usage:" in usage_text:
            usage_text = usage_text.replace("Usage:", "").strip()

        full_command = " ".join(command_chain) if command_chain else ""

        parts = usage_text.split(None, 1)
        if len(parts) > 1 and command_chain:
            usage_line = f"{prefix} {full_command} {parts[1]}"
        elif command_chain:
            usage_line = f"{prefix} {full_command}"
        else:
            usage_line = f"{prefix} {usage_text}"

        return usage_line.strip()

    @staticmethod
    def categorize_panels(
        help_panels_with_groups: list[tuple[Any, "HelpPanel"]], include_hidden: bool = False
    ) -> dict[str, list[tuple[Any, "HelpPanel"]]]:
        """Categorize help panels by type.

        Parameters
        ----------
        help_panels_with_groups : List[Tuple[Any, HelpPanel]]
            List of (group, panel) tuples.
        include_hidden : bool
            Whether to include hidden panels.

        Returns
        -------
        Dict[str, List[Tuple[Any, HelpPanel]]]
            Categorized panels with keys: 'commands', 'arguments', 'options', 'grouped'.
        """
        result = {"commands": [], "arguments": [], "options": [], "grouped": []}

        for group, panel in help_panels_with_groups:
            if not include_hidden and group and not group.show:
                continue

            if panel.format == "command":
                if not include_hidden:
                    filtered_entries = [
                        e
                        for e in panel.entries
                        if not (e.names and all(n in ["--help", "--version", "-h"] for n in e.names))
                    ]
                    if filtered_entries:
                        panel_copy = type(panel)(
                            entries=filtered_entries,
                            title=panel.title,
                            description=panel.description,
                            format=panel.format,
                        )
                        result["commands"].append((group, panel_copy))
                else:
                    result["commands"].append((group, panel))
            elif panel.format == "parameter":
                title = panel.title
                if title == "Arguments":
                    result["arguments"].append((group, panel))
                elif title and title not in ["Parameters", "Options"]:
                    result["grouped"].append((group, panel))
                else:
                    args = []
                    opts = []
                    for entry in panel.entries:
                        # Simple heuristic: positional args are required with no default
                        is_positional = entry.required and entry.default is None
                        if is_positional:
                            args.append(entry)
                        else:
                            opts.append(entry)

                    if args:
                        panel_copy = type(panel)(
                            entries=args, title="Arguments", description=panel.description, format=panel.format
                        )
                        result["arguments"].append((group, panel_copy))

                    if opts:
                        panel_copy = type(panel)(
                            entries=opts, title="Options", description=panel.description, format=panel.format
                        )
                        result["options"].append((group, panel_copy))

        return result

    @staticmethod
    def iterate_commands(app: "App", include_hidden: bool = False):
        """Iterate through app commands, yielding valid resolved subapps.

        Automatically resolves CommandSpec instances to App instances.

        Parameters
        ----------
        app : App
            The App instance.
        include_hidden : bool
            Whether to include hidden commands.

        Yields
        ------
        Tuple[str, App]
            (command_name, resolved_subapp) for each valid command.
        """
        if not app._commands:
            return

        for name, app_or_spec in app._commands.items():
            if name in app._help_flags or name in app._version_flags:
                continue

            # Resolve CommandSpec to App
            subapp = app_or_spec.resolve(app) if isinstance(app_or_spec, CommandSpec) else app_or_spec

            if not isinstance(subapp, type(app)):
                continue

            if not include_hidden and not subapp.show:
                continue

            yield name, subapp
