"""Generic caching utilities."""

import functools
from collections.abc import Callable
from typing import Any

from cyclopts.utils import Sentinel


class _CACHE_MISS(Sentinel):  # noqa: N801
    """Sentinel for cache misses (distinct from None which is a valid conversion result)."""


def cache(key_func: Callable[..., tuple]) -> Callable[[Callable], Callable]:
    """Decorator that caches function results based on a custom key function.

    Similar to functools.lru_cache, but with custom key generation.
    The decorated function gets a `cache_clear()` method to clear its cache.

    Parameters
    ----------
    key_func
        Function that takes the same arguments as the decorated function
        and returns a hashable cache key tuple.

    Example
    -------
    >>> def my_key(x, y):
    ...     return (x, id(y))
    >>> @cache(my_key)
    ... def my_func(x, y):
    ...     return expensive_computation(x, y)
    >>> my_func.cache_clear()  # Clear the cache
    """

    def decorator(func: Callable) -> Callable:
        func_cache: dict[tuple, Any] = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = key_func(*args, **kwargs)
            cached = func_cache.get(cache_key, _CACHE_MISS)
            if cached is not _CACHE_MISS:
                return cached

            result = func(*args, **kwargs)
            func_cache[cache_key] = result
            return result

        wrapper.cache_clear = func_cache.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
