from typing import Annotated

import pytest

from cyclopts import App, Parameter


def test_no_parse_pos(app, assert_parse_args_partial):
    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)]):
        pass

    assert_parse_args_partial(foo, "buzz_value", "buzz_value")
    _, _, ignored = app.parse_args("buzz_value")
    assert ignored == {"fizz": str}


def test_no_parse_invalid_kind(app):
    """Parameter.parse=False must be used with KEYWORD_ONLY or have a default value."""
    # Invalid: non-KEYWORD_ONLY without default
    with pytest.raises(ValueError):

        @app.default
        def foo(buzz: str, fizz: Annotated[str, Parameter(parse=False)]):
            pass

        app([])


def test_no_parse_with_default_allowed(app):
    """Parameter.parse=False is allowed for non-KEYWORD_ONLY with default."""

    @app.default
    def foo(buzz: str, fizz: Annotated[str, Parameter(parse=False)] = "default_value"):
        return (buzz, fizz)

    result = app("buzz_value", exit_on_error=False)
    assert result == ("buzz_value", "default_value")


def test_no_parse_keyword_only_with_default(app):
    """Parameter.parse=False is allowed for KEYWORD_ONLY with default."""

    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)] = "default_value"):
        return (buzz, fizz)

    result = app("buzz_value", exit_on_error=False)
    assert result == ("buzz_value", "default_value")


# Tests for regex-based parse behavior via App.default_parameter


def test_parse_regex_via_default_parameter():
    """App.default_parameter with regex skips underscore-prefixed params."""
    app = App(default_parameter=Parameter(parse="^(?!_)"))

    @app.default
    def foo(buzz: str, *, visible: str = "visible_default", _hidden: str = "hidden_default"):
        return (buzz, visible, _hidden)

    # "visible" matches ^(?!_), so it's parsed
    # "_hidden" doesn't match ^(?!_), so it's NOT parsed (not in bound.kwargs)
    _, bound, ignored = app.parse_args(["buzz_value", "--visible", "cli_visible"])
    assert bound.args == ("buzz_value",)
    assert bound.kwargs == {"visible": "cli_visible"}
    assert ignored == {"_hidden": str}


def test_parse_regex_not_in_help(capsys):
    """Params not matching regex should not appear in help."""
    app = App(default_parameter=Parameter(parse="^(?!_)"), result_action="return_value")

    @app.default
    def foo(visible: str, *, _private: str = "default"):
        pass

    app(["--help"], exit_on_error=False)
    output = capsys.readouterr().out
    assert "visible" in output.lower()
    assert "_private" not in output.lower()
    assert "private" not in output.lower()


def test_parse_regex_explicit_parse_true_override():
    """Explicit Parameter(parse=True) overrides app-level regex."""
    app = App(default_parameter=Parameter(parse="^(?!_)"))

    @app.default
    def foo(buzz: str, *, _private: Annotated[str, Parameter(parse=True)] = "default"):
        return (buzz, _private)

    # _private would normally be skipped by regex, but parse=True overrides
    _, bound, ignored = app.parse_args(["buzz_value", "--private", "cli_value"])
    assert bound.args == ("buzz_value",)
    assert bound.kwargs == {"_private": "cli_value"}
    assert ignored == {}


def test_parse_regex_explicit_show_true_override(capsys):
    """Explicit Parameter(show=True) overrides regex-based auto-hide."""
    app = App(default_parameter=Parameter(parse="^(?!_)"), result_action="return_value")

    @app.default
    def foo(visible: str, *, _private: Annotated[str, Parameter(show=True)] = "default"):
        pass

    app(["--help"], exit_on_error=False)
    output = capsys.readouterr().out
    assert "private" in output.lower()


def test_parse_compiled_regex_via_default_parameter():
    """App.default_parameter with pre-compiled regex skips underscore-prefixed params."""
    import re

    app = App(default_parameter=Parameter(parse=re.compile("^(?!_)")))

    @app.default
    def foo(buzz: str, *, visible: str = "visible_default", _hidden: str = "hidden_default"):
        return (buzz, visible, _hidden)

    _, bound, ignored = app.parse_args(["buzz_value", "--visible", "cli_visible"])
    assert bound.args == ("buzz_value",)
    assert bound.kwargs == {"visible": "cli_visible"}
    assert ignored == {"_hidden": str}


def test_parse_regex_invalid_positional_no_default():
    """App.default_parameter regex that skips a required positional param should raise."""
    app = App(default_parameter=Parameter(parse="^(?!_)"))

    @app.default
    def foo(_value: str):  # Positional, no default, would be skipped by regex
        pass

    # The error should be raised when trying to parse (Argument creation),
    # not at registration time (since validate_command only sees direct annotations)
    with pytest.raises(ValueError, match="KEYWORD_ONLY"):
        app.parse_args([])
