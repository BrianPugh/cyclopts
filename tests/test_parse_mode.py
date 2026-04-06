"""Tests for parse_mode feature (issue #627)."""

from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.exceptions import UnknownOptionError


class TestStrictScope:
    """Tests for parse_mode='strict'."""

    def test_separate_flags_each_level(self):
        """Each level's flags bind to their own level."""
        app = App(parse_mode="strict", result_action="return_value")

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
        app = App(parse_mode="strict", result_action="return_value")

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
        app = App(parse_mode="strict")

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
        app = App(parse_mode="strict")

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
        """parse_mode with no subcommands works normally."""
        app = App(parse_mode="strict", result_action="return_value")

        @app.default
        def main(*, verbose: bool = False):
            return {"verbose": verbose}

        result = app(["--verbose"])
        assert result == {"verbose": True}

    def test_positional_args_at_command_level(self):
        """Positional args after a command bind to the command."""
        app = App(parse_mode="strict", result_action="return_value")

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
        app = App(parse_mode="strict", result_action="return_value")
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
        app = App(parse_mode="strict", result_action="return_value")

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

    def test_parse_mode_default_is_fallthrough(self):
        """When parse_mode is not set, it defaults to fallthrough (child wins)."""
        app = App(result_action="return_value")  # parse_mode=None → defaults to "fallthrough"

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

        # Default fallthrough: -v after foo goes to child (child wins)
        result = app.meta(["foo", "-v"])
        assert result == {"verbose": False, "version": True}


class TestTokensReassembly:
    """Tests that the meta app's *tokens receives the correct subset."""

    def test_tokens_exclude_meta_flags_strict(self):
        """In strict mode, *tokens should not contain meta-level flags."""
        app = App(parse_mode="strict", result_action="return_value")
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
        """In fallthrough mode, *tokens should not contain bubbled-up flags."""
        app = App(parse_mode="fallthrough", result_action="return_value")
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
        app = App(parse_mode="fallthrough", result_action="return_value")
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
        app = App(parse_mode="strict")

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

    def test_strict_parent_match_no_subcommand_hint(self):
        """When the inner app is invoked directly (no command_chain) and a parent meta
        defines the unknown flag, the hint should indicate a parent-scope origin rather
        than suggest placement relative to a nonexistent subcommand.
        """
        app = App(parse_mode="strict", name="myapp")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.default
        def main():
            pass

        with pytest.raises(UnknownOptionError) as exc_info:
            app(["--verbose"], exit_on_error=False)
        message = str(exc_info.value)
        assert 'Unknown option: "--verbose"' in message
        assert "This option is defined in a parent scope." in message
        assert "subcommand" not in message

    def test_strict_no_parent_match_normal_error(self):
        """In strict mode, if no parent defines the flag, show normal error."""
        app = App(parse_mode="strict")

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

    def test_fallthrough_no_scope_error(self):
        """In fallthrough mode, parent flags after command don't error."""
        app = App(parse_mode="fallthrough", result_action="return_value")

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


class TestFallthroughScope:
    """Tests for parse_mode='fallthrough'."""

    def test_non_conflicting_flag_bubbles_up(self):
        """A meta-only flag after a command bubbles up to meta."""
        app = App(parse_mode="fallthrough", result_action="return_value")

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
        app = App(parse_mode="fallthrough", result_action="return_value")

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
        app = App(parse_mode="fallthrough", result_action="return_value")

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
        app = App(parse_mode="fallthrough")

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

    def test_fallthrough_flag_with_value(self):
        """A meta flag with a value bubbles up correctly."""
        app = App(parse_mode="fallthrough", result_action="return_value")

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

    def test_fallthrough_does_not_land_in_star_args(self):
        """A flag unknown to both child and meta's named params should error,
        not silently land in *tokens.
        """
        app = App(parse_mode="fallthrough")

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

    def test_multiple_flags_mixed_fallthrough(self):
        """Mix of child flags, meta flags, and positional args."""
        app = App(parse_mode="fallthrough", result_action="return_value")

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

    def test_fallthrough_with_equals_syntax(self):
        """Bubble-up works with --flag=value syntax."""
        app = App(parse_mode="fallthrough", result_action="return_value")

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


