from typing import TYPE_CHECKING, Any, List, Tuple, Union

if TYPE_CHECKING:
    from cyclopts.core import App

from cyclopts.group import Group


def _create_or_append(
    group_mapping: List[Tuple[Group, List[Any]]],
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


def groups_from_app(app: "App") -> List[Tuple[Group, List["App"]]]:
    """Extract Group/App association."""
    group_mapping: List[Tuple[Group, List["App"]]] = [
        (app.group_commands, []),
    ]

    # 2 iterations need to be performed:
    # 1. Extract out all Group objects as they may have additional configuration.
    # 2. Assign/Create Groups out of the strings, as necessary.

    for subapp in app._commands.values():
        for group in subapp.group:
            if isinstance(group, Group):
                for mapping in group_mapping:
                    if mapping[0] == group:
                        break
                    elif mapping[0].name == group.name:
                        raise ValueError(f'Command Group "{group.name}" already exists.')
                else:
                    group_mapping.append((group, []))

    for subapp in app._commands.values():
        if subapp.group:
            for group in subapp.group:
                _create_or_append(group_mapping, group, subapp)
        else:
            _create_or_append(group_mapping, app.group_commands, subapp)

    # Remove the empty groups
    group_mapping = [x for x in group_mapping if x[1]]

    # Sort alphabetically by name
    group_mapping.sort(key=lambda x: x[0].name)

    return group_mapping