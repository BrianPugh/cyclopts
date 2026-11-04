"""Tests for ``App.argfile_prefix`` (issue #1032)."""

import asyncio
from pathlib import Path
from typing import Annotated

import pytest

from cyclopts import App, Parameter, TokenizationError


@pytest.fixture
def app(console):
    app = App(argfile_prefix="@", error_console=console, result_action="return_value")

    @app.command
    def run(*, host: str, port: int = 8080, description: str = ""):
        return host, port, description

    @app.command
    def echo(*values: str):
        return values

    return app


def test_argfile_expands_command_and_options(app):
    Path("run.args").write_text("run\n--host\ndb.example.internal\n--port\n5432\n--description\nnightly run\n")
    assert app(["@run.args"]) == ("db.example.internal", 5432, "nightly run")


def test_argfile_expands_in_place(app):
    Path("host.args").write_text("--host\nexample.com\n")
    assert app(["run", "@host.args", "--port", "1"]) == ("example.com", 1, "")


def test_argfile_line_is_one_argument(app):
    """A line is used as-is: no shell-style splitting."""
    Path("values.args").write_text("a b\n 'c'\n\n")
    assert app(["echo", "@values.args"]) == ("a b", " 'c'", "")


def test_argfile_nested(app):
    Path("outer.args").write_text("run\n@inner.args\n")
    Path("inner.args").write_text("--host\nnested\n")
    assert app(["@outer.args"]) == ("nested", 8080, "")


def test_argfile_recursive_reference_raises(app):
    Path("a.args").write_text("@b.args\n")
    Path("b.args").write_text("@a.args\n")
    with pytest.raises(TokenizationError, match="'a.args' is referenced recursively"):
        app(["@a.args"], exit_on_error=False, print_error=False)


def test_argfile_missing_file_prints_error(app, console):
    with console.capture() as capture, pytest.raises(TokenizationError):
        app(["@missing.args"], exit_on_error=False)
    assert "Cannot read argument file 'missing.args'" in capture.get()


def test_argfile_missing_file_exits(app, console):
    with console.capture(), pytest.raises(SystemExit) as e:
        app(["@missing.args"])
    assert e.value.code == 2


def test_argfile_disabled_by_default(console):
    app = App(error_console=console, result_action="return_value")

    @app.default
    def main(*values: str):
        return values

    Path("run.args").write_text("x\n")
    assert app(["@run.args"]) == ("@run.args",)


def test_argfile_after_end_of_options_delimiter_not_expanded(app):
    Path("values.args").write_text("x\n")
    assert app(["echo", "@values.args", "--", "@values.args"]) == ("x", "@values.args")


def test_argfile_delimiter_inside_file_stops_expansion(app):
    Path("values.args").write_text("--\n@values.args\n")
    assert app(["echo", "@values.args", "@values.args"]) == ("@values.args", "@values.args")


def test_argfile_bare_prefix_is_literal(app):
    assert app(["echo", "@"]) == ("@",)


def test_argfile_multi_character_prefix(console):
    app = App(argfile_prefix="+@", error_console=console, result_action="return_value")

    @app.default
    def main(*values: str):
        return values

    Path("values.args").write_text("x\n")
    assert app(["+@values.args", "@values.args"]) == ("x", "@values.args")


def test_argfile_parse_args(app):
    Path("run.args").write_text("run\n--host\nh\n")
    _, bound, _ = app.parse_args("@run.args --port 1")
    assert bound.arguments == {"host": "h", "port": 1}


def test_argfile_parse_known_args(app):
    Path("run.args").write_text("run\n--host\nh\n")
    _, bound, unused, _ = app.parse_known_args(["@run.args"])
    assert bound.arguments == {"host": "h"}
    assert unused == []


def test_argfile_parse_known_args_missing_file_raises(app):
    with pytest.raises(TokenizationError):
        app.parse_known_args(["@missing.args"])


def test_argfile_run_async(app):
    Path("run.args").write_text("run\n--host\nh\n")
    assert asyncio.run(app.run_async(["@run.args"])) == ("h", 8080, "")


def test_argfile_meta_app(console):
    app = App(argfile_prefix="@", error_console=console, result_action="return_value")

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: bool = False,
    ):
        return verbose, app(tokens)

    @app.command
    def run(*, host: str):
        return host

    Path("meta.args").write_text("--verbose\nrun\n--host\nh\n")
    assert app.meta(["@meta.args"]) == (True, "h")


def test_argfile_help_flag_in_file(app, console):
    Path("help.args").write_text("run\n--help\n")
    with console.capture() as capture:
        app(["@help.args"], console=console)
    assert "--host" in capture.get()


def test_argfile_interactive_shell(app, mocker):
    Path("run.args").write_text("run\n--host\nh\n")
    mocker.patch("builtins.input", side_effect=["@run.args", "quit"])
    seen = []
    app.interactive_shell(dispatcher=lambda command, bound, ignored: seen.append(bound.arguments))
    assert seen == [{"host": "h"}]
