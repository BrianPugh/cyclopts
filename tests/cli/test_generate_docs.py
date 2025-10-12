"""Tests for the 'cyclopts generate-docs' command."""

from textwrap import dedent
from unittest.mock import patch

import pytest

from cyclopts.cli import app as cyclopts_cli


def test_generate_docs_to_stdout(tmp_path, capsys):
    """Test generating docs to stdout with explicit format."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="myapp", help="Test application")

            @app.default
            def main(name: str = "World"):
                '''Greet someone.

                Parameters
                ----------
                name : str
                    Name to greet.
                '''
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "--format", "markdown"])

    captured = capsys.readouterr()
    assert "# myapp" in captured.out
    assert "Test application" in captured.out


def test_generate_docs_to_file(tmp_path, capsys):
    """Test generating docs to a file."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="myapp", help="Test app")

            @app.default
            def main():
                '''Main command.'''
                pass
            """
        )
    )

    output_file = tmp_path / "docs.md"

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "--output", str(output_file)])

    assert output_file.exists()
    content = output_file.read_text()
    assert "# myapp" in content
    assert "Test app" in content


def test_generate_docs_format_inference_md(tmp_path):
    """Test format inference from .md extension."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App
            app = App(name="myapp", help="Test")
            """
        )
    )

    output_file = tmp_path / "docs.md"

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "-o", str(output_file)])

    assert output_file.exists()
    content = output_file.read_text()
    assert "# myapp" in content


def test_generate_docs_explicit_format_overrides_extension(tmp_path):
    """Test that explicit format overrides file extension."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App
            app = App(name="myapp", help="Test")
            """
        )
    )

    output_file = tmp_path / "docs.txt"

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "-o", str(output_file), "--format", "markdown"])

    assert output_file.exists()
    content = output_file.read_text()
    assert "# myapp" in content


def test_generate_docs_no_format_no_output_error(capsys):
    """Test error when neither format nor output is specified."""
    with pytest.raises((SystemExit, ValueError)):
        cyclopts_cli(["generate-docs", "dummy.py"])


def test_generate_docs_invalid_extension_error(tmp_path, capsys):
    """Test error when output file has invalid extension."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App
            app = App(name="myapp")
            """
        )
    )

    output_file = tmp_path / "docs.pdf"

    with pytest.raises((SystemExit, ValueError)):
        cyclopts_cli(["generate-docs", str(script), "-o", str(output_file)])


def test_generate_docs_with_include_hidden(tmp_path, capsys):
    """Test generating docs with hidden commands included."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="myapp")

            @app.command(show=False)
            def hidden():
                '''Hidden command.'''
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "--format", "markdown", "--include-hidden"])

    captured = capsys.readouterr()
    assert "hidden" in captured.out.lower()


def test_generate_docs_with_heading_level(tmp_path, capsys):
    """Test custom heading level."""
    script = tmp_path / "app.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app = App(name="myapp", help="Test")

            @app.command
            def cmd():
                '''Command.'''
                pass
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", str(script), "--format", "markdown", "--heading-level", "2"])

    captured = capsys.readouterr()
    assert "## myapp" in captured.out


def test_generate_docs_with_app_notation(tmp_path, capsys):
    """Test generating docs with :app notation."""
    script = tmp_path / "multi.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app1 = App(name="app1", help="First app")
            app2 = App(name="app2", help="Second app")
            """
        )
    )

    with patch("sys.exit"):
        cyclopts_cli(["generate-docs", f"{script}:app2", "--format", "markdown"])

    captured = capsys.readouterr()
    assert "# app2" in captured.out
    assert "Second app" in captured.out


def test_generate_docs_script_not_found(tmp_path, capsys):
    """Test error when script not found."""
    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["generate-docs", str(tmp_path / "nonexistent.py"), "--format", "markdown"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()
