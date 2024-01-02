from typing import TYPE_CHECKING, Callable, Iterable, Optional, Tuple, Union, cast

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.parameter import Parameter

from cyclopts.coercion import to_tuple_converter


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group is not None:
        raise ValueError("Group default_parameter cannot have a group.")


@define
class Group:
    name: str

    help: str = ""

    # All below parameters are keyword-only
    show: bool = field(default=True, kw_only=True)

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

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.name == other.name
        else:
            return False


def to_group_converter(default_group: Group):
    def converter(input_value: Union[None, str, Group]) -> Group:
        if input_value is None:
            return default_group
        elif isinstance(input_value, str):
            return Group(input_value)
        elif isinstance(input_value, Group):
            return input_value
        else:
            raise TypeError

    return converter


def to_groups_converter(input_value: Union[None, str, Group, Iterable[Union[str, Group]]]) -> Tuple[Group, ...]:
    if input_value is None:
        return ()
    elif isinstance(input_value, str):
        return (Group(input_value),)
    elif isinstance(input_value, Group):
        return (input_value,)
    else:
        return tuple(Group(x) if isinstance(x, str) else x for x in input_value)


def get_group_default_parameter(app: "App", group: Group) -> "Parameter":
    # TODO: get rid of this
    from cyclopts.parameter import Parameter

    return Parameter.combine(app.default_parameter, group.default_parameter)
