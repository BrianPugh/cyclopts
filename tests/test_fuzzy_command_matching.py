"""Tests for fuzzy command matching (backward compatibility feature).

Should probably be removed in v5.
"""

import pytest

from cyclopts import App
from cyclopts.exceptions import UnknownCommandError


@pytest.mark.parametrize(
    "func_name,expected_result,test_inputs",
    [
        (
            "myCommand",
            "myCommand executed",
            ["my-command", "mycommand", "my_command", "MyCommand", "MYCOMMAND"],
        ),
        (
            "my_command",
            "my_command executed",
            ["my-command", "mycommand", "my_command", "MY-COMMAND"],
        ),
        (
            "HTTPServer",
            "HTTPServer executed",
            ["http-server", "httpserver", "http_server", "HTTPSERVER"],
        ),
    ],
)
def test_fuzzy_command_matching_basic(app, func_name, expected_result, test_inputs):
    """Fuzzy matching allows commands to be invoked with various styles."""

    def command_func():
        return expected_result

    command_func.__name__ = func_name
    app.command(command_func)

    for input_cmd in test_inputs:
        assert app([input_cmd]) == expected_result


def test_fuzzy_command_matching_no_false_positives(app):
    """Fuzzy matching doesn't match unrelated commands."""

    @app.command
    def my_command():
        return "my_command"

    @app.command
    def other_command():
        return "other_command"

    # These should NOT match
    with pytest.raises(UnknownCommandError, match="myother"):
        app.parse_args(["myother"], exit_on_error=False)

    with pytest.raises(UnknownCommandError, match="commandmy"):
        app.parse_args(["commandmy"], exit_on_error=False)


def test_fuzzy_command_matching_exact_takes_precedence(app):
    """Exact matches are preferred over fuzzy matches."""

    @app.command(name="my-command")
    def cmd1():
        return "cmd1"

    @app.command(name="mycommand")
    def cmd2():
        return "cmd2"

    # Exact match wins
    assert app(["my-command"]) == "cmd1"
    assert app(["mycommand"]) == "cmd2"


def test_fuzzy_command_matching_ambiguous_error(app):
    """Ambiguous fuzzy matches raise clear errors."""

    @app.command(name="my-command")
    def cmd1():
        return "cmd1"

    @app.command(name="mycommand")
    def cmd2():
        return "cmd2"

    # Both normalize to 'mycommand', so this is ambiguous
    with pytest.raises(ValueError, match="Ambiguous command 'my_command'.*my-command.*mycommand"):
        app.parse_args(["my_command"], exit_on_error=False)


@pytest.mark.parametrize(
    "input_cmd,user_id,expected",
    [
        ("get-user-data", "123", "User 123"),
        ("getuserdata", "456", "User 456"),
        ("get_user_data", "789", "User 789"),
        ("GetUserData", "999", "User 999"),
    ],
)
def test_fuzzy_command_matching_with_arguments(app, input_cmd, user_id, expected):
    """Fuzzy matching works with commands that have arguments."""

    @app.command
    def getUserData(user_id: int):  # noqa: N802
        return f"User {user_id}"

    assert app([input_cmd, user_id]) == expected


@pytest.mark.parametrize(
    "command_name,input_variants,expected",
    [
        (
            "buildProject",
            ["buildproject", "build_project", "build-project"],
            "building",
        ),
        (
            "testProject",
            ["testproject", "testProject", "test-project"],
            "testing",
        ),
        (
            "deployProduction",
            ["deployproduction", "deploy_production", "deploy-production"],
            "deploying",
        ),
    ],
)
def test_fuzzy_command_matching_multiple_commands(app, command_name, input_variants, expected):
    """Fuzzy matching works with multiple commands."""

    def command_func():
        return expected

    command_func.__name__ = command_name
    app.command(command_func)

    for input_cmd in input_variants:
        assert app([input_cmd]) == expected


@pytest.mark.parametrize(
    "command_name,input_variants",
    [
        ("cmd1", ["cmd1", "CMD1", "Cmd1"]),
        ("cmd2", ["cmd2", "CMD2", "Cmd2"]),
    ],
)
def test_fuzzy_command_matching_preserves_cmd_digit_behavior(app, command_name, input_variants):
    """Fuzzy matching doesn't break cmd1, cmd2, etc (no lowercase-digit split)."""

    def command_func():
        return command_name

    command_func.__name__ = command_name
    app.command(command_func)

    for input_cmd in input_variants:
        assert app([input_cmd]) == command_name


@pytest.mark.parametrize(
    "subcommand,input_variants,expected",
    [
        ("createTable", ["createtable", "create_table", "create-table"], "table created"),
        ("dropTable", ["droptable", "drop_table", "drop-table"], "table dropped"),
    ],
)
def test_fuzzy_command_matching_nested_commands(app, subcommand, input_variants, expected):
    """Fuzzy matching works with nested commands."""
    sub_app = App()

    def command_func():
        return expected

    command_func.__name__ = subcommand
    sub_app.command(command_func)

    app.command(sub_app, name="database")

    for input_cmd in input_variants:
        assert app(["database", input_cmd]) == expected
