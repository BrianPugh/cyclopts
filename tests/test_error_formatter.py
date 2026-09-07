import textwrap
from io import StringIO

import pytest
from rich.console import Console

import cyclopts
from cyclopts import CoercionError


def test_error_formatter_default_none():
    app = cyclopts.App()
    assert app.error_formatter is None


def test_error_formatter_custom():
    """A custom error_formatter replaces CycloptsPanel output."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    def my_formatter(e):
        return f"error: {e}"

    app = cyclopts.App(error_formatter=my_formatter, result_action="return_value")

    @app.default
    def main(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("abc", exit_on_error=False, error_console=error_console)

    assert buf.getvalue() == 'error: Invalid value for VALUE: unable to convert "abc" into int.\n'


def test_error_formatter_none_uses_cyclopts_panel():
    """When error_formatter is None, the default CycloptsPanel is used."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    app = cyclopts.App(result_action="return_value")

    @app.default
    def main(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("abc", exit_on_error=False, error_console=error_console)

    expected = textwrap.dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for VALUE: unable to convert "abc" into int.         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert buf.getvalue() == expected


def test_error_formatter_runtime_override():
    """error_formatter can be passed as a runtime argument to parse_args."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    def my_formatter(e):
        return f"custom: {e}"

    app = cyclopts.App(result_action="return_value")

    @app.default
    def main(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("abc", exit_on_error=False, error_console=error_console, error_formatter=my_formatter)

    assert buf.getvalue() == 'custom: Invalid value for VALUE: unable to convert "abc" into int.\n'


def test_error_formatter_inherited_by_subcommand():
    """Subcommands inherit error_formatter from the parent app."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=120, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    def my_formatter(e):
        return f"inherited: {e}"

    app = cyclopts.App(error_formatter=my_formatter, result_action="return_value")

    @app.command
    def sub(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("sub abc", exit_on_error=False, error_console=error_console)

    assert buf.getvalue() == 'inherited: Invalid value for VALUE: unable to convert "abc" into int.\n'


@pytest.mark.parametrize("via_call", [False, True])
def test_error_formatter_defined_on_subcommand(via_call):
    """A subcommand's own error_formatter is honored on a parse error in that subcommand.

    Regression test for the #933 family: error-reporting settings were resolved from the
    root app's stack (which never contains the subcommand), so a subcommand-level
    error_formatter was ignored. Exercised via both ``__call__`` and ``parse_args``.
    """
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    def my_formatter(e):
        return f"sub: {e}"

    app = cyclopts.App(result_action="return_value")

    @app.command(error_formatter=my_formatter)
    def sub(value: int):
        pass

    if via_call:
        with pytest.raises(SystemExit):
            app(["sub", "abc"], error_console=error_console)
    else:
        with pytest.raises(CoercionError):
            app.parse_args(["sub", "abc"], exit_on_error=False, error_console=error_console)

    assert buf.getvalue() == 'sub: Invalid value for VALUE: unable to convert "abc" into int.\n'


@pytest.mark.parametrize("via_call", [False, True])
def test_exit_on_error_defined_on_subcommand(via_call):
    """A subcommand's ``exit_on_error=False`` is honored (raises instead of exiting).

    Regression test for the #933 family. ``parse_args`` also covers the case where the
    command context is torn down before the error is handled, so the setting must be
    resolved while that context is live.
    """
    app = cyclopts.App(result_action="return_value")

    @app.command(exit_on_error=False)
    def sub(value: int):
        pass

    # Root default exit_on_error is True; only the subcommand disables it.
    with pytest.raises(CoercionError):
        if via_call:
            app(["sub", "abc"])
        else:
            app.parse_args(["sub", "abc"])


def test_print_error_defined_on_subcommand():
    """A subcommand's ``print_error=False`` suppresses error output (#933 family)."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    app = cyclopts.App(result_action="return_value")

    @app.command(print_error=False)
    def sub(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args(["sub", "abc"], exit_on_error=False, error_console=error_console)

    assert buf.getvalue() == ""


def test_help_on_error_defined_on_subcommand():
    """A subcommand's ``help_on_error=True`` prints the help page before the error (#933 family)."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    app = cyclopts.App(name="prog", result_action="return_value")

    @app.command(help_on_error=True)
    def sub(value: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args(["sub", "abc"], exit_on_error=False, error_console=error_console)

    # The subcommand help page is emitted ahead of the error (root default is help_on_error=False).
    assert "Usage: prog sub" in buf.getvalue()


def test_verbose_defined_on_subcommand():
    """A subcommand's ``verbose=True`` propagates to the raised error (#933 family)."""
    app = cyclopts.App(result_action="return_value")

    @app.command(verbose=True)
    def sub(value: int):
        pass

    with pytest.raises(CoercionError) as exc_info:
        app.parse_args(["sub", "abc"], exit_on_error=False, print_error=False)

    assert exc_info.value.verbose is True


def test_error_formatter_call():
    """error_formatter works when using __call__ instead of parse_args."""
    buf = StringIO()
    error_console = Console(
        file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False
    )

    def my_formatter(e):
        return f"call: {e}"

    app = cyclopts.App(error_formatter=my_formatter, result_action="return_value")

    @app.default
    def main(value: int):
        pass

    with pytest.raises(SystemExit):
        app("abc", error_console=error_console)

    assert buf.getvalue() == 'call: Invalid value for VALUE: unable to convert "abc" into int.\n'
