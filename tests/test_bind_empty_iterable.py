import pytest


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-list", []),
        ("--empty-my-list=True", []),
        ("--empty-my-list=False", None),
    ],
)
def test_optional_list_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_list: list[int] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-set", set()),
        ("--empty-my-set=True", set()),
        ("--empty-my-set=False", None),
    ],
)
def test_optional_set_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_set: set[int] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)
