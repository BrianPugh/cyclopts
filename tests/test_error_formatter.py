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

    assert buf.getvalue() == 'error: Invalid value for "VALUE": unable to convert "abc" into int.\n'


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
        │ Invalid value for "VALUE": unable to convert "abc" into int.       │
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

    assert buf.getvalue() == 'custom: Invalid value for "VALUE": unable to convert "abc" into int.\n'


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

    assert buf.getvalue() == 'inherited: Invalid value for "VALUE": unable to convert "abc" into int.\n'


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

    assert buf.getvalue() == 'call: Invalid value for "VALUE": unable to convert "abc" into int.\n'
