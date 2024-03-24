import sys

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts.parameter import Parameter
from cyclopts.resolve import ResolvedCommand
from cyclopts.utils import ParameterDict, signature


def test_parameter2cli_positional_or_keyword(default_function_groups):
    def foo(a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(signature(foo).parameters.values())[0]
    actual = ResolvedCommand(foo, *default_function_groups).parameter2cli
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_positional_only(default_function_groups):
    def foo(a: Annotated[int, Parameter(negative=())], /):
        pass

    a_iparam = list(signature(foo).parameters.values())[0]
    actual = ResolvedCommand(foo, *default_function_groups).parameter2cli
    assert actual == ParameterDict({a_iparam: ["A"]})


def test_parameter2cli_keyword_only(default_function_groups):
    def foo(*, a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(signature(foo).parameters.values())[0]
    actual = ResolvedCommand(foo, *default_function_groups).parameter2cli
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_var_keyword(default_function_groups):
    def foo(**a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(signature(foo).parameters.values())[0]
    actual = ResolvedCommand(foo, *default_function_groups).parameter2cli
    assert actual == ParameterDict({a_iparam: ["--a"]})


def test_parameter2cli_var_positional(default_function_groups):
    def foo(*a: Annotated[int, Parameter(negative=())]):
        pass

    a_iparam = list(signature(foo).parameters.values())[0]
    actual = ResolvedCommand(foo, *default_function_groups).parameter2cli
    assert actual == ParameterDict({a_iparam: ["A"]})
