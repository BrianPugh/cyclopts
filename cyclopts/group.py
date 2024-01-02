from typing import TYPE_CHECKING, Callable, Iterable, Optional, Union

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

    validator: Union[None, Callable, Iterable[Callable]] = field(
        default=None,
        converter=to_tuple_converter,
        kw_only=True,
    )

    default_parameter: Optional["Parameter"] = field(
        default=None,
        validator=_group_default_parameter_must_be_none,
        kw_only=True,
    )

    # Flags for default groups
    # These are flags instead of an enum since a Group can be multiple defaults.
    is_default_arguments: bool = field(default=False, kw_only=True)
    is_default_parameters: bool = field(default=False, kw_only=True)
    is_default_commands: bool = field(default=False, kw_only=True)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.name == other.name
        else:
            return False


def get_group_default_parameter(app: "App", group: Group) -> "Parameter":
    # TODO: get rid of this
    from cyclopts.parameter import Parameter

    return Parameter.combine(app.default_parameter, group.default_parameter)
