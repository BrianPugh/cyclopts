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

    def test_flag_scope_default_is_bubble_up(self):
        """When flag_scope is not set, it defaults to bubble-up (child wins)."""
        app = App(result_action="return_value")  # flag_scope=None → defaults to "bubble-up"

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

        # Default bubble-up: -v after foo goes to child (child wins)
        result = app.meta(["foo", "-v"])
        assert result == {"verbose": False, "version": True}


class TestTokensReassembly:
    """Tests that the meta app's *tokens receives the correct subset."""

    def test_tokens_exclude_meta_flags_strict(self):
        """In strict mode, *tokens should not contain meta-level flags."""
        app = App(flag_scope="strict", result_action="return_value")
        captured_tokens = []

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
            user: str = "default",
        ):
            captured_tokens.extend(tokens)
            return app(tokens)

        @app.command
        def foo(name: str, *, debug: bool = False):
            return {"name": name, "debug": debug}

        app.meta(["--verbose", "--user", "alice", "foo", "--debug", "myname"])
        assert captured_tokens == ["foo", "--debug", "myname"]

    def test_tokens_exclude_bubbled_flags(self):
        """In bubble-up mode, *tokens should not contain bubbled-up flags."""
        app = App(flag_scope="bubble-up", result_action="return_value")
        captured_tokens = []

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
            user: str = "default",
        ):
            captured_tokens.extend(tokens)
            return app(tokens)

        @app.command
        def foo(name: str, *, debug: bool = False):
            return {"name": name, "debug": debug}

        # --verbose before foo → meta flag, --user after foo → bubbles up
        app.meta(["--verbose", "foo", "--debug", "--user", "alice", "myname"])
        assert captured_tokens == ["foo", "--debug", "myname"]

    def test_tokens_preserve_child_flags(self):
        """Child flags remain in *tokens even when meta defines the same flag."""
        app = App(flag_scope="bubble-up", result_action="return_value")
        captured_tokens = []

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: Annotated[bool, Parameter(alias="-v")] = False,
        ):
            captured_tokens.extend(tokens)
            return app(tokens)

        @app.command
        def foo(*, version: Annotated[bool, Parameter(alias="-v")] = False):
            return {"version": version}

        app.meta(["-v", "foo", "-v"])
        # First -v → meta (pre-command), second -v → child (child wins)
        assert captured_tokens == ["foo", "-v"]


class TestErrorMessages:
    """Tests for scope-aware error messages."""

    def test_strict_parent_match_suggests_placement(self):
        """In strict mode, if a parent defines the unknown flag, suggest placing it before the command."""
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

        with pytest.raises(UnknownOptionError, match="Did you mean to place it directly after"):
            app.meta(["foo", "--verbose"], exit_on_error=False)

    def test_strict_no_parent_match_normal_error(self):
        """In strict mode, if no parent defines the flag, show normal error."""
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

        with pytest.raises(UnknownOptionError, match='Unknown option: "--unknown"'):
            app.meta(["foo", "--unknown"], exit_on_error=False)

    def test_bubble_up_no_scope_error(self):
        """In bubble-up mode, parent flags after command don't error."""
        app = App(flag_scope="bubble-up", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo():
            return {}

        # Should NOT raise — --verbose bubbles up
        result = app.meta(["foo", "--verbose"])
        assert result == {"verbose": True}


class TestBubbleUpScope:
    """Tests for flag_scope='bubble-up'."""

    def test_non_conflicting_flag_bubbles_up(self):
        """A meta-only flag after a command bubbles up to meta."""
        app = App(flag_scope="bubble-up", result_action="return_value")

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

        # --verbose after foo bubbles up to meta (foo doesn't define it)
        result = app.meta(["foo", "--verbose"])
        assert result == {"verbose": True, "debug": False}

    def test_non_conflicting_flag_before_command(self):
        """A meta flag before the command works normally."""
        app = App(flag_scope="bubble-up", result_action="return_value")

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

    def test_conflicting_flag_child_wins(self):
        """When both levels define the same flag, child wins for post-command position."""
        app = App(flag_scope="bubble-up", result_action="return_value")

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

        # -v after foo → child wins (foo's version)
        result = app.meta(["foo", "-v"])
        assert result == {"verbose": False, "version": True}

        # -v at both levels
        result = app.meta(["-v", "foo", "-v"])
        assert result == {"verbose": True, "version": True}

    def test_unknown_flag_errors(self):
        """A flag unknown to both levels still errors."""
        app = App(flag_scope="bubble-up")

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

    def test_bubble_up_flag_with_value(self):
        """A meta flag with a value bubbles up correctly."""
        app = App(flag_scope="bubble-up", result_action="return_value")

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

        # --user after foo bubbles up, --count stays with foo
        result = app.meta(["foo", "--user", "alice", "--count", "5"])
        assert result == {"user": "alice", "count": 5}

    def test_bubble_up_does_not_land_in_star_args(self):
        """A flag unknown to both child and meta's named params should error,
        not silently land in *tokens.
        """
        app = App(flag_scope="bubble-up")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        ):
            app(tokens)

        @app.command
        def foo():
            pass

        # --mystery is unknown to foo and meta has no named params for it
        with pytest.raises(UnknownOptionError):
            app.meta(["foo", "--mystery"], exit_on_error=False)

    def test_multiple_flags_mixed_bubble_up(self):
        """Mix of child flags, meta flags, and positional args."""
        app = App(flag_scope="bubble-up", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
            user: str = "default",
        ):
            result = app(tokens)
            return {"verbose": verbose, "user": user, **result}

        @app.command
        def foo(name: str, *, debug: bool = False):
            return {"name": name, "debug": debug}

        result = app.meta(["foo", "--verbose", "--debug", "--user", "bob", "myname"])
        assert result == {"verbose": True, "user": "bob", "name": "myname", "debug": True}

    def test_bubble_up_with_equals_syntax(self):
        """Bubble-up works with --flag=value syntax."""
        app = App(flag_scope="bubble-up", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            user: str = "default",
        ):
            result = app(tokens)
            return {"user": user, **result}

        @app.command
        def foo(*, debug: bool = False):
            return {"debug": debug}

        result = app.meta(["foo", "--user=alice", "--debug"])
        assert result == {"user": "alice", "debug": True}
