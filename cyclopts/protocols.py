import inspect
from typing import Any, Callable, Protocol, Type


class Dispatcher(Protocol):
    def __call__(self, command: Callable, bound: inspect.BoundArguments, /) -> Any:
        ...
