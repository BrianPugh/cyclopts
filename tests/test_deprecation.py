"""Tests for runtime deprecation warnings (App.deprecated_handler / Parameter.deprecated_handler).

These are distinct from the help-rendering deprecation tests in test_help.py: this file
covers the runtime callback fired when a deprecated command/parameter is actually used.
"""

from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.exceptions import ValidationError


@pytest.fixture
def calls():
    """A list that a fake ``deprecated_handler`` appends ``(kind, name, version, message)`` to."""
    return []


@pytest.fixture
def handler(calls):
    def _handler(kind, name, version, message):
        calls.append((kind, name, version, message))

    return _handler


def test_deprecated_command_fires_handler_on_invocation(app, handler, calls):
    app.deprecated_handler = handler

    @app.command(deprecated=("2.0", "Use new-cmd instead."))
    def old_cmd():
        return "ran"

    result = app(["old-cmd"])

    assert result == "ran"
    assert calls == [("command", "old-cmd", "2.0", "Use new-cmd instead.")]


def test_non_deprecated_command_does_not_fire_handler(app, handler, calls):
    app.deprecated_handler = handler

    @app.command
    def fine_cmd():
        return "ran"

    app(["fine-cmd"])

    assert calls == []


def test_deprecated_parameter_fires_only_when_explicitly_supplied(app, handler, calls):
    app.deprecated_handler = handler

    @app.default
    def main(x: Annotated[int, Parameter(deprecated="use --y instead")] = 0, y: int = 0):
        return x, y

    app(["--y", "5"])
    assert calls == []  # x used its default; never supplied.

    app(["--x", "5"])
    assert calls == [("parameter", "--x", None, "use --y instead")]


def test_deprecated_parameter_with_version(app, handler, calls):
    app.deprecated_handler = handler

    @app.default
    def main(x: Annotated[int, Parameter(deprecated=("1.5", "Use --y."))] = 0):
        return x

    app(["--x", "1"])

    assert calls == [("parameter", "--x", "1.5", "Use --y.")]


def test_parameter_deprecated_handler_overrides_app_handler(app, calls):
    app_calls = []
    param_calls = []
    app.deprecated_handler = lambda kind, name, version, message: app_calls.append((kind, name, version, message))

    @app.default
    def main(
        x: Annotated[
            int,
            Parameter(
                deprecated="p",
                deprecated_handler=lambda kind, name, version, message: param_calls.append(
                    (kind, name, version, message)
                ),
            ),
        ] = 0,
    ):
        return x

    app(["--x", "1"])

    assert app_calls == []
    assert param_calls == [("parameter", "--x", None, "p")]


def test_subapp_inherits_root_deprecated_handler(app, handler, calls):
    app.deprecated_handler = handler

    sub = App(name="sub", deprecated="deprecated subapp")
    app.command(sub)

    @sub.default
    def sub_main():
        return "ran"

    app(["sub"])

    assert calls == [("command", "sub", None, "deprecated subapp")]


def test_deprecated_intermediate_group_and_leaf_both_fire(app, handler, calls):
    app.deprecated_handler = handler

    group = App(name="group", deprecated="whole group is old")
    app.command(group)

    @group.command(deprecated="leaf itself is also old")
    def leaf():
        return "ran"

    app(["group", "leaf"])

    assert ("command", "group", None, "whole group is old") in calls
    assert ("command", "leaf", None, "leaf itself is also old") in calls
    assert len(calls) == 2


def test_no_deprecation_no_warning(app, handler, calls):
    app.deprecated_handler = handler

    @app.default
    def main(x: int = 0):
        return x

    app(["--x", "1"])

    assert calls == []


def test_deprecated_handler_not_fired_on_failed_validation(app, handler, calls):
    """A validator rejecting the arguments must prevent the deprecated_handler from firing."""
    app.deprecated_handler = handler

    def reject(x):
        raise ValueError("nope")

    @app.default(validator=reject)
    def main(x: Annotated[int, Parameter(deprecated="old param")] = 0):
        return x

    with pytest.raises(ValidationError):
        app(["--x", "1"], print_error=False, exit_on_error=False)

    assert calls == []


def test_default_deprecated_handler_emits_deprecation_warning(app):
    """Without a custom handler, the built-in default emits a stdlib DeprecationWarning."""

    @app.command(deprecated=("3.0", "Use other instead."))
    def old_cmd():
        return "ran"

    with pytest.warns(DeprecationWarning, match="old-cmd.*deprecated.*v3.0.*Use other instead."):
        app(["old-cmd"])
