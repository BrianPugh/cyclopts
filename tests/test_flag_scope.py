"""Tests for flag_scope feature (issue #627)."""

from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.exceptions import UnknownOptionError


class TestStrictScope:
    """Tests for flag_scope='strict'."""

    def test_separate_flags_each_level(self):
        """Each level's flags bind to their own level."""
        app = App(flag_scope="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(*, debug: bool = False):
            return {"debug": debug}

        result = app.meta(["--verbose", "foo", "--debug"])
        assert result == {"verbose": True, "debug": True}

    def test_flags_only_bind_to_own_level(self):
        """In strict mode, a flag only binds to the command it appears after."""
        app = App(flag_scope="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: Annotated[bool, Parameter(alias="-v")] = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(*, version: Annotated[bool, Parameter(alias="-v")] = False):
            return {"version": version}

        # -v before foo → meta's verbose
        result = app.meta(["-v", "foo"])
        assert result == {"verbose": True, "version": False}

        # -v after foo → foo's version
        result = app.meta(["foo", "-v"])
        assert result == {"verbose": False, "version": True}

        # -v at both levels
        result = app.meta(["-v", "foo", "-v"])
        assert result == {"verbose": True, "version": True}

    def test_unknown_flag_at_command_level_errors(self):
        """In strict mode, unknown flags at command level raise an error."""
        app = App(flag_scope="strict")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo():
            pass

        with pytest.raises(UnknownOptionError):
            app.meta(["foo", "--unknown"], exit_on_error=False)

    def test_meta_flag_after_command_errors_strict(self):
        """In strict mode, a meta-only flag after a command is an error."""
        app = App(flag_scope="strict")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo():
            pass

        # --verbose is only defined on meta, but appears after foo → error in strict
        with pytest.raises(UnknownOptionError):
            app.meta(["foo", "--verbose"], exit_on_error=False)

    def test_no_commands_still_works(self):
        """flag_scope with no subcommands works normally."""
        app = App(flag_scope="strict", result_action="return_value")

        @app.default
        def main(*, verbose: bool = False):
            return {"verbose": verbose}

        result = app(["--verbose"])
        assert result == {"verbose": True}

    def test_positional_args_at_command_level(self):
        """Positional args after a command bind to the command."""
        app = App(flag_scope="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(name: str, *, debug: bool = False):
            return {"name": name, "debug": debug}

        result = app.meta(["--verbose", "foo", "--debug", "myname"])
        assert result == {"verbose": True, "name": "myname", "debug": True}

    def test_nested_subcommands_strict(self):
        """Strict scoping works with nested subcommands."""
        app = App(flag_scope="strict", result_action="return_value")
        sub = App(name="sub")
        app.command(sub)

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @sub.command
        def bar(*, debug: bool = False):
            return {"debug": debug}

        result = app.meta(["--verbose", "sub", "bar", "--debug"])
        assert result == {"verbose": True, "debug": True}

    def test_meta_flag_with_value_strict(self):
        """Meta flags that take values work with strict scoping."""
        app = App(flag_scope="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            user: str = "default",
        ):
            result = app(tokens)
            return {"user": user, **result}

        @app.command
        def foo(*, count: int = 0):
            return {"count": count}

        result = app.meta(["--user", "alice", "foo", "--count", "5"])
        assert result == {"user": "alice", "count": 5}

    def test_flag_scope_none_preserves_current_behavior(self):
        """When flag_scope is None, behavior is unchanged (flat parsing)."""
        app = App(result_action="return_value")  # flag_scope=None (default)

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: Annotated[bool, Parameter(alias="-v")] = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(*, version: Annotated[bool, Parameter(alias="-v")] = False):
            return {"version": version}

        # With flat parsing (current behavior), -v after foo is consumed by meta's verbose
        result = app.meta(["foo", "-v"])
        assert result == {"verbose": True, "version": False}
