import inspect

import pytest
from typing_extensions import Annotated

from cyclopts import Parameter


def test_custom_converter(app):
    def custom_converter(type_, *args):
        return 2 * int(args[0])

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args("5")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_custom_validator(app):
    def custom_validator(type_, arg):
        if not (0 < arg < 150):
            raise ValueError("An unreasonable age was entered.")

    @app.default
    def foo(age: Annotated[int, Parameter(validator=custom_validator)]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args("10")
    assert actual_command == foo
    assert actual_bind == expected_bind

    with pytest.raises(ValueError):
        app.parse_args("200")


def test_custom_converter_and_validator(app):
    def custom_validator(type_, arg):
        if not (0 < arg < 150):
            raise ValueError("An unreasonable age was entered.")

    def custom_converter(type_, *args):
        return 2 * int(args[0])

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter, validator=custom_validator)]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args("5")
    assert actual_command == foo
    assert actual_bind == expected_bind

    with pytest.raises(ValueError):
        app.parse_args("200")
