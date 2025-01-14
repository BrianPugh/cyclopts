from typing import TYPE_CHECKING, Any, Union

from cyclopts.group import Group

if TYPE_CHECKING:
    from cyclopts.core import App


def _create_or_append(
    group_mapping: list[tuple[Group, list[Any]]],
    group: Union[str, Group],
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


def groups_from_app(app: "App") -> list[tuple[Group, list["App"]]]:
    """Extract Group/App association from all commands of ``app``.

    Returns
    -------
    list
        List of items where each item is a tuple containing:

        * :class:`.Group` - The group

        * ``list[App]`` - The list of app subcommands within the group.
    """
    assert not isinstance(app.group_commands, str)
    group_commands = app.group_commands or Group.create_default_commands()
    group_mapping: list[tuple[Group, list[App]]] = [
        (group_commands, []),
    ]

    subapps = list(app.subapps)

    # 2 iterations need to be performed:
    # 1. Extract out all Group objects as they may have additional configuration.
    # 2. Assign/Create Groups out of the strings, as necessary.
    for subapp in subapps:
        assert isinstance(subapp.group, tuple)
        for group in subapp.group:
            if isinstance(group, Group):
                for mapping in group_mapping:
                    if mapping[0] is group:
                        break
                    elif mapping[0].name == group.name:
                        raise ValueError(f'Command Group "{group.name}" already exists.')
                else:
                    group_mapping.append((group, []))

    for subapp in subapps:
        if subapp.group:
            assert isinstance(subapp.group, tuple)
            for group in subapp.group:
                _create_or_append(group_mapping, group, subapp)
        else:
            _create_or_append(group_mapping, app.group_commands or Group.create_default_commands(), subapp)

    # Remove the empty groups
    group_mapping = [x for x in group_mapping if x[1]]

    # Sort alphabetically by name
    group_mapping.sort(key=lambda x: x[0].name)

    return group_mapping


def inverse_groups_from_app(input_app: "App") -> list[tuple["App", list[Group]]]:
    out = []
    seen_apps = []
    for group, apps in groups_from_app(input_app):
        for app in apps:
            try:
                index = seen_apps.index(app)
            except ValueError:
                index = len(out)
                out.append((app, []))
                seen_apps.append(app)
            out[index][1].append(group)
    return out
