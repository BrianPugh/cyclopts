from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter
from cyclopts.config import Env, Toml


def test_config_end2end(app, tmp_path, assert_parse_args):
    config_fn = tmp_path / "config.toml"

    config_fn.write_text(
        dedent(
            """\
            [tool.cyclopts]
            key1 = "foo1"
            key2 = "foo2"
            list1 = []
            dict1 = {}

            [tool.cyclopts.function1]
            key3 = "bar1"
            key4 = "bar2"
            """
        )
    )

    app.config = Toml(config_fn, root_keys=["tool", "cyclopts"])

    @app.default
    def default(key1, key2, *, list1: list[int], dict1: dict[str, int]):
        pass

    @app.command
    def function1(key3, key4):
        pass

    assert_parse_args(default, "foo", key1="foo", key2="foo2", list1=[], dict1={})
    assert_parse_args(default, "foo --key2=fizz", key1="foo", key2="fizz", list1=[], dict1={})
    assert_parse_args(default, "foo --list1 1", key1="foo", key2="foo2", list1=[1], dict1={})
    assert_parse_args(function1, "function1 --key4=fizz", key3="bar1", key4="fizz")


def test_config_env_repeated(app, monkeypatch, assert_parse_args):
    monkeypatch.setenv("FOO", "bar")

    app.config = Env()

    @app.default
    def default(foo: Annotated[str, Parameter(env_var="FOO")]):
        pass

    assert_parse_args(default, "", "bar")


def test_config_env_help(app, assert_parse_args, console):
    """Special-case for :class:`.config.Env` to get added to help-page."""
    app.config = Env()

    @app.default
    def default(foo: Annotated[str, Parameter(env_var="BAR")]):
        pass

    with console.capture() as capture:
        app(["--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_end2end FOO

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  [env var: BAR, FOO] [required]                       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_config_env_help_meta_option(app, console, monkeypatch):
    """A meta app's option reads its ``Env`` variable without the subcommand's command segments."""
    app.config = Env("DEMO_")
    db = App(name="db")
    app.command(db)

    @db.command
    def migrate(steps: int = 1):
        return steps

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], verbose: bool = False):
        return verbose, app(tokens)

    with console.capture() as capture:
        app.meta(["db", "migrate", "--help"], console=console)
    actual = capture.get()
    assert "DEMO_VERBOSE" in actual
    assert "DEMO_DB_MIGRATE_VERBOSE" not in actual
    assert "DEMO_DB_MIGRATE_STEPS" in actual

    monkeypatch.setenv("DEMO_VERBOSE", "true")
    assert app.meta(["db", "migrate"]) == (True, 1)