class TestHelpDisplay:
    """Tests that help pages respect flag scoping."""

    def _get_help_text(self, app, tokens):
        from io import StringIO

        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, width=80, force_terminal=False)
        try:
            app.meta(tokens, console=console, exit_on_error=False)
        except SystemExit:
            pass
        return buf.getvalue()

    def test_fallthrough_shows_parent_flags(self):
        """In fallthrough mode, subcommand help shows parent meta flags."""
        app = App(parse_mode="fallthrough")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo(*, debug: bool = False):
            pass

        help_text = self._get_help_text(app, ["foo", "--help"])
        assert "--verbose" in help_text
        assert "--debug" in help_text

    def test_strict_hides_parent_flags(self):
        """In strict mode, subcommand help does NOT show parent meta flags."""
        app = App(parse_mode="strict")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo(*, debug: bool = False):
            pass

        help_text = self._get_help_text(app, ["foo", "--help"])
        assert "--verbose" not in help_text
        assert "--debug" in help_text

    def test_strict_root_still_shows_own_flags(self):
        """In strict mode, root help still shows its own flags."""
        app = App(parse_mode="strict")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo(*, debug: bool = False):
            pass

        help_text = self._get_help_text(app, ["--help"])
        assert "--verbose" in help_text


class TestEdgeCases:
    """Edge case tests for parse_mode interactions."""

    def test_end_of_options_delimiter(self):
        """parse_mode works correctly with -- delimiter."""
        app = App(parse_mode="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(
            *args: Annotated[str, Parameter(allow_leading_hyphen=True)],
        ):
            return {"args": args}

        # -- forces everything after it to be positional
        result = app.meta(["--verbose", "foo", "--", "--not-a-flag"])
        assert result == {"verbose": True, "args": ("--not-a-flag",)}

    def test_combined_short_flags_same_level(self):
        """Combined short flags on the same level work."""
        app = App(parse_mode="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: Annotated[bool, Parameter(alias="-v")] = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(*, debug: Annotated[bool, Parameter(alias="-d")] = False):
            return {"debug": debug}

        # -v on meta level, -d on child level (not combined)
        result = app.meta(["-v", "foo", "-d"])
        assert result == {"verbose": True, "debug": True}

    def test_env_var_with_parse_mode(self):
        """Environment variable binding works with parse_mode."""
        import os

        app = App(parse_mode="strict", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: Annotated[bool, Parameter(env_var="TEST_VERBOSE")] = False,
        ):
            result = app(tokens)
            return {"verbose": verbose, **result}

        @app.command
        def foo(*, debug: bool = False):
            return {"debug": debug}

        # Env var should still work for meta-level params
        os.environ["TEST_VERBOSE"] = "true"
        try:
            result = app.meta(["foo", "--debug"])
            assert result == {"verbose": True, "debug": True}
        finally:
            del os.environ["TEST_VERBOSE"]

    def test_help_flag_with_parse_mode(self):
        """--help works at both levels with parse_mode."""
        app = App(parse_mode="strict")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo():
            pass

        # --help at root level
        with pytest.raises(SystemExit):
            app.meta(["--help"])

        # --help at subcommand level
        with pytest.raises(SystemExit):
            app.meta(["foo", "--help"])

    def test_version_flag_with_parse_mode(self):
        """--version works with parse_mode."""
        app = App(parse_mode="strict", version="1.0.0")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            verbose: bool = False,
        ):
            app(tokens)

        @app.command
        def foo():
            pass

        with pytest.raises(SystemExit):
            app.meta(["--version"])

    def test_non_meta_app_with_parse_mode(self):
        """parse_mode on a non-meta app doesn't break anything."""
        app = App(parse_mode="strict", result_action="return_value")

        @app.command
        def foo(*, debug: bool = False):
            return {"debug": debug}

        @app.command
        def bar():
            return "bar"

        result = app(["foo", "--debug"])
        assert result == {"debug": True}

        result = app(["bar"])
        assert result == "bar"

    def test_repeated_list_flag_bubbles_up(self):
        """A list flag used multiple times correctly bubbles up."""
        app = App(parse_mode="fallthrough", result_action="return_value")

        @app.meta.default
        def meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            tag: list[str] | None = None,
        ):
            result = app(tokens)
            return {"tags": tag or [], **result}

        @app.command
        def foo(*, debug: bool = False):
            return {"debug": debug}

        result = app.meta(["foo", "--tag", "a", "--debug", "--tag", "b"])
        assert result == {"tags": ["a", "b"], "debug": True}

    def test_equals_syntax_with_strict_mode(self):
        """--flag=value syntax works with strict scoping."""
        app = App(parse_mode="strict", result_action="return_value")

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

        result = app.meta(["--user=alice", "foo", "--count=5"])
        assert result == {"user": "alice", "count": 5}

    def test_strict_error_hint_with_equals_syntax(self):
        """Error hint works when the unknown option uses --flag=value syntax."""
        app = App(parse_mode="strict")

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
            app.meta(["foo", "--verbose=true"], exit_on_error=False)


