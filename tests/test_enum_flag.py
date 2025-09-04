"""Tests for enum.Flag and enum.IntFlag support in cyclopts."""

from dataclasses import dataclass
from enum import Flag, auto
from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, MissingArgumentError, Parameter
from cyclopts.exceptions import CoercionError, UnknownOptionError


class Permission(Flag):
    """File permissions as bit flags."""

    READ = auto()
    """Enable read permissions."""

    WRITE = auto()
    """Enable write permissions."""

    EXECUTE = auto()
    """Enable execute permissions."""


@dataclass
class User:
    name: str
    perms: Permission = Permission.READ


def test_flag_as_boolean_flags():
    """Test that Flag enum members are exposed as boolean CLI flags."""
    app = App()

    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    # Test individual flags
    result = app(["--perms.read"], exit_on_error=False)
    assert result == Permission.READ

    result = app(["--perms.write"], exit_on_error=False)
    assert result == Permission.WRITE

    result = app(["--perms.execute"], exit_on_error=False)
    assert result == Permission.EXECUTE

    # Test multiple flags combined
    result = app(["--perms.read", "--perms.write"], exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE

    result = app(["--perms.read", "--perms.write", "--perms.execute"], exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE | Permission.EXECUTE


@pytest.mark.parametrize(
    "command",
    [["--perms", "read", "--perms", "write"], ["read", "write"]],
)
def test_flag_with_list_str_input(app, command):
    """Test that Flag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    result = app(command, exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE


def test_flag_unknown_member_str(app):
    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    with pytest.raises(CoercionError):
        app("foo", exit_on_error=False)


def test_flag_unknown_member_option(app):
    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    with pytest.raises(UnknownOptionError):
        app("--perms.foo", exit_on_error=False)


def test_flag_as_boolean_flags_star_name(app, console):
    """Test that Flag enum members are exposed as boolean CLI flags."""

    @app.default
    def main(perms: Annotated[Permission, Parameter(name="*", negative_bool="")] = Permission.READ):
        """Manage file permissions."""
        return perms

    # Test individual flags
    result = app(["--read"], exit_on_error=False)
    assert result == Permission.READ

    result = app(["--write"], exit_on_error=False)
    assert result == Permission.WRITE

    result = app(["--execute"], exit_on_error=False)
    assert result == Permission.EXECUTE

    # Test multiple flags combined
    result = app(["--read", "--write"], exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE

    result = app(["--read", "--write", "--execute"], exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE | Permission.EXECUTE

    # Test help output
    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --read     Enable read permissions. [default: False]               │
        │ --write    Enable write permissions. [default: False]              │
        │ --execute  Enable execute permissions. [default: False]            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert expected == actual


@pytest.mark.skip
def test_flag_with_negative_bool_star_name():
    """Test that negative boolean flags work with Flag enums."""
    app = App()

    @app.default
    def main(
        perms: Annotated[Permission, Parameter(name="*")] = Permission.READ | Permission.WRITE,
    ):
        return perms

    # Test removing flags with negative
    result = app(["--no-read"], exit_on_error=False)
    assert result == Permission.WRITE

    result = app(["--no-write"], exit_on_error=False)
    assert result == Permission.READ

    result = app(["--no-read", "--no-write"], exit_on_error=False)
    assert result == Permission.READ

    # Test combining positive and negative
    result = app(["--execute", "--no-read"], exit_on_error=False)
    assert result == Permission.WRITE | Permission.EXECUTE


def test_flag_with_default_value():
    """Test Flag enum with non-zero default value."""
    app = App()

    @app.default
    def main(perms: Permission = Permission.READ | Permission.WRITE):
        return perms

    # Test default value is used when no arguments
    result = app([], exit_on_error=False)
    assert result == Permission.READ | Permission.WRITE

    # Test that providing flags overrides the default completely
    result = app(["--perms.execute"], exit_on_error=False)
    assert result == Permission.EXECUTE

    # Test combining multiple flags overrides default
    result = app(["--perms.read", "--perms.execute"], exit_on_error=False)
    assert result == Permission.READ | Permission.EXECUTE


def test_flag_empty_value():
    """Test Flag enum with empty (zero) value."""
    app = App()

    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    # Test empty value when no arguments
    result = app([], exit_on_error=False)
    assert result == Permission.READ

    # Test that empty value can be modified
    result = app(["--perms.read"], exit_on_error=False)
    assert result == Permission.READ


def test_flag_all_flags():
    """Test combining all flags results in the complete set."""
    app = App()

    @app.default
    def main(perms: Permission = Permission.READ):
        return perms

    # Test all flags combined
    all_flags = Permission.READ | Permission.WRITE | Permission.EXECUTE
    result = app(["--perms.read", "--perms.write", "--perms.execute"], exit_on_error=False)
    assert result == all_flags


def test_flag_with_other_parameters():
    """Test Flag enum alongside other parameters."""
    app = App()

    @app.default
    def main(name: str, perms: Permission = Permission.READ, verbose: bool = False):
        return name, perms, verbose

    # Test with positional and flag parameters
    result = app(["test.txt", "--perms.read", "--perms.write"], exit_on_error=False)
    assert result == ("test.txt", Permission.READ | Permission.WRITE, False)

    # Test with all parameter types
    result = app(["test.txt", "--perms.execute", "--verbose"], exit_on_error=False)
    assert result == ("test.txt", Permission.EXECUTE, True)


def test_flag_star_name_with_other_parameters():
    """Test Flag enum with star name alongside other parameters."""
    app = App()

    @app.default
    def main(
        name: str,
        perms: Annotated[Permission, Parameter(name="*")] = Permission.READ,
        verbose: bool = False,
    ):
        return name, perms, verbose

    # Test star name expansion with other parameters
    result = app(["test.txt", "--read", "--write", "--verbose"], exit_on_error=False)
    assert result == ("test.txt", Permission.READ | Permission.WRITE, True)


def test_flag_no_flags_provided():
    """Test behavior when no flags are provided but parameter is required."""
    app = App()

    @app.default
    def main(perms: Permission):  # No default value
        return perms

    with pytest.raises(MissingArgumentError):
        app([], exit_on_error=False)


def test_flag_help_shows_member_docstrings(console):
    """Test that Flag enum member docstrings appear in help output."""
    app = App()

    @app.default
    def main(perms: Permission = Permission.READ):
        """Manage file permissions."""
        return perms

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
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


def test_flag_help_star_name_shows_member_docstrings(console):
    """Test that Flag enum member docstrings appear with star name expansion."""
    app = App()

    @app.default
    def main(perms: Annotated[Permission, Parameter(name="*")] = Permission.READ):
        """Manage file permissions."""
        return perms

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Manage file permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
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


def test_flag_in_dataclass():
    """Test Flag enum field in a dataclass."""
    app = App()

    @app.default
    def main(user: User):
        return user

    # Test with name only (should use default perms)
    result = app(["Alice"], exit_on_error=False)
    assert result.name == "Alice"
    assert result.perms == Permission.READ

    # Test with name and flag permissions
    result = app(["Bob", "--user.perms.write", "--user.perms.execute"], exit_on_error=False)
    assert result.name == "Bob"
    assert result.perms == Permission.WRITE | Permission.EXECUTE

    # Test with all permissions
    result = app(["Charlie", "--user.perms.read", "--user.perms.write", "--user.perms.execute"], exit_on_error=False)
    assert result.name == "Charlie"
    assert result.perms == Permission.READ | Permission.WRITE | Permission.EXECUTE


def test_flag_in_dataclass_positionally():
    """Test Flag enum field positionally in a dataclass."""
    app = App()

    @app.default
    def main(user: User):
        return user

    result = app(["Bob", "write", "execute"], exit_on_error=False)
    assert result.name == "Bob"
    assert result.perms == Permission.WRITE | Permission.EXECUTE


def test_flag_in_dataclass_help(console):
    """Test help output for dataclass with Flag enum field."""
    app = App()

    @app.default
    def main(user: User):
        """Create a user with permissions."""
        return user

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
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


def test_flag_in_dataclass_help_no_negative(console):
    """Test help output for dataclass with Flag enum field."""
    app = App()

    @app.default
    def main(user: Annotated[User, Parameter(negative="")]):
        """Create a user with permissions."""
        return user

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
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
        return user

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_enum_flag [ARGS] [OPTIONS]

        Create a user with permissions.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
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
