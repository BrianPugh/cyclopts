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
    group_mapping: List[Tuple[Group, List["App"]]] = [
        (app.group_commands, []),
    ]

    for subapp in app._commands.values():
        if subapp.group:
            for group in subapp.group:
                _create_or_append(group_mapping, group, subapp)
        else:
            _create_or_append(group_mapping, app.group_commands, subapp)

    # Remove the empty groups
    group_mapping = [x for x in group_mapping if x[1]]

    return group_mapping
