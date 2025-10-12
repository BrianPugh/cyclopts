"""Tests for the hidden '_complete' command for dynamic completion."""

from textwrap import dedent
from unittest.mock import patch

from cyclopts.cli import app as cyclopts_cli


def test_complete_run_subcommand(tmp_path, capsys):
    """Test completion for 'run' subcommand."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="testapp")

            @app.command
            def build():
                '''Build the project.'''
                pass

            @app.command
            def deploy():
                '''Deploy the app.'''
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script)])

    captured = capsys.readouterr()
    assert "build" in captured.out
    assert "deploy" in captured.out


def test_complete_run_with_options(tmp_path, capsys):
    """Test completion includes options."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="testapp")

            @app.default
            def main(verbose: bool = False, count: int = 1):
                '''Main command.'''
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script)])

    captured = capsys.readouterr()
    assert "--verbose" in captured.out
    assert "--count" in captured.out


def test_complete_run_invalid_script_silent(tmp_path, capsys):
    """Test that completion silently fails for invalid scripts."""
    nonexistent = tmp_path / "nonexistent.py"

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(nonexistent)])

    captured = capsys.readouterr()
    assert captured.out == ""


def test_complete_run_nested_commands(tmp_path, capsys):
    """Test completion for nested command structure."""
    script = tmp_path / "nested.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="testapp")
            db = App(name="db", help="Database commands")

            @db.command
            def migrate():
                '''Run migrations.'''
                pass

            app.command(db)
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script)])

    captured = capsys.readouterr()
    assert "db" in captured.out


def test_complete_run_with_words(tmp_path, capsys):
    """Test completion with current command line words."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="testapp")
            db = App(name="db")

            @db.command
            def migrate():
                '''Run migrations.'''
                pass

            @db.command
            def backup():
                '''Backup database.'''
                pass

            app.command(db)
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script), "db"])

    captured = capsys.readouterr()
    assert "migrate" in captured.out
    assert "backup" in captured.out


def test_complete_non_run_subcommand_silent(tmp_path, capsys):
    """Test that completion is silent for non-run subcommands."""
    script = tmp_path / "app.py"
    script.write_text("from cyclopts import App\napp = App()")

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "generate-docs", str(script)])

    captured = capsys.readouterr()
    assert captured.out == ""


def test_complete_run_script_with_syntax_error_silent(tmp_path, capsys):
    """Test that completion silently handles scripts with syntax errors."""
    script = tmp_path / "broken.py"
    script.write_text("this is not valid python $$$ @@@")

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script)])

    captured = capsys.readouterr()
    assert captured.out == ""


def test_complete_shows_help_for_default_command(tmp_path, capsys):
    """Test that options from default command are shown."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App
            from typing import Annotated
            from cyclopts import Parameter

            app = App(name="testapp")

            @app.default
            def main(
                verbose: Annotated[bool, Parameter(help="Enable verbose mode")] = False,
                debug: Annotated[bool, Parameter(help="Enable debug mode")] = False,
            ):
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["_complete", "run", str(script)])

    captured = capsys.readouterr()
    assert "--verbose" in captured.out
    assert "--debug" in captured.out
    assert "Enable verbose mode" in captured.out or "verbose mode" in captured.out.lower()
