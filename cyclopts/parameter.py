import inspect
import typing
from typing import Callable, Optional

from attrs import frozen

from cyclopts.exceptions import RepeatKeywordError


@frozen
class Parameter:
    # User Options
    name: str = ""
    coercion: Optional[Callable] = None
    show_default = True
    help: str = ""


def get_hint_param(parameter: inspect.Parameter):
    """Get the type hint and ``Parameter`` from a possibly annotated type hint."""
    hint = parameter.annotation
    args = typing.get_args(hint)

    if args:
        hint = args[0]
        annotations = [x for x in args[1:] if isinstance(x, Parameter)]
        if len(annotations) > 2:
            raise RepeatKeywordError
        elif len(annotations) == 1:
            return hint, annotations[0]
        else:
            return hint, Parameter()
    else:
        return hint, Parameter()
