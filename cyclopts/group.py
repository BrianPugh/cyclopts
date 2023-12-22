import inspect
from typing import TYPE_CHECKING, Callable, List, Literal, Optional, Union

from attrs import define, field

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.parameter import Parameter


@define
class Group:
    name: str
    """
    Group name used for the help-panel and for group-referenced-by-string.
    """

    help: str = ""
    """
    Additional documentation show on help screen.
    """

    # All below parameters are keyword-only

    validator: Optional[Callable] = field(default=None, kw_only=True)
    """
    A callable where the CLI-provided group variables will be keyword-unpacked, regardless
    of their positional/keyword type in the command function signature.

    .. code-block:: python

        def validator(**kwargs):
            "Raise an exception if something is invalid."

    *Not invoked on command groups.*
    """

    default_parameter: Optional["Parameter"] = field(default=None, kw_only=True)
    """
    Default Parameter in the parameter-resolution-stack that goes
    between ``app.default_parameter`` and the function signature's Annotated Parameter.
    """

    default: Optional[Literal["Arguments", "Parameters", "Commands"]] = field(default=None, kw_only=True)
    """
    Only one group registered to an app can have each non-``None`` option.
    """

    # Private Internal Use
    _children: List[Union[inspect.Parameter, "App"]] = field(factory=list, init=False)
    """
    List of ``inspect.Parameter`` or ``App`` (for commands) included in the group.
    Externally populated.
    """

    def __str__(self):
        return self.name
