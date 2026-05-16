import subprocess
import warnings
from pathlib import Path

import pytest

import cyclopts.core
from cyclopts import App
from cyclopts.core import _log_framework_warning


@pytest.fixture(autouse=True)
def clear_cache():
    # Setup
    _log_framework_warning.cache_clear()

    yield

    # Teardown
    _log_framework_warning.cache_clear()


def test_app_iter(app):
    """Like a dictionary, __iter__ of an App should yield keys (command names)."""

    @app.command
    def foo():
        pass

    @app.command
    def bar():
        pass

    actual = list(app)
    assert actual == ["--help", "-h", "--version", "foo", "bar"]


def test_app_iter_with_meta(app):
    @app.command
    def foo():
        pass

    @app.command
    def bar():
        pass

    @app.meta.command
    def fizz():
        pass

    actual = list(app)
    assert actual == ["--help", "-h", "--version", "foo", "bar"]

    actual = list(app.meta)
    assert actual == ["--help", "-h", "--version", "fizz", "foo", "bar"]


def test_app_update():
    app1 = App()
    app2 = App()

    @app1.command
    def foo():
        pass

    @app2.command
    def bar():
        pass

    app1.update(app2)

    assert list(app1) == ["--help", "-h", "--version", "foo", "bar"]


def test_log_framework_warning_unknown():
    # Should not generate a warning for UNKNOWN framework
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Convert warnings to errors
        _log_framework_warning(cyclopts.core.TestFramework.UNKNOWN)  # Should not raise


def test_log_framework_warning_pytest(app):
    # Should generate a warning when called from non-cyclopts module
    with pytest.warns(UserWarning) as warning_records:
        try:
            app(exit_on_error=False)
        except Exception:
            pass

    assert len(warning_records) == 1
    warning_msg = str(warning_records[0].message)
    assert (
        warning_msg
        == 'Cyclopts application invoked without tokens under unit-test framework "pytest". Did you mean "app([])"?'
    )


@pytest.mark.skip(reason="code-coverage injects pytest into subprocess. Otherwise works.")
def test_log_framework_warning_pytest_subprocess():
    current_dir = Path(__file__).parent

    # Construct the path to the script relative to the test file
    script_path = current_dir / "empty_app.py"

    # Run the script using the constructed path
    result = subprocess.run(
        ["python", str(script_path)],
        capture_output=True,
        text=True,
    )

    assert "Cyclopts application invoked without tokens under unit-test framework" not in result.stderr
