import inspect
import sys

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts.bind import parameter2cli
from cyclopts.parameter import Parameter
from cyclopts.utils import ParameterDict


def test_parameter2cli_positional_or_keyword():
    def foo(a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(inspect.signature(foo).parameters.values())[0]
    actual = parameter2cli(foo)
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_positional_only():
    def foo(a: Annotated[int, Parameter(negative=())], /):
        pass

    a_iparam = list(inspect.signature(foo).parameters.values())[0]
    actual = parameter2cli(foo)
    assert actual == ParameterDict({a_iparam: ["A"]})


def test_parameter2cli_keyword_only():
    def foo(*, a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(inspect.signature(foo).parameters.values())[0]
    actual = parameter2cli(foo)
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_var_keyword():
    def foo(**a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(inspect.signature(foo).parameters.values())[0]
    actual = parameter2cli(foo)
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_var_positional():
    def foo(*a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(inspect.signature(foo).parameters.values())[0]
    actual = parameter2cli(foo)
    assert actual == ParameterDict({a_iparam: ["A"]})
