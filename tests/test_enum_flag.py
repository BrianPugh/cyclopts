"""Tests for enum.Flag and enum.IntFlag support in cyclopts."""

from dataclasses import dataclass
from enum import Flag, IntFlag, auto
from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import MissingArgumentError, Parameter
from cyclopts.exceptions import CoercionError, UnknownOptionError


class Permission(Flag):
    """File permissions as bit flags."""

    READ = auto()
    """Enable read permissions."""
    WRITE = auto()
    """Enable write permissions."""
    EXECUTE = auto()
    """Enable execute permissions."""


class HttpStatus(IntFlag):
    INFORMATIONAL = 100
    SUCCESS = 200
    REDIRECTION = 300
    CLIENT_ERROR = 400
    SERVER_ERROR = 500


@dataclass
class User:
    name: str
    perms: Permission = Permission.READ


def test_flag_as_boolean_flags(app, assert_parse_args):
    """Test that Flag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(perms: Permission = Permission.READ):
        pass

    assert_parse_args(main, "--perms.read", perms=Permission.READ)
    assert_parse_args(main, "--perms.write", perms=Permission.WRITE)
    assert_parse_args(main, "--perms.read --perms.write", perms=Permission.READ | Permission.WRITE)


def test_int_flag_as_boolean_flags(app, assert_parse_args):
    """Test that IntFlag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(error_on: HttpStatus | None = None):
        pass

    assert_parse_args(main, "")
    assert_parse_args(main, "--error-on.success", error_on=HttpStatus.SUCCESS)


@pytest.mark.parametrize(
    "command",
    ["--perms read --perms write", "read write"],
)
def test_flag_with_list_str_input(app, assert_parse_args, command):
    """Test that Flag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(perms: Permission = Permission.READ):
        pass

    assert_parse_args(main, command, Permission.READ | Permission.WRITE)


def test_flag_unknown_member_str(app):
    @app.default
    def main(perms: Permission = Permission.READ):
        pass

    with pytest.raises(CoercionError):
        app("foo", exit_on_error=False)


def test_flag_unknown_member_option(app):
    @app.default
    def main(perms: Permission = Permission.READ):
        pass

    with pytest.raises(UnknownOptionError):
        app("--perms.foo", exit_on_error=False)


def test_flag_as_boolean_flags_star_name(app, assert_parse_args, console):
    """Test that Flag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(perms: Annotated[Permission, Parameter(name="*", negative_bool="")] = Permission.READ):
        """Manage file permissions."""
        pass

    # Test individual flags
    assert_parse_args(main, "--read", Permission.READ)
    assert_parse_args(main, "--write", Permission.WRITE)
    assert_parse_args(main, "--execute", Permission.EXECUTE)

    # Test multiple flags combined
    assert_parse_args(main, "--read --write", Permission.READ | Permission.WRITE)
    assert_parse_args(main, "--read --write --execute", Permission.READ | Permission.WRITE | Permission.EXECUTE)

    # Test help output
    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --read     Enable read permissions. [default: False]               │
        │ --write    Enable write permissions. [default: False]              │
        │ --execute  Enable execute permissions. [default: False]            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert expected == actual


def test_flag_with_default_value(app, assert_parse_args):
    """Test Flag enum with non-zero default value."""

    @app.default
    def main(perms: Permission = Permission.READ | Permission.WRITE):
        pass

    assert_parse_args(main, "")


def test_flag_with_other_parameters(app, assert_parse_args):
    """Test Flag enum alongside other parameters."""

    @app.default
    def main(name: str, perms: Permission = Permission.READ, verbose: bool = False):
        pass

    # Test with positional and flag parameters
    assert_parse_args(main, "test.txt --perms.read --perms.write", "test.txt", Permission.READ | Permission.WRITE)

    # Test with all parameter types
    assert_parse_args(main, "test.txt --perms.execute --verbose", "test.txt", Permission.EXECUTE, True)


def test_flag_star_name_with_other_parameters(app, assert_parse_args):
    """Test Flag enum with star name alongside other parameters."""

    @app.default
    def main(
        name: str,
        perms: Annotated[Permission, Parameter(name="*")] = Permission.READ,
        verbose: bool = False,
    ):
        pass

    # Test star name expansion with other parameters
    assert_parse_args(main, "test.txt --read --write --verbose", "test.txt", Permission.READ | Permission.WRITE, True)


