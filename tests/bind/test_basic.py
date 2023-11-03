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


def test_basic_1(app):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    def run(s):
        actual_command, actual_bind, unused_args = app.parse_known_args(s)
        assert actual_command == foo
        assert actual_bind == expected_bind
        assert unused_args == []

    run("foo 1 2 3")
    run("foo --a 1 --b 2 --c 3")
    run("foo --c 3 1 2")
    run("foo --c 3 --b=2 1")
    run("foo --c 3 --b=2 --a 1")
