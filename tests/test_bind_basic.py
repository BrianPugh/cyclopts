import sys
from functools import partial
from typing import Annotated, Any, Optional

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import (
    ArgumentOrderError,
    CoercionError,
    CombinedShortOptionError,
    InvalidCommandError,
    MissingArgumentError,
    RepeatArgumentError,
    UnknownOptionError,
    UnusedCliTokensError,
)
from cyclopts.group import Group


def test_parse_known_args(app):
    @app.command
    def foo(a: int, b: int):
        pass

    command, _, unused_tokens, ignored = app.parse_known_args("foo 1 2 --bar 100")
    assert ignored == {}
    assert command == foo
    assert unused_tokens == ["--bar", "100"]


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
        "foo 1 2 --c=3",
        "foo --a 1 --b 2 --c 3",
        "foo --c 3 --b=2 --a 1",
    ],
)
def test_basic_1(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 --d 10 --some-flag",
        "foo --some-flag 1 --b=2 --c 3 --d 10",
        "foo 1 2 --some-flag 3 --d 10",
    ],
)
def test_basic_2(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int, d: int = 5, *, some_flag: bool = False):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3, d=10, some_flag=True)


def test_functools_partial_default(app, assert_parse_args):
    def foo(a: int, b: int, c: int):
        pass

    foo_partial = partial(foo, c=3)
    app.default(foo_partial)

    assert_parse_args(foo_partial, "1 2", a=1, b=2)


def test_functools_partial_command(app, assert_parse_args):
    def foo(a: int, b: int, c: int):
        pass

    foo_partial = partial(foo, c=3)
    app.command(foo_partial)

    assert_parse_args(foo_partial, "foo 1 2", a=1, b=2)


def test_basic_allow_hyphen_or_underscore(app, assert_parse_args):
    @app.default
    def default(foo_bar):
        pass

    assert_parse_args(default, "--foo-bar=bazz", "bazz")
    assert_parse_args(default, "--foo_bar=bazz", "bazz")


def test_out_of_order_mixed_positional_or_keyword(app, assert_parse_args):
    @app.command
    def foo(a, b, c):
        pass

    with pytest.raises(ArgumentOrderError):
        app.parse_args("foo --b=5 1 2", print_error=False, exit_on_error=False)


def test_command_rename(app, assert_parse_args):
    @app.command(name="bar")
    def foo():
        pass

    assert_parse_args(foo, "bar")


def test_command_delete(app, assert_parse_args):
    @app.command
    def foo():
        pass

    del app["foo"]

    with pytest.raises(InvalidCommandError):
        assert_parse_args(foo, "foo")


def test_command_multiple_alias(app, assert_parse_args):
    @app.command(name=["bar", "baz"])
    def foo():
        pass

    assert_parse_args(foo, "bar")
    assert_parse_args(foo, "baz")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_multiple_names(app, cmd_str, assert_parse_args):
    @app.command
    def foo(age: Annotated[int, Parameter(name=["--age", "--duration", "-a"])]):
        pass

    assert_parse_args(foo, cmd_str, age=10)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--job-name foo",
        "-j foo",
    ],
)
def test_short_name_j(app, cmd_str, assert_parse_args):
    """
    "-j" previously didn't work as a short-name because it's a valid complex value.

    https://github.com/BrianPugh/cyclopts/issues/328
    """

    @app.default
    def main(
        *,
        job_name: Annotated[str, Parameter(name=["--job-name", "-j"], negative=False)],
    ):
        pass

    assert_parse_args(main, cmd_str, job_name="foo")


def test_short_flag_combining(app, assert_parse_args):
    @app.default
    def main(
        foo: Annotated[bool, Parameter(name=("--foo", "-f"))] = False,
        bar: Annotated[bool, Parameter(name=("--bar", "-b"))] = False,
        my_list: Annotated[Optional[list], Parameter(negative=("--empty-my-list", "-e"))] = None,
    ):
        pass

    # Note: ``my_list`` is explicitly getting an empty list.
    assert_parse_args(main, "-bfe", foo=True, bar=True, my_list=[])


def test_short_flag_combining_unknown_flag(app, assert_parse_args):
    @app.default
    def main(
        foo: Annotated[bool, Parameter(name=("--foo", "-f"))] = False,
        bar: Annotated[bool, Parameter(name=("--bar", "-b"))] = False,
    ):
        pass

    with pytest.raises(UnknownOptionError):
        # The flag "-e" is unknown
        app("-be", exit_on_error=False)


def test_short_flag_combining_with_short_option(app, assert_parse_args):
    @app.default
    def main(
        *,
        foo: Annotated[bool, Parameter(name=("--foo", "-f"))] = False,
        bar: Annotated[str, Parameter(name=("--bar", "-b"))],
    ):
        pass

    with pytest.raises(CombinedShortOptionError):
        # The flag "-e" is unknown
        app("-fb", exit_on_error=False)


