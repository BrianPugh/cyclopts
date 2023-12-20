import inspect
from typing import List

from cyclopts.utils import ParameterDict


def test_parameter_dict_immutable():
    def foo(a: int, b: int = 3):
        pass

    parameter_dict = ParameterDict()
    parameters = dict(inspect.signature(foo).parameters)

    for name, parameter in parameters.items():
        parameter_dict[parameter] = name

    for name, parameter in parameters.items():
        assert parameter_dict[parameter] == name


def test_parameter_dict_mutable():
    def foo(a: int, b: List[int] = []):  # noqa: B006
        pass

    parameter_dict = ParameterDict()
    parameters = dict(inspect.signature(foo).parameters)

    for name, parameter in parameters.items():
        parameter_dict[parameter] = name

    for name, parameter in parameters.items():
        assert parameter_dict[parameter] == name
