import inspect
import sys

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter, ValidationError


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
    def custom_validator(type_, value):
        if not (0 < value < 150):
            raise ValueError("An unreasonable age was entered.")

    @app.default
    def foo(age: Annotated[int, Parameter(validator=custom_validator)]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args("10")
    assert actual_command == foo
    assert actual_bind == expected_bind

    with pytest.raises(ValidationError):
        app.parse_args("200", print_error=False, exit_on_error=False)


def test_custom_converter_and_validator(app):
    def custom_validator(type_, value):
        if not (0 < value < 150):
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

    with pytest.raises(ValidationError):
        app.parse_args("200", print_error=False, exit_on_error=False)
