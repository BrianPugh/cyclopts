import inspect
from typing import List, Literal, Optional

from cyclopts import coercion
from cyclopts.coercion import Pipeline, get_coercion


def test_get_coercion_bool():
    def foo(a: bool = False):
        pass

    def bar(a: Optional[bool] = None):
        pass

    for f in [foo, bar]:
        signature = inspect.signature(f)
        parameter = list(signature.parameters.values())[0]
        assert (Pipeline([coercion.bool]), False) == get_coercion(parameter)


def test_get_coercion_list_int():
    def foo(a: List[int]):
        pass

    parameter = list(inspect.signature(foo).parameters.values())[0]
    assert (Pipeline([coercion.int]), True) == get_coercion(parameter)


def test_get_coercion_literal():
    def foo(a: Literal[1, 2, 3]):
        pass

    parameter = list(inspect.signature(foo).parameters.values())[0]
    assert (Pipeline([coercion.int]), True) == get_coercion(parameter)  # TODO
