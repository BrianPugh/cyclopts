from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union, cast

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.parameter import Parameter

from cyclopts.coercion import to_tuple_converter


def _group_default_parameter_must_be_none(instance, attribute, value: Optional["Parameter"]):
    if value is None:
        return

    if value.group:
        raise ValueError("Group default_parameter cannot have a group.")


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
