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

from attrs import field

from cyclopts.utils import UNSET, SortHelper, frozen, is_iterable, resolve_callables, to_tuple_converter

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
    """Sort groups for the help-page.

    Note, much logic is similar to here and ``HelpPanel.sort``, so any changes here should probably be reflected over there as well.
    """
    assert len(groups) == len(attributes)

    if not groups:
        return groups, attributes

    sorted_entries = SortHelper.sort(
        [
            SortHelper(resolve_callables(group._sort_key, group), group.name, (group, attribute))
            for group, attribute in zip(groups, attributes)
        ]
    )
    out_groups, out_attributes = zip(*[x.value for x in sorted_entries])
    return list(out_groups), list(out_attributes)
