from typing import TYPE_CHECKING, Any, NamedTuple

from cyclopts.group import Group

if TYPE_CHECKING:
    from cyclopts.command_spec import CommandSpec
    from cyclopts.core import App


class RegisteredCommand(NamedTuple):
    """A command with the names it was registered under.

    Attributes
    ----------
    names : tuple[str, ...]
        All names (including aliases) this command is registered under.
    command : App | CommandSpec
        The command's App instance (resolved) or CommandSpec (lazy/unresolved).
    """

    names: tuple[str, ...]
    command: "App | CommandSpec"


def _create_or_append(
    group_mapping: list[tuple[Group, list[Any]]],
    group: str | Group,
    element: Any,
):
    # updates group_mapping inplace.
    if isinstance(group, str):
        group = Group(group)
    elif isinstance(group, Group):
        pass
    else:
        raise TypeError

    for mapping in group_mapping:
        if mapping[0].name == group.name:
            mapping[1].append(element)
            break
    else:
        group_mapping.append((group, [element]))


def groups_from_app(app: "App") -> list[tuple[Group, list[RegisteredCommand]]]:
    """Extract Group/App association from all commands of ``app``.

    Returns
    -------
    list
        List of items where each item is a tuple containing:

        * :class:`.Group` - The group

        * ``list[RegisteredCommand]`` - List of RegisteredCommand tuples containing
          the registered names and command (App or CommandSpec) for each command.

    Notes
    -----
    Unresolved lazy commands are included with CommandSpec as the command,
    allowing help generation without triggering imports. Lazy commands are
    placed in the default commands group since we cannot access their .group
    attribute without importing.

    Limitation: Group objects defined in unresolved lazy modules won't be
    available until those modules are imported. To avoid this, define Group
    objects in non-lazy modules. See docs/source/lazy_loading.rst for details.
    """
    assert not isinstance(app.group_commands, str)
    group_commands = app.group_commands or Group.create_default_commands()

    # First pass: collect all registered names and unique commands
    entry_names: dict[int, list[str]] = {}
    unique_commands: dict[int, App | CommandSpec] = {}

    for name in app:
        command = app._get_item(name, recurse_meta=True)._resolved_command
        entry_id = id(command)
        entry_names.setdefault(entry_id, []).append(name)
        unique_commands[entry_id] = command

    group_mapping: list[tuple[Group, list[RegisteredCommand]]] = [
        (group_commands, []),
    ]

    # Extract Group objects from commands that have them
    # Both App and CommandSpec have .group property (CommandSpec returns () if unresolved)
    for command in unique_commands.values():
        assert isinstance(command.group, tuple)
        for group in command.group:
            if isinstance(group, Group):
                for mapping in group_mapping:
                    if mapping[0] is group:
                        break
                    elif mapping[0].name == group.name:
                        raise ValueError(f'Command Group "{group.name}" already exists.')
                else:
                    group_mapping.append((group, []))

    # Assign commands to groups with their registered names
    for entry_id, command in unique_commands.items():
        names = tuple(entry_names[entry_id])
        entry = RegisteredCommand(names=names, command=command)

        assert isinstance(command.group, tuple)
        if command.group:
            for group in command.group:
                _create_or_append(group_mapping, group, entry)
        else:
            # Commands without groups go to default group
            _create_or_append(group_mapping, group_commands, entry)

    # Remove empty groups
    group_mapping = [x for x in group_mapping if x[1]]

    # Sort alphabetically by name
    group_mapping.sort(key=lambda x: x[0].name)

    return group_mapping


def inverse_groups_from_app(input_app: "App") -> list[tuple["App", list[Group]]]:
    out = []
    seen_apps = []
    for group, registered_commands in groups_from_app(input_app):
        for registered_command in registered_commands:
            # Skip unresolved lazy commands - they don't have a resolved App
            if not registered_command.command._is_resolved:
                continue
            app = registered_command.command
            try:
                index = seen_apps.index(app)
            except ValueError:
                index = len(out)
                out.append((app, []))
                seen_apps.append(app)
            out[index][1].append(group)
    return out
