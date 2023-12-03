import inspect
from typing import Any, Callable, Protocol, Type


class Converter(Protocol):
    def __call__(self, type_: Type, /, *args: str) -> Any:
        ...


class Validator(Protocol):
    def __call__(self, type_: Type, value: Any, /) -> None:
        ...


class Dispatcher(Protocol):
    def __call__(self, command: Callable, bound: inspect.BoundArguments, /) -> Any:
        ...
