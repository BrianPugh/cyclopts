from functools import partial
from typing import Annotated, Any

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import (
    ArgumentOrderError,
    CoercionError,
    MissingArgumentError,
    RepeatArgumentError,
    UnknownCommandError,
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

    with pytest.raises(UnknownCommandError):
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
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_alias(app, cmd_str, assert_parse_args):
    @app.command
    def foo(age: Annotated[int, Parameter(alias=["--duration", "-a"])]):
        pass

    assert_parse_args(foo, cmd_str, age=10)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_name_and_alias(app, cmd_str, assert_parse_args):
    """Weird use-case, but should be handled."""

    @app.command
    def foo(age: Annotated[int, Parameter(name="--age", alias=["--duration", "-a"])]):
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
        my_list: Annotated[list | None, Parameter(negative=("--empty-my-list", "-e"))] = None,
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

    # With GNU-style support, -fb is now valid: -f (flag) + -b (needs value from next token)
    # Since no next token exists, should raise MissingArgumentError
    with pytest.raises(MissingArgumentError):
        app("-fb", exit_on_error=False)

    # But -fb with a value should work
    assert_parse_args(main, "-fb value", foo=True, bar="value")


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
        def foo(a: Annotated[int | None, Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: int | None = None):
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


@pytest.mark.parametrize(
    "value",
    [
        "10000000000000001",
        "10000000000000011",
        "100000000000000111234",
    ],
)
def test_bind_large_int(app, assert_parse_args, value):
    """Test that large integers are parsed correctly without precision loss.

    Reproduces bug: https://github.com/BrianPugh/cyclopts/issues/581
    """

    @app.default
    def foo(a: int):
        pass

    assert_parse_args(foo, value, int(value))


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


# ============================================================================
# GNU-style combined short options tests
# Tests for the feature where short options can be combined with their values
# in a single token, similar to GNU getopt behavior.
#
# Examples:
#     -o9         →  -o with value "9"
#     -iuroot     →  -i (flag), -u with value "root"
#     -fvbfile    →  -f (flag), -v (flag), -b with value "file"
# ============================================================================


def test_single_short_option_with_attached_value(app, assert_parse_args):
    """Test that -o9 is equivalent to -o 9."""

    @app.default
    def main(output: Annotated[str, Parameter(name=("-o", "--output"))]):
        pass

    # Traditional syntax should still work
    assert_parse_args(main, "-o 9", output="9")
    assert_parse_args(main, "-o=9", output="9")

    # NEW: Attached value should work
    assert_parse_args(main, "-o9", output="9")


def test_single_short_option_with_attached_string_value(app, assert_parse_args):
    """Test that -ofile.txt works for string values."""

    @app.default
    def main(output: Annotated[str, Parameter(name=("-o", "--output"))]):
        pass

    # Traditional syntax
    assert_parse_args(main, "-o file.txt", output="file.txt")

    # NEW: Attached string value
    assert_parse_args(main, "-ofile.txt", output="file.txt")
    assert_parse_args(main, "-oroot", output="root")


def test_combined_flags_before_option_with_value(app, assert_parse_args):
    """Test sudo -iuroot style: flags followed by option with attached value."""

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
        interactive: Annotated[bool, Parameter(name=("-i", "--interactive"))] = False,
    ):
        pass

    # Traditional syntax
    assert_parse_args(main, "-i -u root", interactive=True, user="root")

    # NEW: GNU-style combined
    assert_parse_args(main, "-iuroot", interactive=True, user="root")


def test_multiple_flags_before_option_with_value(app, assert_parse_args):
    """Test multiple flags combined with an option that takes a value."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("-o", "--output"))],
        force: Annotated[bool, Parameter(name=("-f", "--force"))] = False,
        verbose: Annotated[bool, Parameter(name=("-v", "--verbose"))] = False,
    ):
        pass

    # Traditional syntax
    assert_parse_args(main, "-f -v -o file.txt", force=True, verbose=True, output="file.txt")

    # NEW: GNU-style combined
    assert_parse_args(main, "-fvofile.txt", force=True, verbose=True, output="file.txt")
    assert_parse_args(main, "-vfofile.txt", verbose=True, force=True, output="file.txt")


def test_option_with_value_at_end_consumes_next_token(app, assert_parse_args):
    """Test that -fu (without attached value) consumes next token."""

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
        force: Annotated[bool, Parameter(name=("-f", "--force"))] = False,
    ):
        pass

    # When -u is at the end without attached value, next token is the value
    assert_parse_args(main, "-fu root", force=True, user="root")


def test_option_with_value_in_middle_stops_processing(app, assert_parse_args):
    """Test that once we hit an option with a value, rest is consumed as the value."""

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
        force: Annotated[bool, Parameter(name=("-f", "--force"))] = False,
        verbose: Annotated[bool, Parameter(name=("-v", "--verbose"))] = False,
    ):
        pass

    # -fuvroot should be: -f (flag), -u with value "vroot"
    # The 'v' is NOT treated as a flag, it's part of the value
    assert_parse_args(main, "-fuvroot", force=True, user="vroot")


def test_combined_short_options_numeric_value(app, assert_parse_args):
    """Test numeric values attached to short options."""

    @app.default
    def main(
        port: Annotated[int, Parameter(name=("-p", "--port"))],
        verbose: Annotated[bool, Parameter(name=("-v", "--verbose"))] = False,
    ):
        pass

    # Traditional syntax
    assert_parse_args(main, "-v -p 8080", verbose=True, port=8080)

    # NEW: Attached numeric value
    assert_parse_args(main, "-vp8080", verbose=True, port=8080)
    assert_parse_args(main, "-p8080", port=8080)


def test_gnu_backward_compatibility_all_flags(app, assert_parse_args):
    """Test that combining only flags still works (no regression)."""

    @app.default
    def main(
        force: Annotated[bool, Parameter(name=("-f", "--force"))] = False,
        verbose: Annotated[bool, Parameter(name=("-v", "--verbose"))] = False,
        quiet: Annotated[bool, Parameter(name=("-q", "--quiet"))] = False,
    ):
        pass

    # This should continue to work as before
    assert_parse_args(main, "-fvq", force=True, verbose=True, quiet=True)
    assert_parse_args(main, "-qvf", quiet=True, verbose=True, force=True)


def test_gnu_backward_compatibility_space_separated(app, assert_parse_args):
    """Ensure traditional space-separated syntax still works."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("-o", "--output"))],
        user: Annotated[str, Parameter(name=("-u", "--user"))],
    ):
        pass

    # Traditional syntax must still work
    assert_parse_args(main, "-o file.txt -u root", output="file.txt", user="root")


