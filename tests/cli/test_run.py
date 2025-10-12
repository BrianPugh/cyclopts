"""Tests for the 'cyclopts run' command."""

import sys
from textwrap import dedent

import pytest

from cyclopts.cli import app as cyclopts_cli


def test_run_simple_script(tmp_path, capsys):
    """Test running a simple script with default app."""
    script = tmp_path / "simple.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="simple")

            @app.default
            def main(name: str = "World"):
                print(f"Hello, {name}!")

            if __name__ == "__main__":
                app()
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script)])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Hello, World!" in captured.out


def test_run_script_with_args(tmp_path, capsys):
    """Test running a script with command-line arguments."""
    script = tmp_path / "greet.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="greet")

            @app.default
            def main(name: str, greeting: str = "Hello"):
                print(f"{greeting}, {name}!")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script), "--name", "Alice", "--greeting", "Hi"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Hi, Alice!" in captured.out


def test_run_script_with_positional_args(tmp_path, capsys):
    """Test running a script with positional arguments."""
    script = tmp_path / "echo.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="echo")

            @app.default
            def main(message: str):
                print(message)
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script), "Hello World"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Hello World" in captured.out


def test_run_script_with_app_notation(tmp_path, capsys):
    """Test running a script with ':app_name' notation."""
    script = tmp_path / "multi.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app1 = App(name="app1")
            app2 = App(name="app2")

            @app1.default
            def main1():
                print("App 1")

            @app2.default
            def main2():
                print("App 2")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", f"{script}:app2"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "App 2" in captured.out


def test_run_script_with_subcommands(tmp_path, capsys):
    """Test running a script with subcommands."""
    script = tmp_path / "commands.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="commands")

            @app.command
            def build():
                print("Building...")

            @app.command
            def deploy():
                print("Deploying...")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script), "build"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Building..." in captured.out


def test_run_script_not_found(tmp_path, capsys):
    """Test error when script file not found."""
    nonexistent = tmp_path / "nonexistent.py"

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(nonexistent)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_run_not_python_file(tmp_path, capsys):
    """Test error when file is not a Python file."""
    textfile = tmp_path / "notpython.txt"
    textfile.write_text("This is not Python")

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(textfile)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "not a python file" in captured.err.lower()


def test_run_no_app_found(tmp_path, capsys):
    """Test error when no App object found in script."""
    script = tmp_path / "noapp.py"
    script.write_text(
        dedent(
            """\
            # No App object here
            def main():
                print("No app")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "no cyclopts app" in captured.err.lower()


def test_run_multiple_apps_error(tmp_path, capsys):
    """Test error when multiple App objects found without specification."""
    script = tmp_path / "multiapp.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app1 = App(name="app1")
            app2 = App(name="app2")

            @app1.default
            def main1():
                pass

            @app2.default
            def main2():
                pass
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "multiple app objects" in captured.err.lower()


def test_run_specified_app_not_found(tmp_path, capsys):
    """Test error when specified app object not found."""
    script = tmp_path / "test.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App
            app = App()
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", f"{script}:nonexistent"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "no object named" in captured.err.lower()


def test_run_specified_object_not_app(tmp_path, capsys):
    """Test error when specified object is not an App."""
    script = tmp_path / "notapp.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App()
            some_string = "not an app"
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", f"{script}:some_string"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "not a cyclopts app" in captured.err.lower()


def test_run_with_variadic_args(tmp_path, capsys):
    """Test running script with variadic arguments."""
    script = tmp_path / "variadic.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="variadic")

            @app.default
            def main(*files: str):
                for f in files:
                    print(f"Processing: {f}")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script), "file1.txt", "file2.txt", "file3.txt"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Processing: file1.txt" in captured.out
    assert "Processing: file2.txt" in captured.out
    assert "Processing: file3.txt" in captured.out


def test_run_with_leading_hyphen(tmp_path, capsys):
    """Test that script path can start with hyphen."""
    script = tmp_path / "-special.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="special")

            @app.default
            def main():
                print("Special script")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script)])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Special script" in captured.out


def test_run_script_with_import_error(tmp_path, capsys):
    """Test handling script with import errors."""
    script = tmp_path / "broken.py"
    script.write_text(
        dedent(
            """\
            import nonexistent_module
            from cyclopts import App
            app = App()
            """
        )
    )

    with pytest.raises((SystemExit, ImportError)):
        cyclopts_cli(["run", str(script)])


@pytest.mark.skipif(sys.platform == "win32", reason="Windows path handling differs")
def test_run_script_with_windows_path_colon(tmp_path, capsys):
    """Test that Windows paths with drive letters are handled correctly."""
    script = tmp_path / "winpath.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="winpath")

            @app.default
            def main():
                print("Windows path")
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["run", str(script.resolve())])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Windows path" in captured.out
