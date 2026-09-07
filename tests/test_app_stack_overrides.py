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


def test_reentrant_sibling_does_not_inherit_config():
    """A subcommand's settings must not leak sideways into a re-entrantly invoked sibling.

    Regression test for the #933 follow-up: resolving a subcommand's configuration was
    done by exposing the invoked command chain in the entry app's top stack frame, but
    ``resolve`` scanned *every* frame. When ``outer`` (which sets ``backend``/
    ``end_of_options_delimiter``) re-entrantly invokes sibling ``inner`` while its own
    frame is still live, ``inner``'s frame sat above the leftover ``[root, outer]`` frame;
    ``inner``'s ``None`` values fell through and picked up ``outer``'s settings. Resolution
    must be scoped to the innermost invocation frame.
    """
    seen = {}

    app = App(result_action="return_value")

    @app.command(backend="trio", end_of_options_delimiter="OUTERDELIM")
    def outer():
        return app(["inner"])

    @app.command  # sets nothing; must resolve to the root defaults, not outer's
    def inner():
        seen["backend"] = app.app_stack.resolve("backend", fallback="asyncio")
        seen["eood"] = app.app_stack.resolve("end_of_options_delimiter")
        return "inner-ran"

    assert app(["outer"]) == "inner-ran"
    assert seen == {"backend": "asyncio", "eood": None}

    # Directly invoking the sibling resolves to the same defaults.
    seen.clear()
    assert app(["inner"]) == "inner-ran"
    assert seen == {"backend": "asyncio", "eood": None}


def test_subcommand_config_resolved_via_meta_forwarding():
    """Subcommand settings resolve when the meta app forwards to the invoked command.

    The ``app.meta`` entry point dispatches subcommands by re-entrantly calling ``app(tokens)``
    inside ``meta.default``; that inner call runs on the owner app's stack, so a subcommand-level
    setting the parent does not define (here ``error_formatter``) must still be honored end-to-end
    (#933). Guards the meta-app stack shape flagged during review.
    """
    from io import StringIO

    from rich.console import Console

    from cyclopts import CoercionError

    buf = StringIO()
    error_console = Console(file=buf, width=70, color_system=None)

    app = App(name="root", result_action="return_value")

    @app.meta.default
    def meta_main(*tokens: Annotated[str, Parameter(allow_leading_hyphen=True)]):
        return app(list(tokens), error_console=error_console)

    @app.command(error_formatter=lambda e: f"SUBFMT: {e}")
    def sub(value: int):
        return value

    with pytest.raises(CoercionError):
        app.meta(["sub", "abc"], exit_on_error=False)

    assert buf.getvalue().strip() == 'SUBFMT: Invalid value for VALUE: unable to convert "abc" into int.'
