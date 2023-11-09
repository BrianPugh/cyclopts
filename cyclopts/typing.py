import collections.abc
from typing import Iterable, List, Tuple, get_args, get_origin


def is_iterable_type_hint(type_hint):
    if isinstance(type_hint, type) and issubclass(type_hint, collections.abc.Iterable):
        return True
    origin_type = get_origin(type_hint)
    if origin_type and issubclass(origin_type, collections.abc.Iterable):
        return True
    return False
