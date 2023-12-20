import functools
import inspect
from collections.abc import MutableMapping
from typing import Any, Iterator


def record_init_kwargs(target: str):
    """Class decorator that records init argument names as a tuple to ``target``."""

    def decorator(cls):
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, **kwargs):
            original_init(self, **kwargs)
            # Circumvent frozen protection.
            object.__setattr__(self, target, tuple(kwargs.keys()))

        cls.__init__ = new_init
        return cls

    return decorator


class ParameterDict(MutableMapping):
    """A dictionary implementation that can handle ``inspect.Parameter`` as keys.

    Traditional dictionaries don't always work because ``inspect.Parameter.default`` may be mutable.
    """

    def __init__(self):
        self.store = {}

    def _param_key(self, param: inspect.Parameter) -> tuple:
        if not isinstance(param, inspect.Parameter):
            raise TypeError("Key must be an inspect.Parameter")
        return (param.name, param.kind, param.annotation)

    def __getitem__(self, key: inspect.Parameter) -> Any:
        return self.store[self._param_key(key)]

    def __setitem__(self, key: inspect.Parameter, value: Any) -> None:
        self.store[self._param_key(key)] = value

    def __delitem__(self, key: inspect.Parameter) -> None:
        del self.store[self._param_key(key)]

    def __iter__(self) -> Iterator[inspect.Parameter]:
        return iter(self.store)

    def __len__(self) -> int:
        return len(self.store)

    def setdefault(self, key: inspect.Parameter, default: Any = None) -> Any:
        return self.store.setdefault(self._param_key(key), default)
