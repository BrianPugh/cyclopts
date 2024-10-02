from typing import List


def test_kwargs_list_int(app, assert_parse_args):
    @app.command
    def foo(a: int, **kwargs: List[int]):
        pass

    assert_parse_args(foo, "foo 1 --bar=2 --baz=4 --bar 3", 1, bar=[2, 3], baz=[4])


def test_kwargs_int(app, assert_parse_args):
    @app.command
    def foo(a: int, **kwargs: int):
        pass

    assert_parse_args(foo, "foo 1 --bar=2 --baz 3", 1, bar=2, baz=3)
    assert_parse_args(foo, "foo 1", 1)


def test_args_and_kwargs_int(app, assert_parse_args):
    @app.command
    def foo(a: int, *args: int, **kwargs: int):
        pass

    assert_parse_args(foo, "foo 1 2 3 4 5 --bar=2 --baz 3", 1, 2, 3, 4, 5, bar=2, baz=3)
    assert_parse_args(foo, "foo 1", 1)
