import itertools
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, cast

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.parameter import Parameter

from cyclopts.coercion import to_tuple_converter


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group:
        raise ValueError("Group default_parameter cannot have a group.")


# Used for Group.sorted
_sort_key_counter = itertools.count()


@define
class Group:
    name: str = ""

    help: str = ""

    # All below parameters are keyword-only
    _show: Optional[bool] = field(default=None, alias="show", kw_only=True)

    sort_key: Any = field(default=None)

    converter: Optional[Callable] = field(default=None, kw_only=True)

    validator: Tuple[Callable, ...] = field(
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
    def create_sorted(cls, *args, sort_key=None, **kwargs):
        """Create a group with a globally incremented :attr:`~Group.sort_key`.

        Used to create a group that will be displayed **after** a previously declared :meth:`Group.create_sorted` group on the help-page.

        If a :attr:`~Group.sort_key` is provided, it is **prepended** to the globally incremented counter value (i.e. has priority during sorting).
        """
        if callable(sort_key):
            raise TypeError(f"Cannot use a callable sort_key with {cls.__name__}.create_sorted.")
        count = next(_sort_key_counter)
        sort_key = count if sort_key is None else (sort_key, count)
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
    sort_key__group_attributes = [
        (
            group.sort_key if group.sort_key is None or not callable(group.sort_key) else group.sort_key(group),
            (group, attribute),
        )
        for group, attribute in zip(groups, attributes)
    ]

    # Sort panels here!
    sort_key_panels, none_sort_key_panels = [], []

    for sort_key, (group, attribute) in sort_key__group_attributes:
        if sort_key is None:
            none_sort_key_panels.append(((group.name, 1), (group, attribute)))
        else:
            sort_key_panels.append(((sort_key, group.name), (group, attribute)))

    sort_key_panels.sort()
    none_sort_key_panels.sort()

    combined = sort_key_panels + none_sort_key_panels

    out_groups, out_attributes = zip(*[x[1] for x in combined])

    return out_groups, out_attributes
