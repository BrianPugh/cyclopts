import inspect

import pytest

import cyclopts


@pytest.fixture
def app():
    return cyclopts.App()


def test_missing_positional_type(app):
    with pytest.raises(cyclopts.MissingTypeError):

        @app.command
        def foo(a, b, c):
            pass


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
        "foo --a 1 --b 2 --c 3",
        "foo --c 3 1 2",
        "foo --c 3 --b=2 1",
        "foo --c 3 --b=2 --a 1",
        "foo 1 --b=2 3",
    ],
)
def test_basic_1(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind, unused_args = app.parse_known_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert unused_args == []
