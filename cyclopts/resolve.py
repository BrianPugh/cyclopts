"""Cyclopts central Group/Parameter resolver.

All fallbacks and configuration hierarchy resolution should occur here.
All downstream functions should consume data "as is" without fallbacks.
"""

import inspect
from typing import Callable, Dict, List, Optional, Tuple, cast

from docstring_parser import parse as docstring_parse

from cyclopts.exceptions import DocstringError
from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter
from cyclopts.utils import ParameterDict


def _list_index(lst: List, key: Callable) -> int:
    """Returns index of first occurrence in list."""
    for i, element in enumerate(lst):
        if key(element):
            return i
    raise ValueError


def _has_unparsed_parameters(f: Callable, *args) -> bool:
    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        _, cparam = get_hint_parameter(iparam, *args)

        if not cparam.parse:
            return True
    return False


def _resolve_groups(
    f: Callable,
    app_parameter: Optional[Parameter],
    group_arguments: Group,
    group_parameters: Group,
):
    """Resolves groups and mapping iparams to groups.

    cparams will have to be externally re-resolved to include group.default_parameter
    """
    resolved_groups = []
    iparam_to_groups = ParameterDict()

    signature = inspect.signature(f)

    for iparam in signature.parameters.values():
        _, cparam = get_hint_parameter(iparam, app_parameter)

        if not cparam.parse:
            continue

        if cparam.group:
            groups = cparam.group
        elif iparam.kind is iparam.POSITIONAL_ONLY:
            groups = (group_arguments,)
        else:
            groups = (group_parameters,)

        iparam_to_groups.setdefault(iparam, [])

        for group in groups:  # pyright: ignore
            if isinstance(group, str):
                try:
                    index = _list_index(resolved_groups, lambda x: x.name == group)  # noqa: B023
                except ValueError:
                    group = Group(group)
                    resolved_groups.append(group)
                else:
                    group = resolved_groups[index]
                iparam_to_groups[iparam].append(group)
            elif isinstance(group, Group):
                # Ensure a different, but same-named group doesn't already exist
                if any(group is not x and x.name == group.name for x in resolved_groups):
                    raise ValueError("Cannot register 2 distinct Group objects with same name.")

                if group.default_parameter is not None and group.default_parameter.group:
                    # This shouldn't be possible due to ``Group`` internal checks.
                    raise ValueError("Group.default_parameter cannot have a specified group.")  # pragma: no cover

                try:
                    index = resolved_groups.index(group)
                except ValueError:
                    resolved_groups.append(group)
                else:
                    group = resolved_groups[index]
                iparam_to_groups[iparam].append(group)
            else:
                raise TypeError

    return resolved_groups, iparam_to_groups


def _resolve_docstring(f) -> ParameterDict:
    signature = inspect.signature(f)
    f_docstring = docstring_parse(f.__doc__)

    iparam_to_docstring_cparam = ParameterDict()

    for dparam in f_docstring.params:
        try:
            iparam = signature.parameters[dparam.arg_name]
        except KeyError:
            # Even though we could pass/continue, we're raising
            # an exception because the developer really aught to know.
            raise DocstringError(
                f"Docstring parameter {dparam.arg_name} has no equivalent in function signature."
            ) from None
        else:
            iparam_to_docstring_cparam[iparam] = Parameter(help=dparam.description)

    return iparam_to_docstring_cparam


class ResolvedCommand:
    command: Callable
    groups: List[Group]
    groups_iparams: List[Tuple[Group, List[inspect.Parameter]]]
    iparam_to_groups: ParameterDict
    iparam_to_cparam: ParameterDict
    name_to_iparam: Dict[str, inspect.Parameter]

    def __init__(
        self,
        f,
        app_parameter: Optional[Parameter] = None,
        group_arguments: Optional[Group] = None,
        group_parameters: Optional[Group] = None,
        parse_docstring: bool = True,
    ):
        """
        ``app_parameter`` implicitly has the command-group parameter already resolved.

        Parameters
        ----------
        f: Callable
            Function to resolve annotated :class:`Parameters`.
        app_parameter:
            Default :class:`Parameter` to inherit configuration from.
        group_arguments: Optional[Group]
            Default :class:`Group` for positional-only arguments.
        group_parameters: Optional[Group]
            Default :class:`Group` for non-positional-only arguments.
        parse_docstring: bool
            Parse the docstring to populate Parameter ``help``, if not explicitly set.
            Disable for improved performance if ``help`` won't be used in the resulting :class:`Parameter`.
        """
        if group_arguments is None:
            group_arguments = Group.create_default_arguments()
        if group_parameters is None:
            group_parameters = Group.create_default_parameters()

        self.command = f
        signature = inspect.signature(f)
        self.name_to_iparam = cast(Dict[str, inspect.Parameter], signature.parameters)

        # Get:
        # 1. Fully resolved and created Groups.
        # 2. A mapping of inspect.Parameter to those Group objects.
        self.groups, self.iparam_to_groups = _resolve_groups(f, app_parameter, group_arguments, group_parameters)

        # Fully Resolve each Cyclopts Parameter
        self.iparam_to_cparam = ParameterDict()
        iparam_to_docstring_cparam = _resolve_docstring(f) if parse_docstring else ParameterDict()
        for iparam, groups in self.iparam_to_groups.items():
            if iparam.kind in (iparam.POSITIONAL_ONLY, iparam.VAR_POSITIONAL):
                # Name is only used for help-string
                names = [iparam.name.upper()]
            else:
                names = ["--" + iparam.name.replace("_", "-")]

            default_name_parameter = Parameter(name=names)

            cparam = get_hint_parameter(
                iparam,
                app_parameter,
                *(x.default_parameter for x in groups),
                iparam_to_docstring_cparam.get(iparam),
                default_name_parameter,
                Parameter(required=iparam.default is iparam.empty),
            )[1]
            self.iparam_to_cparam[iparam] = cparam

        self.bind = signature.bind_partial if _has_unparsed_parameters(f, app_parameter) else signature.bind

        # Create a convenient group-to-iparam structure
        self.groups_iparams = [
            (
                group,
                [iparam for iparam, groups in self.iparam_to_groups.items() if group in groups],
            )
            for group in self.groups
        ]
