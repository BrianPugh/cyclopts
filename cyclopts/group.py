import inspect
from typing import TYPE_CHECKING, Callable, Iterable, List, Literal, Optional, Union

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.parameter import Parameter

from cyclopts.coercion import to_tuple_converter


@define
class Group:
    name: str

    help: str = ""

    # All below parameters are keyword-only
    show: bool = field(default=True, kw_only=True)

    converter: Optional[Callable] = field(default=None)

    validator: Union[None, Callable, Iterable[Callable]] = field(default=None, converter=to_tuple_converter)

    default_parameter: Optional["Parameter"] = field(default=None, kw_only=True)

    default: Optional[Literal["Arguments", "Parameters", "Commands"]] = field(default=None, kw_only=True)

    # Private Internal Use
    _children: List[Union[inspect.Parameter, "App"]] = field(factory=list, init=False)
    """
    List of ``inspect.Parameter`` or ``App`` (for commands) included in the group.
    Externally populated.
    This is for private internal use and is initialized as an empty list.
    """

    def __str__(self):
        return self.name