def test_gnu_backward_compatibility_equals_syntax(app, assert_parse_args):
    """Ensure equals syntax still works."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("-o", "--output"))],
    ):
        pass

    # Equals syntax must still work
    assert_parse_args(main, "-o=file.txt", output="file.txt")
    assert_parse_args(main, "--output=file.txt", output="file.txt")


def test_empty_string_value_attached(app, assert_parse_args):
    """Test edge case: can we have an empty attached value?"""

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
        force: Annotated[bool, Parameter(name=("-f", "--force"))] = False,
    ):
        pass

    # -fu with no characters after should consume next token
    # This is actually the same as test_option_with_value_at_end_consumes_next_token
    assert_parse_args(main, "-fu root", force=True, user="root")


def test_counting_parameter_combined(app, assert_parse_args):
    """Test that counting parameters work in combinations."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("-o", "--output"))],
        verbose: Annotated[int, Parameter(name=("-v", "--verbose"), count=True)] = 0,
    ):
        pass

    # Multiple v's for verbosity levels, then option with value
    assert_parse_args(main, "-vvvofile.txt", verbose=3, output="file.txt")
    assert_parse_args(main, "-vvofile.txt", verbose=2, output="file.txt")


def test_only_option_no_flags(app, assert_parse_args):
    """Test single option with attached value (simplest case)."""

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
    ):
        pass

    assert_parse_args(main, "-uroot", user="root")
    assert_parse_args(main, "-u root", user="root")


def test_long_option_should_not_be_split(app, assert_parse_args):
    """Test that long options (--) are NOT affected by this feature."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("--output",))],
    ):
        pass

    # Long options should still require space or equals
    assert_parse_args(main, "--output file.txt", output="file.txt")
    assert_parse_args(main, "--output=file.txt", output="file.txt")

    # --outputfile.txt should NOT be split into --output with value file.txt
    # It should be treated as an unknown option "--outputfile.txt"
    # (This maintains current behavior)


def test_hyphenated_value_attached(app, assert_parse_args):
    """Test that hyphenated values work when attached."""

    @app.default
    def main(
        output: Annotated[str, Parameter(name=("-o", "--output"))],
    ):
        pass

    # Value containing hyphens
    assert_parse_args(main, "-omy-file.txt", output="my-file.txt")
    assert_parse_args(main, "-o--weird-value", output="--weird-value")


def test_special_characters_in_attached_value(app, assert_parse_args):
    """Test special characters in attached values."""

    @app.default
    def main(
        pattern: Annotated[str, Parameter(name=("-p", "--pattern"))],
    ):
        pass

    # Special characters should be preserved
    assert_parse_args(main, "-p*.txt", pattern="*.txt")
    assert_parse_args(main, "-p[a-z]+", pattern="[a-z]+")
    # Note: For short options with GNU-style attachment, = is part of the value
    # Use -p "file=value" or --pattern=file for splitting on =
    assert_parse_args(main, "-pfile=value", pattern="file=value")


def test_multiple_options_only_first_gets_attached_value(app, assert_parse_args):
    """Test behavior when multiple value-taking options are combined.

    Only the first option can have an attached value. Once we hit a value-taking
    option, everything after is the value.
    """

    @app.default
    def main(
        user: Annotated[str, Parameter(name=("-u", "--user"))],
        password: Annotated[str | None, Parameter(name=("-p", "--password"))] = None,
    ):
        pass

    # -uprootpass should be: -u with value "prootpass"
    # The 'p' is NOT treated as another option, it's part of the value
    assert_parse_args(main, "-uprootpass", user="prootpass")

    # To set both, use separate options or space
    assert_parse_args(main, "-uroot -ppass", user="root", password="pass")


@pytest.mark.parametrize(
    "cmd,expected_output",
    [
        ("-o9", "9"),
        ("-o99", "99"),
        ("-o123abc", "123abc"),
        ("-oabc123", "abc123"),
    ],
)
def test_various_attached_values(app, assert_parse_args, cmd, expected_output):
    """Parametrized test for various value formats."""

    @app.default
    def main(output: Annotated[str, Parameter(name=("-o", "--output"))]):
        pass

    assert_parse_args(main, cmd, output=expected_output)


def test_single_char_option_with_negative_value(app, assert_parse_args):
    """Test that -o-5 treats -5 as the value for -o."""

    @app.default
    def main(
        offset: Annotated[int, Parameter(name=("-o", "--offset"))],
    ):
        pass

    # -o-5 should be: -o with value "-5"
    # This tests that the "-5" part is treated as a value, not as a separate option
    assert_parse_args(main, "-o-5", offset=-5)
