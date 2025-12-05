from typing import Annotated

import pytest

from cyclopts import Parameter


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


def test_no_parse_keyword_only_without_default(app):
    """Parameter.parse=False is allowed for KEYWORD_ONLY without default."""

    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)]):
        return (buzz, fizz)

    _, _, ignored = app.parse_args("buzz_value")
    assert ignored == {"fizz": str}


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


# Tests for automatic underscore-prefix parse=False behavior


def test_underscore_param_auto_no_parse(app):
    """Underscore-prefixed KEYWORD_ONLY params auto-disable parsing."""

    @app.default
    def foo(buzz: str, *, _injected: str = "injected_default"):
        return (buzz, _injected)

    result = app("buzz_value", exit_on_error=False)
    assert result == ("buzz_value", "injected_default")


def test_underscore_param_parse_args_ignored(app):
    """Underscore-prefixed KEYWORD_ONLY params appear in ignored dict."""

    @app.default
    def foo(buzz: str, *, _injected: str = "injected_default"):
        pass

    _, _, ignored = app.parse_args("buzz_value")
    assert ignored == {"_injected": str}


def test_underscore_param_explicit_parse_true(app):
    """Explicit Parameter(parse=True) overrides underscore auto-disable."""

    @app.default
    def foo(buzz: str, *, _injected: Annotated[str, Parameter(parse=True)] = "default"):
        return (buzz, _injected)

    # Underscore is stripped for CLI flag name, so --injected not --_injected
    result = app(["buzz_value", "--injected", "cli_value"], exit_on_error=False)
    assert result == ("buzz_value", "cli_value")


def test_underscore_param_not_keyword_only_still_parses(app, assert_parse_args):
    """Underscore params that are NOT KEYWORD_ONLY should still be parsed."""

    @app.default
    def foo(_required: str):
        return _required

    assert_parse_args(foo, "_value", "_value")


def test_underscore_param_not_in_help(app, capsys):
    """Underscore KEYWORD_ONLY params should not appear in help."""

    @app.default
    def foo(visible: str, *, _injected: str = "default"):
        pass

    app(["--help"], exit_on_error=False)
    output = capsys.readouterr().out
    assert "visible" in output.lower()
    assert "_injected" not in output.lower()
    assert "injected" not in output.lower()


def test_underscore_param_explicit_show_true(app, capsys):
    """Explicit Parameter(show=True) overrides underscore auto-hide."""

    @app.default
    def foo(visible: str, *, _injected: Annotated[str, Parameter(show=True)] = "default"):
        pass

    app(["--help"], exit_on_error=False)
    output = capsys.readouterr().out
    assert "injected" in output.lower()


def test_underscore_param_multiple(app):
    """Multiple underscore-prefixed KEYWORD_ONLY params all auto-disable."""

    @app.default
    def foo(buzz: str, *, _first: str = "first", _second: int = 42):
        return (buzz, _first, _second)

    result = app("buzz_value", exit_on_error=False)
    assert result == ("buzz_value", "first", 42)


def test_underscore_keyword_only_without_default(app):
    """Underscore KEYWORD_ONLY params without defaults also auto-disable."""

    @app.default
    def foo(buzz: str, *, _injected: str):
        return (buzz, _injected)

    # _injected is not parsed, so calling with just buzz_value should work
    # but _injected will have no value (will use UNSET/cause issue)
    # Actually, this should use the default binding behavior
    _, _, ignored = app.parse_args("buzz_value")
    assert ignored == {"_injected": str}
