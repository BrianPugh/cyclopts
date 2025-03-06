import inspect
from typing import Any, Callable, Protocol


class Dispatcher(Protocol):
    def __call__(
        self, command: Callable[..., Any], bound: inspect.BoundArguments, ignored: dict[str, Any], /
    ) -> Any: ...