def test_flag_no_flags_provided(app):
    """Test behavior when no flags are provided but parameter is required."""

    @app.default
    def main(perms: Permission):  # No default value
        pass

    with pytest.raises(MissingArgumentError):
        app([], exit_on_error=False)


def test_flag_help_shows_member_docstrings(app, console):
    """Test that Flag enum member docstrings appear in help output."""

    @app.default
    def main(perms: Permission = Permission.READ):
        """Manage file permissions."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_enum_flag [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --perms.read          Enable read permissions. [default: False]    │
        │   --perms.no-read                                                  │
        │ --perms.write         Enable write permissions. [default: False]   │
        │   --perms.no-write                                                 │
        │ --perms.execute       Enable execute permissions. [default: False] │
        │   --perms.no-execute                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert expected == actual


def test_flag_help_star_name_shows_member_docstrings(app, console):
    """Test that Flag enum member docstrings appear with star name expansion."""

    @app.default
    def main(perms: Annotated[Permission, Parameter(name="*")] = Permission.READ):
        """Manage file permissions."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --read --no-read        Enable read permissions. [default: False]  │
        │ --write --no-write      Enable write permissions. [default: False] │
        │ --execute --no-execute  Enable execute permissions. [default:      │
        │                         False]                                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert expected == actual


def test_flag_in_dataclass(app, assert_parse_args):
    """Test Flag enum field in a dataclass."""

    @app.default
    def main(user: User):
        pass

    # Test with name only (should use default perms)
    assert_parse_args(main, "Alice", User("Alice", Permission.READ))

    # Test with name and flag permissions
    assert_parse_args(
        main, "Bob --user.perms.write --user.perms.execute", User("Bob", Permission.WRITE | Permission.EXECUTE)
    )


def test_flag_in_dataclass_positionally(app, assert_parse_args):
    """Test Flag enum field positionally in a dataclass."""

    @app.default
    def main(user: User):
        pass

    assert_parse_args(main, "Bob write execute", User("Bob", Permission.WRITE | Permission.EXECUTE))


def test_flag_in_dataclass_help(app, console):
    """Test help output for dataclass with Flag enum field."""

    @app.default
    def main(user: User):
        """Create a user with permissions."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [OPTIONS] USER.NAME

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.NAME --user.name      [required]                           │
        │    --user.perms.read          Enable read permissions. [default:   │
        │      --user.perms.no-read     False]                               │
        │    --user.perms.write         Enable write permissions. [default:  │
        │      --user.perms.no-write    False]                               │
        │    --user.perms.execute       Enable execute permissions.          │
        │      --user.perms.no-execute  [default: False]                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert expected == actual


def test_flag_in_dataclass_help_no_negative(app, console):
    """Test help output for dataclass with Flag enum field."""

    @app.default
    def main(user: Annotated[User, Parameter(negative="")]):
        """Create a user with permissions."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [OPTIONS] USER.NAME

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.NAME --user.name  [required]                               │
        │    --user.perms.read      Enable read permissions. [default:       │
        │                           False]                                   │
        │    --user.perms.write     Enable write permissions. [default:      │
        │                           False]                                   │
        │    --user.perms.execute   Enable execute permissions. [default:    │
        │                           False]                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert expected == actual


def test_flag_in_dataclass_help_no_keywords(app, assert_parse_args, console):
    """Test help output for dataclass with Flag enum field."""

    @dataclass
    class User:
        name: str
        perms: Annotated[Permission, Parameter(accepts_keys=False)] = Permission.READ

    @app.default
    def main(user: Annotated[User, Parameter(negative="")]):
        """Create a user with permissions."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag USER.NAME [ARGS]

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.NAME --user.name    [required]                             │
        │    USER.PERMS --user.perms  [choices: read, write, execute]        │
        │                             [default: read]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert expected == actual

    assert_parse_args(main, "Bob read write", User("Bob", perms=Permission.READ | Permission.WRITE))
