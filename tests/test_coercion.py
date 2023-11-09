import inspect
from typing import List, Optional

from cyclopts import coercion
from cyclopts.coercion import get_coercion


def test_get_coercion_bool():
    def foo(a: bool = False):
        pass

    def bar(a: Optional[bool] = None):
        pass

    for f in [foo, bar]:
        signature = inspect.signature(f)
        parameter = list(signature.parameters.values())[0]
        assert (coercion.bool, False) == get_coercion(parameter)


def test_get_coercion_list_int():
    def foo(a: List[int]):
        pass

    signature = inspect.signature(foo)
    parameter = list(signature.parameters.values())[0]
    assert (coercion.int, True) == get_coercion(parameter)
