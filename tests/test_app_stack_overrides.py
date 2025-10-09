"""Tests for AppStack override functionality."""

from typing import Annotated

import pytest

from cyclopts import App, Parameter, UnknownOptionError


def test_meta_app_override_propagation():
    """Test that overrides propagate from parent app to meta app calls."""
    results = []

    app = App(result_action="return_value")

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        results.append("meta")
        try:
            app(tokens, exit_on_error=False)
        except UnknownOptionError:
            results.append("caught")

    @app.command
    def foo(*, flag: bool = False):
        results.append(f"foo {flag}")

    # This should not exit even though there's an unknown option
    app.meta(["foo", "--unknown"], exit_on_error=False)
    assert results == ["meta", "caught"]


def test_nested_app_override_propagation():
    """Test that overrides propagate through nested app invocations."""
    results = []

    root_app = App(result_action="return_value")
    sub_app = App(name="sub", result_action="return_value")

    @root_app.meta.default
    def root_meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        results.append("root_meta")
        root_app(tokens, exit_on_error=False)

    @sub_app.meta.default
    def sub_meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        results.append("sub_meta")
        sub_app(tokens)  # Should inherit exit_on_error=False

    @sub_app.command
    def cmd(*, flag: bool = False):
        results.append(f"cmd {flag}")

    root_app.command(sub_app.meta, name="sub")

    # Test that exit_on_error=False propagates through the chain
    try:
        root_app.meta(["sub", "cmd", "--unknown"], exit_on_error=False)
    except UnknownOptionError:
        results.append("caught")

    assert "root_meta" in results
    assert "sub_meta" in results
    assert "caught" in results


def test_parse_args_override_propagation():
    """Test that parse_args properly stores and uses overrides."""
    app = App(result_action="return_value")

    @app.default
    def main(value: int):
        return value

    # Test with exit_on_error=False
    with pytest.raises(UnknownOptionError):
        app.parse_args(["--unknown"], exit_on_error=False)

    # Test that overrides are properly cleaned up after parse_args
    assert len(app.app_stack.overrides_stack) == 1
    assert app.app_stack.overrides_stack[0] == {}


def test_call_override_propagation():
    """Test that __call__ properly stores and uses overrides."""
    app = App(result_action="return_value")
    results = []

    @app.default
    def main(value: int = 0):
        results.append(value)
        return value

    # Test with exit_on_error=False
    with pytest.raises(UnknownOptionError):
        app(["--unknown"], exit_on_error=False)

    # Normal call should work
    app(["--value", "5"])
    assert results == [5]

    # Test that overrides are properly cleaned up
    assert len(app.app_stack.overrides_stack) == 1
    assert app.app_stack.overrides_stack[0] == {}


def test_multiple_override_parameters():
    """Test that all override parameters are properly handled."""
    app = App(result_action="return_value")

    @app.default
    def main(value: int):
        return value

    # Test multiple overrides at once
    with pytest.raises(UnknownOptionError) as exc_info:
        app.parse_args(["--unknown"], exit_on_error=False, print_error=False, verbose=True, help_on_error=False)

    # Check that verbose was applied
    assert exc_info.value.verbose is True

    # Check cleanup
    assert len(app.app_stack.overrides_stack) == 1
    assert app.app_stack.overrides_stack[0] == {}
