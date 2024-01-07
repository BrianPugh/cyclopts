from typing import TYPE_CHECKING, Callable, Optional, Tuple, Union, cast

from attrs import field, frozen

if TYPE_CHECKING:
    from cyclopts.parameter import Parameter

from cyclopts.coercion import to_tuple_converter


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group:
        raise ValueError("Group default_parameter cannot have a group.")


@frozen
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

    @classmethod
    def create_default_arguments(cls):
        return cls("Arguments")

    @classmethod
    def create_default_parameters(cls):
        return cls("Parameters")

    @classmethod
    def create_default_commands(cls):
        return cls("Commands")


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
