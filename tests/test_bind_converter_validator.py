from typing import Annotated
from unittest.mock import Mock

import pytest

from cyclopts import Parameter, ValidationError
from cyclopts.exceptions import CoercionError


@pytest.fixture
def validator():
    return Mock()


def test_custom_converter(app, assert_parse_args):
    def custom_converter(type_, tokens):
        return 2 * int(tokens[0].value)

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    assert_parse_args(foo, "5", age=10)


def test_custom_converter_dict(app, assert_parse_args):
    def custom_converter(type_, tokens):
        return {k: 2 * int(v[0].value) for k, v in tokens.items()}

    @app.default
    def foo(*, color: Annotated[dict[str, int], Parameter(converter=custom_converter)]):
        pass

    assert_parse_args(foo, "--color.red 5 --color.green 10", color={"red": 10, "green": 20})


def test_custom_converter_user_value_error_single_token(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5", exit_on_error=False)
    assert str(e.value) == 'Invalid value for "AGE": unable to convert "5" into int.'


def test_custom_converter_user_value_error_multi_token(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(age: Annotated[tuple[int, int], Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5 6", exit_on_error=False)
    assert str(e.value) == 'Invalid value for "--age": unable to convert value to tuple[int, int].'


def test_custom_converter_user_value_error_with_message(app):
    def custom_converter(type_, tokens):
        raise ValueError("Some user-provided message.")

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5", exit_on_error=False)
    assert str(e.value) == "Some user-provided message."


def test_custom_converter_user_kwargs_error(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(**kwargs: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--foo 5", exit_on_error=False)
    assert str(e.value) == 'Invalid value for "--foo": unable to convert "5" into int.'


def test_custom_converter_user_kwargs_error_with_message(app):
    def custom_converter(type_, tokens):
        raise ValueError("Some user-provided message.")

    @app.default
    def foo(**kwargs: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--foo 5", exit_on_error=False)
    assert str(e.value) == "Invalid value for --foo: Some user-provided message."


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

    def custom_converter(type_, tokens):
        return 2 * int(tokens[0].value)

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
