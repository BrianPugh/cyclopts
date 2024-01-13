import inspect
from typing import List

import pytest

from cyclopts.utils import ParameterDict


@pytest.fixture
def parameter_dict():
    return ParameterDict()


def test_parameter_dict_immutable(parameter_dict):
    def foo(a: int, b: int = 3):
        pass

    parameters = dict(inspect.signature(foo).parameters)

    for name, parameter in parameters.items():
        parameter_dict[parameter] = name

    for name, parameter in parameters.items():
        assert parameter_dict[parameter] == name

    # Test __contains__
    assert parameters["a"] in parameter_dict
    assert parameters["b"] in parameter_dict


def test_parameter_dict_mutable(parameter_dict):
    def foo(a: int, b: List[int] = []):  # noqa: B006
        pass

    parameters = dict(inspect.signature(foo).parameters)

    for name, parameter in parameters.items():
        parameter_dict[parameter] = name

    assert len(parameter_dict) == 2

    for name, parameter in parameters.items():
        assert parameter_dict[parameter] == name

    # Test __contains__
    assert parameters["a"] in parameter_dict
    assert parameters["b"] in parameter_dict

    del parameter_dict[parameters["a"]]
    assert parameters["a"] not in parameter_dict


def test_parameter_dict_invalid_key(parameter_dict):
    with pytest.raises(TypeError):
        parameter_dict["foo"]


def test_parameter_dict_invalid_contains(parameter_dict):
    with pytest.raises(TypeError):
        # Assert is only here to make the linter happy.
        # Tests __contains__ magic method.
        assert "foo" not in parameter_dict  # pyright: ignore[reportUnusedExpression]