def test_short_integer_flag(app, assert_parse_args):
    @app.default
    def main(
        foo: Annotated[int, Parameter(name=("--foo", "-f"))],
        *,
        bar: Annotated[bool, Parameter(name=("--bar", "-1"))],
    ):
        pass

    assert_parse_args(main, "-1 -2", -2, bar=True)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_multiple_names_no_hyphen(app, cmd_str, assert_parse_args):
    @app.command
    def foo(age: Annotated[int, Parameter(name=["age", "duration", "-a"])]):
        pass

    assert_parse_args(foo, cmd_str, age=10)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion(app, cmd_str, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[Optional[int], Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Optional[int] = None):
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Pipe Typing Syntax")
@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion_python310_syntax(app, cmd_str, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[int | None, Parameter(help="help for a")] = None):  # pyright: ignore
            pass

    else:

        @app.command
        def foo(a: int | None = None):  # pyright: ignore
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--foo val1 --foo val2",
    ],
)
def test_exception_repeat_argument(app, cmd_str):
    @app.default
    def default(foo: str):
        pass

    with pytest.raises(RepeatArgumentError):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--foo val1 --foo val2",
    ],
)
def test_exception_repeat_argument_kwargs(app, cmd_str):
    @app.default
    def default(**kwargs: str):
        pass

    with pytest.raises(RepeatArgumentError):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


def test_exception_unused_token(app):
    @app.default
    def default(foo: str):
        pass

    with pytest.raises(UnusedCliTokensError):
        app.parse_args("foo bar", print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_no_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & no default should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")]):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_none_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & ``None`` default should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = None):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a=None):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_typed_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & typed default should be treated as a ``type(default)``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = 5):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a=5):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_any_hint(app, cmd_str, annotated, assert_parse_args):
    """The ``Any`` type hint should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Any = None):
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1",
        "0b1",
        "0x01",
        "1.0",
        "0.9",
    ],
)
def test_bind_int_advanced(app, cmd_str, assert_parse_args):
    @app.default
    def foo(a: int):
        pass

    assert_parse_args(foo, cmd_str, 1)


def test_bind_int_advanced_coercion_error(app):
    @app.default
    def foo(a: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("foo", exit_on_error=False)


def test_bind_override_app_groups(app):
    g_commands = Group("Custom Commands")
    g_arguments = Group("Custom Arguments")
    g_parameters = Group("Custom Parameters")

    @app.command(group_commands=g_commands, group_arguments=g_arguments, group_parameters=g_parameters)
    def foo():
        pass

    assert app["foo"].group_commands == g_commands
    assert app["foo"].group_arguments == g_arguments
    assert app["foo"].group_parameters == g_parameters


def test_bind_version(app, capsys):
    app.version = "1.2.3"
    actual_command, actual_bind, ignored = app.parse_args("--version")
    assert ignored == {}
    assert actual_command == app.version_print

    actual_command(*actual_bind.args, **actual_bind.kwargs)
    captured = capsys.readouterr()
    assert captured.out == "1.2.3\n"


def test_bind_version_factory(app, capsys):
    app.version = lambda: "1.2.3"
    actual_command, actual_bind, ignored = app.parse_args("--version")
    assert ignored == {}
    assert actual_command == app.version_print

    actual_command(*actual_bind.args, **actual_bind.kwargs)
    captured = capsys.readouterr()
    assert captured.out == "1.2.3\n"


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 3", MissingArgumentError),
        ("foo 1 2", MissingArgumentError),
    ],
)
def test_missing_keyword_argument(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, *, d: int):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 -- --2 3 4",
        "-- 1 --2 3 4",
        "--c=3 4 -- 1 --2",
        "--c 3 4 -- 1 --2",
    ],
)
def test_default_double_hyphen_end_of_options_delimiter(app, cmd_str, assert_parse_args):
    @app.default
    def foo(a: int, b: str, c: tuple[int, int]):
        pass

    assert_parse_args(foo, cmd_str, 1, "--2", (3, 4))


def test_disabled_double_hyphen_end_of_options_delimiter_from_app(app, assert_parse_args):
    app.end_of_options_delimiter = ""

    @app.default
    def foo(a: int, b: Annotated[str, Parameter(allow_leading_hyphen=True)], c: tuple[int, int]):
        pass

    assert_parse_args(foo, "1 -- 3 4", 1, "--", (3, 4))


def test_disabled_double_hyphen_end_of_options_delimiter_from_parse_args(app, assert_parse_args_config):
    @app.default
    def foo(a: int, b: Annotated[str, Parameter(allow_leading_hyphen=True)], c: tuple[int, int]):
        pass

    assert_parse_args_config({"end_of_options_delimiter": ""}, foo, "1 -- 3 4", 1, "--", (3, 4))


def test_end_of_options_delimiter_from_parse_args(app, assert_parse_args):
    app.end_of_options_delimiter = "AND"

    @app.default
    def foo(a: int, b: str, c: tuple[int, int]):
        pass

    assert_parse_args(foo, "1 AND --2 3 4", 1, "--2", (3, 4))


def test_end_of_options_delimiter_override(app, assert_parse_args_config):
    app.end_of_options_delimiter = "AND"  # This gets overridden

    @app.default
    def foo(a: int, b: str, c: tuple[int, int]):
        pass

    assert_parse_args_config({"end_of_options_delimiter": "DELIMIT"}, foo, "1 DELIMIT --2 3 4", 1, "--2", (3, 4))
