import inspect
from typing import Optional, Union

import pytest
from typing_extensions import Annotated

import cyclopts
from cyclopts import Parameter


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 --b=2 3",
        "foo 1 2 3",
        "foo --a 1 --b 2 --c 3",
        "foo --c 3 1 2",
        "foo --c 3 --b=2 1",
        "foo --c 3 --b=2 --a 1",
    ],
)
def test_basic_1(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 --d 10 --some-flag",
        "foo --some-flag 1 --b=2 3 --d 10",
        "foo 1 2 --some-flag 3 --d 10",
    ],
)
def test_basic_2(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, d: int = 5, some_flag: bool = False):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3, d=10, some_flag=True)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_multiple_names(app, cmd_str):
    @app.command
    def foo(age: Annotated[int, Parameter(name=["--age", "--duration", "-a"])]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion(app, cmd_str, annotated):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[Optional[int], Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Optional[int] = None):
            pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert isinstance(actual_bind.args[0], int)
