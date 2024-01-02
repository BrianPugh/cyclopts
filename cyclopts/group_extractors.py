import inspect
from typing import TYPE_CHECKING, Callable, Iterable, List, Literal, Optional, Tuple, Union

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.core import App

from cyclopts.coercion import to_tuple_converter
from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter


def _extract_default_groups(cparams) -> Tuple[Optional[Group], Optional[Group]]:
    default_arguments, default_parameters = None, None
    for cparam in cparams:
        if cparam.group is None:
            continue

        for group in cparam.group:  # pyright: ignore
            if isinstance(group, Group):
                if group.is_default_arguments:
                    if default_arguments is None:
                        default_arguments = group
                    else:
                        raise ValueError('Cannot specify more than 1 default="Arguments"')
                elif group.is_default_parameters:
                    if default_parameters is None:
                        default_parameters = group
                    else:
                        raise ValueError('Cannot specify more than 1 default="Parameters"')
                elif group.is_default_commands:
                    raise NotImplementedError("Unexpected group type.")
            elif isinstance(group, str):
                # For an implied group (string-only), then ``is_default_*==False``.
                pass
            else:
                raise NotImplementedError("Unexpected group type.")

    return default_arguments, default_parameters


def _default_groups_from_function(
    f: Callable,
    default_parameter: Optional[Parameter] = None,
    default_group_arguments: Optional[Group] = None,
    default_group_parameters: Optional[Group] = None,
) -> Tuple[Group, Group]:
    signature = inspect.signature(f)
    iparams = list(signature.parameters.values())
    cparams = []

    for iparam in iparams:
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter=default_parameter)
        cparams.append(cparam)

    default_arguments, default_parameters = _extract_default_groups(cparams)
    if default_arguments is None:
        default_arguments = default_group_arguments or Group("Arguments", is_default_arguments=True)
    if default_parameters is None:
        default_parameters = default_group_parameters or Group("Parameters", is_default_parameters=True)
    return default_arguments, default_parameters


def _create_or_append(
    group_mapping: List[Tuple[Group, List[inspect.Parameter]]], group: Union[str, Group], iparam: inspect.Parameter
):
    # updates group_mapping inplace.

    if isinstance(group, str):
        group = Group(group)
    elif isinstance(group, Group):
        pass
    else:
        raise TypeError

    for mapping in group_mapping:
        if mapping[0] == group:
            mapping[1].append(iparam)
            break
    else:
        group_mapping.append((group, [iparam]))


def groups_from_function(
    f: Callable,
    default_parameter: Optional[Parameter] = None,
    default_group_arguments: Optional[Group] = None,
    default_group_parameters: Optional[Group] = None,
) -> List[Tuple[Group, List[inspect.Parameter]]]:
    """Get a list of all groups WITH their children populated.

    The exact Group instances are not guarenteeed to be the same.
    """
    group_arguments, group_parameters = _default_groups_from_function(
        f,
        default_parameter,
        default_group_arguments,
        default_group_parameters,
    )
    group_mapping: List[Tuple[Group, List[inspect.Parameter]]] = [
        (group_arguments, []),
        (group_parameters, []),
    ]

    # Assign each parameter to a group
    for iparam in inspect.signature(f).parameters.values():
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter=default_parameter)
        if cparam.group:
            for group in cparam.group:  # pyright: ignore
                if (
                    isinstance(group, Group)
                    and group.default_parameter is not None
                    and group.default_parameter.group is not None
                ):
                    # This shouldn't be possible due to ``Group`` internal checks.
                    raise ValueError("Group.default_parameter cannot have a specified group.")
                _create_or_append(group_mapping, group, iparam)
        else:
            if iparam.kind == iparam.POSITIONAL_ONLY:
                _create_or_append(group_mapping, group_arguments, iparam)
            else:
                _create_or_append(group_mapping, group_parameters, iparam)

    # Remove the empty groups
    group_mapping = [x for x in group_mapping if x[1]]

    return group_mapping


def groups_from_commands(apps: List["App"]) -> List[Group]:
    raise NotImplementedError
