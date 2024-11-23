import itertools
from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    Union,
    cast,
)

from attrs import field, frozen

from cyclopts.utils import UNSET, Sentinel, is_iterable, to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.argument import ArgumentCollection
    from cyclopts.parameter import Parameter


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group:
        raise ValueError("Group default_parameter cannot have a group.")


# Used for Group.sorted
_sort_key_counter = itertools.count()


@frozen
class Group:
    name: str = ""

    help: str = ""

    # All below parameters are keyword-only
    _show: Optional[bool] = field(default=None, alias="show", kw_only=True)

    _sort_key: Any = field(
        default=None,
        alias="sort_key",
        converter=lambda x: UNSET if x is None else x,
        kw_only=True,
    )

    # This can ONLY ever be a Tuple[Callable, ...]
    validator: Union[None, Callable[["ArgumentCollection"], Any], Iterable[Callable[["ArgumentCollection"], Any]]] = (
        field(
            default=None,
            converter=lambda x: cast(tuple[Callable, ...], to_tuple_converter(x)),
            kw_only=True,
        )
    )

    default_parameter: Optional["Parameter"] = field(
        default=None,
        validator=_group_default_parameter_must_be_none,
        kw_only=True,
    )

    @property
    def show(self):
        return bool(self.name) if self._show is None else self._show

    @property
    def sort_key(self):
        return None if self._sort_key is UNSET else self._sort_key

    @classmethod
    def create_default_arguments(cls):
        return cls("Arguments")

    @classmethod
    def create_default_parameters(cls):
        return cls("Parameters")

    @classmethod
    def create_default_commands(cls):
        return cls("Commands")

    @classmethod
    def create_ordered(cls, name="", help="", *, show=None, sort_key=None, validator=None, default_parameter=None):
        """Create a group with a globally incrementing :attr:`~Group.sort_key`.

        Used to create a group that will be displayed **after** a previously instantiated :meth:`Group.create_ordered` group on the help-page.

        Parameters
        ----------
        name: str
            Group name used for the help-page and for group-referenced-by-string.
            This is a title, so the first character should be capitalized.
            If a name is not specified, it will not be shown on the help-page.
        help: str
            Additional documentation shown on the help-page.
            This will be displayed inside the group's panel, above the parameters/commands.
        show: Optional[bool]
            Show this group on the help-page.
            Defaults to :obj:`None`, which will only show the group if a ``name`` is provided.
        sort_key: Any
            If provided, **prepended** to the globally incremented counter value (i.e. has priority during sorting).

        validator: Union[None, Callable[["ArgumentCollection"], Any], Iterable[Callable[["ArgumentCollection"], Any]]]
            Group validator to collectively apply.
        default_parameter: Optional[cyclopts.Parameter]
            Default parameter for elements within the group.
        """
        count = next(_sort_key_counter)
        if sort_key is None:
            sort_key = (UNSET, count)
        elif is_iterable(sort_key):
            sort_key = (tuple(sort_key), count)
        else:
            sort_key = (sort_key, count)
        return cls(
            name,
            help,
            show=show,
            sort_key=sort_key,
            validator=validator,
            default_parameter=default_parameter,
        )


def sort_groups(groups: list[Group], attributes: list[Any]) -> tuple[list[Group], list[Any]]:
    """Sort groups for the help-page."""
    assert len(groups) == len(attributes)
    if not groups:
        return groups, attributes

    # Resolve callable ``sort_key``
    sort_key__group_attributes = []
    for group, attribute in zip(groups, attributes):
        value = (group, attribute)
        if callable(group._sort_key) or is_iterable(group._sort_key):
            sort_key__group_attributes.append((resolve_callables(group._sort_key, group), value))
        else:
            sort_key__group_attributes.append((group._sort_key, value))

    sort_key_panels: list[tuple[tuple, tuple[Group, Any]]] = []
    ordered_no_user_sort_key_panels: list[tuple[tuple, tuple[Group, Any]]] = []
    no_user_sort_key_panels: list[tuple[tuple, tuple[Group, Any]]] = []

    for sort_key, (group, attribute) in sort_key__group_attributes:
        value = (group, attribute)
        if sort_key in (UNSET, None):
            no_user_sort_key_panels.append(((group.name,), value))
        elif is_iterable(sort_key) and sort_key[0] in (UNSET, None):
            ordered_no_user_sort_key_panels.append((sort_key[1:] + (group.name,), value))
        else:
            sort_key_panels.append(((sort_key, group.name), value))

    sort_key_panels.sort()
    ordered_no_user_sort_key_panels.sort()
    no_user_sort_key_panels.sort()

    combined = sort_key_panels + ordered_no_user_sort_key_panels + no_user_sort_key_panels

    out_groups, out_attributes = zip(*[x[1] for x in combined])

    return list(out_groups), list(out_attributes)


def resolve_callables(t, *args, **kwargs):
    """Recursively resolves callable elements in a tuple."""
    if isinstance(t, type(Sentinel)):
        return t

    if callable(t):
        return t(*args, **kwargs)

    resolved = []
    for element in t:
        if isinstance(element, type(Sentinel)):
            resolved.append(element)
        elif callable(element):
            resolved.append(element(*args, **kwargs))
        elif is_iterable(element):
            resolved.append(resolve_callables(element, *args, **kwargs))
        else:
            resolved.append(element)
    return tuple(resolved)
