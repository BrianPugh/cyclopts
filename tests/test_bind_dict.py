import sys
from typing import Dict

import pytest


@pytest.mark.parametrize(
    "type_",
    [
        Dict[str, str],
        dict,
        Dict,
    ],
)
def test_bind_dict_str_to_str(app, assert_parse_args, type_):
    @app.command
    def foo(d: type_):
        pass

    assert_parse_args(foo, "foo --d.key_1='val1' --d.key-2='val2'", d={"key_1": "val1", "key-2": "val2"})


def test_bind_dict_str_to_int_typing(app, assert_parse_args):
    @app.command
    def foo(d: Dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Native Typing")
def test_bind_dict_str_to_int_builtin(app, assert_parse_args):
    @app.command
    def foo(d: Dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})
