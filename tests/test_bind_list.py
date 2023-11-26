import inspect
from typing import List, Optional


def test_pos_list(app):
    @app.command
    def foo(a: List[int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind([1, 2, 3])

    actual_command, actual_bind = app.parse_args("foo 1 2 3")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_keyword_list(app):
    @app.command
    def foo(a: List[int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind([1, 2, 3])

    actual_command, actual_bind = app.parse_args("foo --a=1 --a=2 --a 3")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_keyword_list_pos(app):
    @app.command
    def foo(a: List[int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind([1, 2, 3])

    actual_command, actual_bind = app.parse_args("foo 1 2 3")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_keyword_optional_list_none_default(app):
    @app.command
    def foo(a: Optional[List[int]] = None):
        assert a is None

    signature = inspect.signature(foo)
    expected_bind = signature.bind()

    actual_command, actual_bind = app.parse_args("foo")
    assert actual_command == foo
    assert actual_bind == expected_bind

    foo(*actual_bind.args, **actual_bind.kwargs)
