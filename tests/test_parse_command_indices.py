from typing import Annotated

from cyclopts import App, Parameter
from cyclopts.bind import normalize_tokens


def test_command_indices_simple():
    """Single command at start."""
    app = App()

    @app.command
    def foo():
        pass

    _, _, _, indices = app._parse_commands(normalize_tokens(["foo"]))
    assert indices == [0]


def test_command_indices_with_leading_flags():
    """Command after flags."""
    app = App()

    @app.command
    def foo():
        pass

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: bool = False,
    ):
        app(tokens)

    _, _, _, indices = app.meta._parse_commands(normalize_tokens(["--verbose", "foo"]))
    assert indices == [1]


def test_command_indices_nested_commands():
    """Nested subcommands."""
    app = App()
    sub = App(name="sub")
    app.command(sub)

    @sub.command
    def bar():
        pass

    _, _, _, indices = app._parse_commands(normalize_tokens(["sub", "bar"]))
    assert indices == [0, 1]


def test_command_indices_with_trailing_args():
    """Command followed by args (not commands)."""
    app = App()

    @app.command
    def foo(name: str):
        pass

    _, _, _, indices = app._parse_commands(normalize_tokens(["foo", "myname"]))
    assert indices == [0]


def test_command_indices_no_commands():
    """No commands found."""
    app = App()

    @app.default
    def main(name: str):
        pass

    _, _, _, indices = app._parse_commands(normalize_tokens(["myname"]))
    assert indices == []


def test_command_indices_flags_between_commands():
    """Flags interspersed between nested commands."""
    app = App()
    sub = App(name="sub")
    app.command(sub)

    @sub.command
    def bar():
        pass

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: bool = False,
    ):
        app(tokens)

    _, _, _, indices = app.meta._parse_commands(normalize_tokens(["--verbose", "sub", "bar", "--extra"]))
    # --verbose consumed by meta, sub at original index 1, bar at original index 2
    assert indices == [1, 2]


def test_command_indices_empty_tokens():
    """Empty token list."""
    app = App()

    @app.default
    def main():
        pass

    _, _, _, indices = app._parse_commands(normalize_tokens([]))
    assert indices == []


def test_parse_commands_public_api_unchanged():
    """Public parse_commands still returns 3-tuple."""
    app = App()

    @app.command
    def foo():
        pass

    result = app.parse_commands(["foo"])
    assert len(result) == 3
    command_chain, apps, unused = result
    assert command_chain == ("foo",)
