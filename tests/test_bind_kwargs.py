import inspect
from typing import List


def test_kwargs_list_int(app):
    @app.command
    def foo(a: int, **kwargs: List[int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, bar=[2, 3], baz=[4])

    actual_command, actual_bind = app.parse_args("foo 1 --bar=2 --baz=4 --bar 3")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_kwargs_int(app):
    @app.command
    def foo(a: int, **kwargs: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, bar=2, baz=3)

    actual_command, actual_bind = app.parse_args("foo 1 --bar=2 --baz 3")
    assert actual_command == foo
    assert actual_bind == expected_bind