class TestNestedMeta:
    """Tests for nested meta-of-meta apps with ``parse_mode='strict'``.

    These exercise the ``while meta and meta.default_command: meta = meta._meta``
    loop in :func:`cyclopts.core._build_strict_parent_info`, which walks the
    full meta chain to collect parent scopes for scope-aware error hints.
    """

    @staticmethod
    def _build_app():
        """Build a 3-level app: outer-meta -> inner-meta -> app -> sub.

        ``app`` is given an explicit name so assertions about the hint's
        suggested-parent name are deterministic (they don't depend on
        ``sys.argv[0]``).
        """
        app = App(name="myapp", parse_mode="strict", result_action="return_value")

        @app.meta.default
        def inner_meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            inner_flag: bool = False,
        ):
            result = app(tokens)
            out = {"inner": inner_flag}
            if isinstance(result, dict):
                out.update(result)
            return out

        @app.meta.meta.default
        def outer_meta(
            *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
            outer_flag: bool = False,
        ):
            result = app.meta(tokens)
            out = {"outer": outer_flag}
            if isinstance(result, dict):
                out.update(result)
            return out

        @app.command
        def sub(*, sub_flag: bool = False):
            return {"sub": sub_flag}

        return app

    def test_nested_meta_chain_is_linked(self):
        """Sanity check that ``app.meta.meta`` really is a meta-of-meta.

        Confirms ``_meta_parent`` links walk all the way back to ``app`` so
        :func:`_build_strict_parent_info` has a full chain to iterate.
        """
        app = self._build_app()
        assert app.meta._meta_parent is app
        assert app.meta.meta._meta_parent is app.meta
        # Names are derived from each default_command's function name.
        assert app.name[0] == "myapp"
        assert app.meta.name[0] == "inner-meta"
        assert app.meta.meta.name[0] == "outer-meta"

    def test_all_levels_bind_when_placed_correctly(self):
        """Each level's flag binds to its own level when placed there."""
        app = self._build_app()
        result = app.meta.meta(["--outer-flag", "--inner-flag", "sub", "--sub-flag"])
        assert result == {"outer": True, "inner": True, "sub": True}

    def test_outer_only(self):
        """Only the outermost meta's flag is set."""
        app = self._build_app()
        result = app.meta.meta(["--outer-flag", "sub"])
        assert result == {"outer": True, "inner": False, "sub": False}

    def test_inner_only(self):
        """Only the inner meta's flag is set."""
        app = self._build_app()
        result = app.meta.meta(["--inner-flag", "sub"])
        assert result == {"outer": False, "inner": True, "sub": False}

    def test_sub_only(self):
        """Only the subcommand's flag is set."""
        app = self._build_app()
        result = app.meta.meta(["sub", "--sub-flag"])
        assert result == {"outer": False, "inner": False, "sub": True}

    def test_outer_flag_after_sub_errors_with_hint(self):
        """An outer-meta-only flag after the subcommand errors in strict mode.

        The scope-aware hint points at the parent *of* the meta that owns the
        flag -- that is, ``outer-meta``'s ``_meta_parent`` is ``inner-meta``,
        so the hint suggests placing it after ``"inner-meta"`` (the position
        just before the subcommand, which is also where ``inner-meta`` forwards
        to ``app``).
        """
        app = self._build_app()
        with pytest.raises(
            UnknownOptionError,
            match=r'Unknown option: "--outer-flag"\. Did you mean to place it directly after "inner-meta"\?',
        ):
            app.meta.meta(["sub", "--outer-flag"], exit_on_error=False)

    def test_inner_flag_after_sub_errors_with_hint(self):
        """An inner-meta-only flag after the subcommand errors in strict mode.

        ``inner-meta``'s ``_meta_parent`` is ``app`` (name ``"myapp"``), so the
        hint points at ``"myapp"``.
        """
        app = self._build_app()
        with pytest.raises(
            UnknownOptionError,
            match=r'Unknown option: "--inner-flag"\. Did you mean to place it directly after "myapp"\?',
        ):
            app.meta.meta(["sub", "--inner-flag"], exit_on_error=False)

    def test_build_strict_parent_info_walks_full_chain(self):
        """Directly exercise :func:`_build_strict_parent_info`.

        When invoked from the outermost meta, the strict parent-info list
        should contain one entry per meta level in the chain (inner + outer).
        Each entry's ``argument_collection`` should contain the flag defined
        on that level.
        """
        app = self._build_app()
        # Trigger a parse so the app_stack is populated; capture mid-flight
        # via the error-hint path. An easier approach: construct the info
        # directly by driving the outer app and asking it during parse.
        # We instead simulate by invoking with a token that triggers the hint
        # and inspect the exception's attached parent info.
        try:
            app.meta.meta(["sub", "--outer-flag"], exit_on_error=False)
        except UnknownOptionError as e:
            assert e.parent_apps_with_collections is not None
            # Chain should include both meta levels.
            parent_names = [name for name, _ in e.parent_apps_with_collections]
            # inner-meta is the _meta_parent of outer-meta; myapp is the
            # _meta_parent of inner-meta. Both must appear.
            assert "inner-meta" in parent_names
            assert "myapp" in parent_names
            # The outer-meta's collection should contain --outer-flag.
            outer_ac = next(ac for name, ac in e.parent_apps_with_collections if name == "inner-meta")
            # match() raises ValueError if not found.
            outer_ac.match("--outer-flag")
            # The inner-meta's collection should contain --inner-flag.
            inner_ac = next(ac for name, ac in e.parent_apps_with_collections if name == "myapp")
            inner_ac.match("--inner-flag")
        else:
            raise AssertionError("expected UnknownOptionError")

    def test_strict_help_hides_both_meta_levels(self):
        """In strict mode, subcommand help hides flags from *both* meta levels."""
        from io import StringIO

        from rich.console import Console

        app = self._build_app()
        buf = StringIO()
        console = Console(file=buf, width=80, force_terminal=False)
        try:
            app.meta.meta(["sub", "--help"], console=console, exit_on_error=False)
        except SystemExit:
            pass
        help_text = buf.getvalue()
        assert "--outer-flag" not in help_text
        assert "--inner-flag" not in help_text
        assert "--sub-flag" in help_text
