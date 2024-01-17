import itertools
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, cast

from attrs import define, field

from cyclopts.utils import Sentinel, is_iterable

if TYPE_CHECKING:
    from cyclopts.parameter import Parameter

from cyclopts._convert import to_tuple_converter
from cyclopts.utils import resolve_callables


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group:
        raise ValueError("Group default_parameter cannot have a group.")


# Used for Group.sorted
_sort_key_counter = itertools.count()


NO_USER_SORT_KEY = Sentinel("NO_USER_SORT_KEY")


@define
class Group:
    name: str = ""

    help: str = ""

    # All below parameters are keyword-only
    _show: Optional[bool] = field(default=None, alias="show", kw_only=True)

    _sort_key: Any = field(
        default=None,
        alias="sort_key",
        converter=lambda x: NO_USER_SORT_KEY if x is None else x,
    )

    converter: Optional[Callable] = field(default=None, kw_only=True)

    # This can ONLY ever be a Tuple[Callable, ...]
    validator: Union[None, Callable, Iterable[Callable]] = field(
        default=None,
        converter=lambda x: cast(Tuple[Callable, ...], to_tuple_converter(x)),
        kw_only=True,
    )

    default_parameter: Optional["Parameter"] = field(
        default=None,
        validator=_group_default_parameter_must_be_none,
        kw_only=True,
    )

    def __str__(self):
        return self.name

    @property
    def show(self):
        return bool(self.name) if self._show is None else self._show

    @show.setter
    def show(self, value):
        self._show = value

    @property
    def sort_key(self):
        return None if self._sort_key is NO_USER_SORT_KEY else self._sort_key

    @sort_key.setter
    def sort_key(self, value):
        self._sort_key = value

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
    def create_ordered(cls, *args, sort_key=None, **kwargs):
        """Create a group with a globally incremented :attr:`~Group.sort_key`.

        Used to create a group that will be displayed **after** a previously declared :meth:`Group.create_ordered` group on the help-page.

        If a :attr:`~Group.sort_key` is provided, it is **prepended** to the globally incremented counter value (i.e. has priority during sorting).
        """
        count = next(_sort_key_counter)
        if sort_key is None:
            sort_key = (NO_USER_SORT_KEY, count)
        elif is_iterable(sort_key):
            sort_key = (tuple(sort_key), count)
        else:
            sort_key = (sort_key, count)
        return cls(*args, sort_key=sort_key, **kwargs)


@define
class GroupConverter:
    default_group: Group

    def __call__(self, input_value: Union[None, str, Group]) -> Group:
        if input_value is None:
            return self.default_group
        elif isinstance(input_value, str):
            return Group(input_value)
        elif isinstance(input_value, Group):
            return input_value
        else:
            raise TypeError


def sort_groups(groups: List[Group], attributes: List[Any]) -> Tuple[List[Group], List[Any]]:
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

    sort_key_panels: List[Tuple[Tuple, Tuple[Group, Any]]] = []
    ordered_no_user_sort_key_panels: List[Tuple[Tuple, Tuple[Group, Any]]] = []
    no_user_sort_key_panels: List[Tuple[Tuple, Tuple[Group, Any]]] = []

    for sort_key, (group, attribute) in sort_key__group_attributes:
        value = (group, attribute)
        if sort_key in (NO_USER_SORT_KEY, None):
            no_user_sort_key_panels.append(((group.name,), value))
        elif is_iterable(sort_key) and sort_key[0] in (NO_USER_SORT_KEY, None):
            ordered_no_user_sort_key_panels.append((sort_key[1:] + (group.name,), value))
        else:
            sort_key_panels.append(((sort_key, group.name), value))

    sort_key_panels.sort()
    ordered_no_user_sort_key_panels.sort()
    no_user_sort_key_panels.sort()

    combined = sort_key_panels + ordered_no_user_sort_key_panels + no_user_sort_key_panels

    out_groups, out_attributes = zip(*[x[1] for x in combined])

    return list(out_groups), list(out_attributes)
