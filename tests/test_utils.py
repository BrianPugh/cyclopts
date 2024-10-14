import inspect
from typing import List

import pytest

from cyclopts.utils import ParameterDict, Sentinel, grouper, signature


@pytest.fixture
def parameter_dict():
    return ParameterDict()


def test_parameter_dict_immutable(parameter_dict):
    def foo(a: int, b: int = 3):
        pass

    parameters = dict(signature(foo).parameters)

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

    parameters = dict(signature(foo).parameters)
    a, b = parameters.values()
    c = inspect.Parameter("c", inspect.Parameter.POSITIONAL_OR_KEYWORD)

    for name, parameter in parameters.items():
        parameter_dict[parameter] = name

    assert len(parameter_dict) == 2

    for name, parameter in parameters.items():
        assert parameter_dict[parameter] == name

    # Test __contains__
    assert parameters["a"] in parameter_dict
    assert parameters["b"] in parameter_dict

    # Test __iter__
    assert list(parameter_dict) == [a, b]

    # Test setdefault
    assert parameter_dict.setdefault(a, "foo") == "a"
    assert parameter_dict.setdefault(c, "foo") == "foo"

    # test __delitem__
    del parameter_dict[parameters["a"]]
    assert parameters["a"] not in parameter_dict

    # Test clear
    parameter_dict.clear()
    assert len(parameter_dict) == 0


def test_parameter_dict_invalid_key(parameter_dict):
    with pytest.raises(TypeError):
        parameter_dict["foo"]


def test_parameter_dict_invalid_contains(parameter_dict):
    with pytest.raises(TypeError):
        # Assert is only here to make the linter happy.
        # Tests __contains__ magic method.
        assert "foo" not in parameter_dict  # pyright: ignore[reportUnusedExpression]


def test_grouper():
    assert [(1,), (2,), (3,), (4,)] == list(grouper([1, 2, 3, 4], 1))
    assert [(1, 2), (3, 4)] == list(grouper([1, 2, 3, 4], 2))
    assert [(1, 2, 3, 4)] == list(grouper([1, 2, 3, 4], 4))

    with pytest.raises(ValueError):
        grouper([1, 2, 3, 4], 3)


def test_sentinel():
    class SENTINEL_VALUE(Sentinel):  # noqa: N801
        pass

    assert str(SENTINEL_VALUE) == "<SENTINEL_VALUE>"
    assert bool(SENTINEL_VALUE) is False
