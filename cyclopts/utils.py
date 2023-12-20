import functools
import inspect
from collections.abc import MutableMapping
from typing import Any, Dict, Iterator, Optional


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
    """A dictionary implementation that can handle mutable ``inspect.Parameter`` as keys."""

    def __init__(self, store: Optional[Dict[inspect.Parameter, Any]] = None):
        self.store = {}
        self.reverse_mapping = {}
        if store is not None:
            for k, v in store.items():
                self[k] = v

    def _param_key(self, param: inspect.Parameter) -> tuple:
        if not isinstance(param, inspect.Parameter):
            raise TypeError(f"Key must be an inspect.Parameter; got {type(param)}.")
        return (param.name, param.kind, param.annotation)

    def __getitem__(self, key: inspect.Parameter) -> Any:
        return self.store[self._param_key(key)]

    def __setitem__(self, key: inspect.Parameter, value: Any) -> None:
        processed_key = self._param_key(key)
        self.store[processed_key] = value
        self.reverse_mapping[processed_key] = key

    def __delitem__(self, key: inspect.Parameter) -> None:
        processed_key = self._param_key(key)
        del self.store[processed_key]
        del self.reverse_mapping[processed_key]

    def __iter__(self) -> Iterator[inspect.Parameter]:
        return iter(self.reverse_mapping.values())

    def __len__(self) -> int:
        return len(self.store)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, inspect.Parameter):
            raise TypeError(f"Key must be an inspect.Parameter; got {type(key)}.")
        return self._param_key(key) in self.store

    def setdefault(self, key: inspect.Parameter, default: Any = None) -> Any:
        processed_key = self._param_key(key)
        if processed_key not in self.store:
            self.reverse_mapping[processed_key] = key
        return self.store.setdefault(processed_key, default)
