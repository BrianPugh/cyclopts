"""TypedDict.

TODO/Notes:
    * total=False/True (>=3.8)
        * MyDict.__total__
    * MyDict.__required_keys__ frozenset  (>= 3.9)
    * MyDict.__optional_keys__ frozenset  (>= 3.9)
    * Required/NotRequired (>= 3.11)
"""

import sys
from textwrap import dedent
from typing import List, TypedDict

import pytest

from cyclopts.exceptions import MissingArgumentError

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required
else:
    from typing import NotRequired, Required


class MyDict(TypedDict):
    my_int: int
    my_str: str
    my_list: list
    my_list_int: List[int]


def test_bind_typed_dict(app, assert_parse_args):
    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(
        foo,
        "foo --d.my_int=5 --d.my_str=bar --d.my-list=a --d.my-list=b --d.my-list-int=1 --d.my-list-int=2",
        d={
            "my_int": 5,
            "my_str": "bar",
            "my_list": ["a", "b"],
            "my_list_int": [1, 2],
        },
    )


def test_bind_typed_dict_missing_arg(app, console):
    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo --d.my_int=5 --d.my_str=bar",
            console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Missing argument for keys ['--d.my_list', '--d.my_list_int'].      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_typed_dict_total_false(app, assert_parse_args):
    class MyDict(TypedDict, total=False):
        my_int: int
        my_str: str

    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(foo, "foo --d.my_str=bar", d={"my_str": "bar"})


def test_bind_typed_dict_not_required(app, assert_parse_args):
    class MyDict(TypedDict):
        my_int: int
        my_str: NotRequired[str]

    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(foo, "foo --d.my_int=5", d={"my_int": 5})


def test_bind_typed_dict_required(app, assert_parse_args):
    class MyDict(TypedDict, total=False):
        my_int: Required[int]
        my_str: str

    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(foo, "foo --d.my_int=5", d={"my_int": 5})
