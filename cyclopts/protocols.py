from typing import Any, Protocol, Type


class Converter(Protocol):
    def __call__(self, type_: Type, /, *args: str) -> Any:
        ...


class Validator(Protocol):
    def __call__(self, type_: Type, value: Any, /) -> None:
        ...
