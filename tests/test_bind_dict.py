import pytest


@pytest.mark.parametrize(
    "type_",
    [
        dict[str, str],
        dict,
        dict,
    ],
)
def test_bind_dict_str_to_str(app, assert_parse_args, type_):
    @app.command
    def foo(d: type_):  # pyright: ignore
        pass

    assert_parse_args(foo, "foo --d.key_1='val1' --d.key-2='val2'", d={"key_1": "val1", "key-2": "val2"})


def test_bind_dict_str_to_int_typing(app, assert_parse_args):
    @app.command
    def foo(d: dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})


def test_bind_dict_str_to_int_builtin(app, assert_parse_args):
    @app.command
    def foo(d: dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})
