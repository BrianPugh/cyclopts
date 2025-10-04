"""Performance and import optimization regression tests."""

import subprocess
import sys
import textwrap


def test_rich_not_imported_on_happy_path():
    """Ensure Rich library is not imported during happy path execution.

    Rich is only needed for error formatting and help display.
    For successful CLI execution, it should not be imported to minimize startup time.
    This test prevents regressions where Rich might accidentally get imported early.
    """
    script = textwrap.dedent("""
        import sys
        import cyclopts

        app = cyclopts.App()

        @app.default
        def main(name: str = "world"):
            return f"Hello, {name}!"

        # Execute happy path
        sys.argv = ["test", "--name", "Alice"]
        result = app()

        # Check Rich was not imported
        assert "rich" not in sys.modules, f"Rich was imported! Modules: {[m for m in sys.modules if 'rich' in m]}"
        print("SUCCESS: Rich not imported")
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "SUCCESS: Rich not imported" in result.stdout


def test_lazy_modules_not_imported_on_happy_path():
    """Ensure lazy-loaded modules are not imported during happy path execution.

    Modules like types, validators, and _edit should only be imported when explicitly used.
    This test prevents regressions where these might accidentally get eagerly imported.
    """
    script = textwrap.dedent("""
        import sys
        import cyclopts

        app = cyclopts.App()

        @app.default
        def main(value: int = 42):
            return value * 2

        # Execute happy path
        sys.argv = ["test", "--value", "21"]
        result = app()
        assert result == 42

        # Check lazy modules were not imported
        lazy_modules = ["cyclopts.types", "cyclopts.validators", "cyclopts._edit"]
        imported_lazy = [m for m in lazy_modules if m in sys.modules]
        assert not imported_lazy, f"Lazy modules were imported: {imported_lazy}"
        print("SUCCESS: Lazy modules not imported")
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "SUCCESS: Lazy modules not imported" in result.stdout


def test_rich_is_imported_on_error():
    """Verify Rich IS imported when displaying errors.

    This ensures the optimization didn't break error formatting.
    """
    script = textwrap.dedent("""
        import sys
        import cyclopts

        app = cyclopts.App()

        @app.default
        def main(value: int):
            return value

        # Execute with missing required argument (should error)
        sys.argv = ["test"]
        try:
            app()
        except SystemExit:
            pass  # Expected

        # Rich should now be imported for error display
        assert "rich" in sys.modules, "Rich should be imported for error display"
        print("SUCCESS: Rich imported for error")
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "SUCCESS: Rich imported for error" in result.stdout


def test_lazy_modules_imported_when_accessed():
    """Verify lazy modules ARE imported when explicitly accessed.

    This ensures the lazy loading mechanism works correctly.
    """
    script = textwrap.dedent("""
        import sys
        import cyclopts

        # Initially not imported
        assert "cyclopts.types" not in sys.modules
        assert "cyclopts.validators" not in sys.modules

        # Access them
        _ = cyclopts.types
        _ = cyclopts.validators

        # Now they should be imported
        assert "cyclopts.types" in sys.modules
        assert "cyclopts.validators" in sys.modules
        print("SUCCESS: Lazy modules imported on access")
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "SUCCESS: Lazy modules imported on access" in result.stdout
