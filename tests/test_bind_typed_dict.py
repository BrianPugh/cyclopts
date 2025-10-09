import sys
from textwrap import dedent
from typing import Annotated, TypedDict

import pytest

from cyclopts import MissingArgumentError, Parameter
from cyclopts.exceptions import UnknownOptionError

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import NotRequired, Required
else:  # pragma: no cover
    from typing import NotRequired, Required


class MyDict(TypedDict):
    my_int: int
    my_str: str
    my_list: list
    my_list_int: list[int]


def test_bind_typed_dict(app, assert_parse_args):
    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(
        foo,
        "foo --d.my-int=5 --d.my-str=bar --d.my-list=a --d.my-list=b --d.my-list-int=1 --d.my-list-int=2",
        d={
            "my_int": 5,
            "my_str": "bar",
            "my_list": ["a", "b"],
            "my_list_int": [1, 2],
        },
    )


def test_bind_typed_dict_missing_arg_basic(app, console):
    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo --d.my-int=5 --d.my-str=bar",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--d.my-list" requires an argument.        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_typed_dict_missing_arg_flatten(app, console):
    @app.command
    def foo(d: Annotated[MyDict, Parameter(name="*")]):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--my-int" requires an argument.           │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_typed_dict_missing_arg_renamed_no_hyphen(app, console):
    class MyDict(TypedDict):
        my_int: int
        my_str: str
        my_list: Annotated[list, Parameter(name="your-list")]
        my_list_int: list[int]

    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo --d.my-int=5 --d.my-str=bar",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--d.your-list" requires an argument.      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_typed_dict_missing_arg_renamed_hyphen(app, console):
    class MyDict(TypedDict):
        my_int: int
        my_str: str
        my_list: Annotated[list, Parameter(name="--your-list")]
        my_list_int: list[int]

    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo --d.my-int=5 --d.my-str=bar",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--your-list" requires an argument.        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_typed_dict_missing_arg_nested(app, console):
    class User(TypedDict):
        name: str
        age: int

    class MyDict(TypedDict):
        my_int: int
        my_str: str
        my_user: User

    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(
            "foo --d.my-int=5 --d.my-str=bar --d.my-user.age=30",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--d.my-user.name" requires an argument.   │
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

    assert_parse_args(foo, "foo --d.my-str=bar", d={"my_str": "bar"})


def test_bind_typed_dict_not_required(app, assert_parse_args):
    class MyDict(TypedDict):
        my_int: int
        my_str: NotRequired[str]

    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(foo, "foo --d.my-int=5", d={"my_int": 5})


def test_bind_typed_dict_required(app, assert_parse_args):
    class MyDict(TypedDict, total=False):
        my_int: Required[int]
        my_str: str

    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(foo, "foo --d.my-int=5", d={"my_int": 5})


def test_bind_typed_dict_extra_field(app, console):
    @app.command
    def foo(d: MyDict):
        pass

    with console.capture() as capture, pytest.raises(UnknownOptionError):
        app.parse_args(
            "foo --d.my-int=5 --d.my-str=bar --d.my-list=a --d.my-list=b --d.my-list-int=1 --d.my-list-int=2 --d.extra-key=10",
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown option: "--d.extra-key".                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
