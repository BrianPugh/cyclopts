import inspect
import sys
from unittest.mock import Mock

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter, ValidationError


@pytest.fixture
def validator():
    return Mock()


def test_custom_converter(app, assert_parse_args):
    def custom_converter(type_, *args):
        return 2 * int(args[0])

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    assert_parse_args(foo, "5", age=10)


def test_custom_validator_positional_or_keyword(app, assert_parse_args, validator):
    @app.default
    def foo(age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "10", age=10)
    validator.assert_called_once_with(int, 10)


def test_custom_validator_var_keyword(app, assert_parse_args, validator):
    @app.default
    def foo(**age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "--age=10", age=10)
    validator.assert_called_once_with(int, 10)


def test_custom_validator_var_positional(app, assert_parse_args, validator):
    @app.default
    def foo(*age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "10", 10)
    validator.assert_called_once_with(int, 10)


def test_custom_validators(app, assert_parse_args):
    def lower_bound(type_, value):
        if value <= 0:
            raise ValueError("An unreasonable age was entered.")

    def upper_bound(type_, value):
        if value > 150:
            raise ValueError("An unreasonable age was entered.")

    @app.default
    def foo(age: Annotated[int, Parameter(validator=[lower_bound, upper_bound])]):
        pass

    assert_parse_args(foo, "10", 10)

    with pytest.raises(ValidationError):
        app.parse_args("0", print_error=False, exit_on_error=False)

    with pytest.raises(ValidationError):
        app.parse_args("200", print_error=False, exit_on_error=False)


def test_custom_converter_and_validator(app, assert_parse_args, validator):
    def custom_validator(type_, value):
        if not (0 < value < 150):
            raise ValueError("An unreasonable age was entered.")

    def custom_converter(type_, *args):
        return 2 * int(args[0])

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter, validator=validator)]):
        pass

    assert_parse_args(foo, "5", 10)

    validator.assert_called_once_with(int, 10)


def test_custom_command_validator(app, assert_parse_args):
    validator = Mock()

    @app.default(validator=validator)
    def foo(a: int, b: int, c: int):
        pass

    assert_parse_args(foo, "1 2 3", 1, 2, 3)
    validator.assert_called_once_with(a=1, b=2, c=3)


def test_custom_command_converter(app, assert_parse_args):
    def converter(**kwargs):
        assert kwargs["a"] == 1
        assert kwargs["b"] == 2
        assert kwargs["c"] == 3
        return {"a": 100, "b": 200}

    @app.default(converter=converter)
    def foo(a: int, b: int, c: int = 5):
        pass

    assert_parse_args(foo, "1 2 3", 100, 200)
