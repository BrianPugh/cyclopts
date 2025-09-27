"""Tests for App.generate_docs() method."""

import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Annotated

from cyclopts import App, Parameter


def test_generate_docs_simple_app():
    """Test basic documentation generation for a simple app."""
    app = App(name="myapp", help="A simple CLI application")

    @app.default
    def main(name: str, verbose: bool = False):
        """Main command.

        Parameters
        ----------
        name : str
            Your name.
        verbose : bool
            Enable verbose output.
        """
        pass

    actual = app.generate_docs()

    expected = dedent(
        """\
        # myapp

        A simple CLI application

        ## Usage

        ```
        Usage: myapp [ARGS] [OPTIONS]
        ```

        ## Parameters

        | Required | Parameter | Description |
        | :------: | --------- | ----------- |
        | ✓ | `NAME`, `--name` | Your name.<br><br>Type: `<class 'str'>` |
        |  | `VERBOSE`, `--verbose`, `--no-verbose` | Enable verbose output.<br><br>Type: `<class 'bool'>`<br>Default: `False` |
        """
    )

    assert actual == expected


def test_generate_docs_with_commands():
    """Test documentation generation with subcommands."""
    app = App(name="myapp", help="CLI with commands")

    @app.command
    def serve(port: int = 8000):
        """Start the server.

        Parameters
        ----------
        port : int
            Port number.
        """
        pass

    @app.command
    def build(output: str = "./dist"):
        """Build the project.

        Parameters
        ----------
        output : str
            Output directory.
        """
        pass

    actual = app.generate_docs()

    # Check structure without being too specific about Usage lines that vary by context
    assert "# myapp" in actual
    assert "CLI with commands" in actual

    # Main usage section
    assert "## Usage" in actual
    assert "Usage: myapp COMMAND" in actual

    # Commands table
    assert "## Commands" in actual
    assert "| `build` | Build the project. |" in actual
    assert "| `serve` | Start the server. |" in actual

    # Serve command details
    assert "## Command: serve" in actual
    assert "Start the server." in actual
    assert "### Usage" in actual
    assert "### Parameters" in actual
    assert "| `PORT`, `--port` | Port number.<br><br>Type: `<class 'int'>`<br>Default: `8000` |" in actual

    # Build command details
    assert "## Command: build" in actual
    assert "Build the project." in actual
    assert "| `OUTPUT`, `--output` | Output directory.<br><br>Type: `<class 'str'>`<br>Default: `./dist` |" in actual


def test_generate_docs_recursive():
    """Test recursive documentation generation."""
    app = App(name="myapp", help="Main app")

    subapp = App(name="db", help="Database commands")

    @subapp.command
    def migrate():
        """Run database migrations."""
        pass

    @subapp.command
    def backup(output: str):
        """Backup the database.

        Parameters
        ----------
        output : str
            Backup file path.
        """
        pass

    app.command(subapp)

    actual = app.generate_docs(recursive=True)

    # Verify structure of recursive documentation
    assert "# myapp" in actual
    assert "Main app" in actual
    assert "## Command: db" in actual
    assert "Database commands" in actual
    assert "migrate" in actual
    assert "backup" in actual
    assert "Run database migrations" in actual
    assert "Backup the database" in actual


def test_generate_docs_non_recursive():
    """Test non-recursive documentation generation."""
    app = App(name="myapp", help="Main app")

    subapp = App(name="db", help="Database commands")

    @subapp.command
    def migrate():
        """Run database migrations."""
        pass

    app.command(subapp)

    actual = app.generate_docs(recursive=False)

    expected = dedent(
        """\
        # myapp

        Main app

        ## Usage

        ```
        Usage: myapp COMMAND
        ```

        ## Commands

        | Command | Description |
        | ------- | ----------- |
        | `db` | Database commands |

        ## Command: db

        Database commands

        ### Usage

        ```
        Usage: myapp db COMMAND
        ```
        """
    )

    assert actual == expected


def test_generate_docs_with_hidden_commands(mocker):
    """Test documentation with hidden commands."""
    # Mock sys.argv[0] for consistent output
    mocker.patch("sys.argv", ["myapp"])

    app = App(name="myapp", help="App with hidden commands")

    @app.command
    def visible():
        """Visible command."""
        pass

    @app.command(show=False)
    def hidden():
        """Hidden command."""
        pass

    # Test WITHOUT include_hidden
    actual_without_hidden = app.generate_docs(include_hidden=False)

    expected_without_hidden = dedent(
        """\
        # myapp

        App with hidden commands

        ## Usage

        ```
        Usage: myapp COMMAND
        ```

        ## Commands

        | Command | Description |
        | ------- | ----------- |
        | `visible` | Visible command. |

        ## Command: visible

        Visible command.

        ### Usage

        ```
        Usage: myapp
        ```
        """
    )

    assert actual_without_hidden == expected_without_hidden

    # Test WITH include_hidden
    actual_with_hidden = app.generate_docs(include_hidden=True)

    # Verify the hidden command is present when include_hidden=True
    assert "## Command: hidden" in actual_with_hidden
    assert "Hidden command." in actual_with_hidden
    # Also verify it has help and version commands shown
    assert "`--help`, `-h`" in actual_with_hidden
    assert "`--version`" in actual_with_hidden


def test_generate_docs_with_required_parameters():
    """Test documentation with required parameters."""
    app = App(name="myapp")

    @app.default
    def main(
        required: Annotated[str, Parameter(help="Required parameter")],
        optional: str = "default",
    ):
        """Main command."""
        pass

    actual = app.generate_docs()

    expected = dedent(
        """\
        # myapp

        Main command.

        ## Usage

        ```
        Usage: myapp [ARGS] [OPTIONS]
        ```

        ## Parameters

        | Required | Parameter | Description |
        | :------: | --------- | ----------- |
        | ✓ | `REQUIRED`, `--required` | Required parameter<br><br>Type: `<class 'str'>` |
        |  | `OPTIONAL`, `--optional` | Type: `<class 'str'>`<br>Default: `default` |
        """
    )

    assert actual == expected


def test_generate_docs_with_choices():
    """Test documentation with parameter choices."""
    from enum import Enum

    app = App(name="myapp")

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    @app.default
    def main(color: Color = Color.RED):
        """Choose a color."""
        pass

    actual = app.generate_docs()

    # Should show available choices in the documentation
    assert "red" in actual
    assert "green" in actual
    assert "blue" in actual
    assert "Choices:" in actual


def test_generate_docs_with_custom_usage():
    """Test documentation with custom usage string."""
    app = App(name="myapp", usage="myapp [OPTIONS] <input> <output>")

    @app.default
    def main():
        """Main command."""
        pass

    actual = app.generate_docs()

    expected = dedent(
        """\
        # myapp

        Main command.

        ## Usage

        ```
        myapp [OPTIONS] <input> <output>
        ```
        """
    )

    assert actual == expected


def test_generate_docs_no_usage():
    """Test documentation with suppressed usage."""
    app = App(name="myapp", usage="")  # Empty string suppresses usage

    @app.default
    def main():
        """Main command."""
        pass

    actual = app.generate_docs()

    expected = dedent(
        """\
        # myapp

        Main command.
        """
    )

    assert actual == expected


def test_generate_docs_write_to_file():
    """Test writing documentation to a file."""
    app = App(name="myapp", help="Test app")

    @app.default
    def main():
        """Main command."""
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "docs" / "cli.md"

        # Generate docs
        actual = app.generate_docs()

        expected = dedent(
            """\
            # myapp

            Test app

            ## Usage

            ```
            Usage: myapp
            ```
            """
        )

        # Write to file manually
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(actual)

        # Check file was created and contains expected content
        assert output_path.exists()
        content = output_path.read_text()
        assert content == expected

        # Should return the expected content
        assert actual == expected


def test_generate_docs_output_format_explicit():
    """Test explicitly specifying output format."""
    app = App(name="myapp", help="Test app")

    @app.default
    def main():
        """Main command."""
        pass

    # Explicitly specify markdown format
    actual = app.generate_docs(output_format="markdown")

    expected = dedent(
        """\
        # myapp

        Test app

        ## Usage

        ```
        Usage: myapp
        ```
        """
    )

    assert actual == expected


def test_generate_docs_output_format_markdown():
    """Test generating markdown format documentation."""
    app = App(name="myapp", help="Test app")

    @app.default
    def main():
        """Main command."""
        pass

    # Test markdown format (default)
    docs_md = app.generate_docs()
    assert "# myapp" in docs_md

    # Test explicitly specifying markdown
    docs_explicit = app.generate_docs(output_format="markdown")
    assert "# myapp" in docs_explicit
    assert docs_md == docs_explicit


def test_generate_docs_invalid_format():
    """Test that invalid output format raises ValueError."""
    import pytest

    app = App(name="myapp", help="Test app")

    with pytest.raises(ValueError, match="Unsupported output format: pdf"):
        app.generate_docs(output_format="pdf")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported output format: rst"):
        app.generate_docs(output_format="rst")  # type: ignore[arg-type]


def test_generate_docs_with_heading_levels():
    """Test custom heading levels."""
    app = App(name="myapp", help="Main app")

    @app.command
    def cmd():
        """A command."""
        pass

    actual = app.generate_docs(heading_level=2)

    # Check the heading levels
    assert "## myapp" in actual
    assert "Main app" in actual
    assert "### Usage" in actual
    assert "### Commands" in actual
    assert "### Command: cmd" in actual
    assert "#### Usage" in actual


def test_generate_docs_complex_nested_app():
    """Test complex nested application documentation."""
    app = App(name="cli", help="Complex CLI tool")

    # Add top-level command
    @app.command
    def version():
        """Show version information."""
        pass

    # Create nested subapp
    git = App(name="git", help="Git operations")

    @git.command
    def clone(
        url: Annotated[str, Parameter(help="Repository URL")],
        depth: int = 1,
    ):
        """Clone a repository.

        Parameters
        ----------
        url : str
            The repository URL to clone.
        depth : int
            Clone depth.
        """
        pass

    @git.command
    def push(force: bool = False):
        """Push changes.

        Parameters
        ----------
        force : bool
            Force push.
        """
        pass

    app.command(git)

    docs = app.generate_docs(recursive=True)

    # Check structure
    assert "# cli" in docs
    assert "Complex CLI tool" in docs
    assert "version" in docs
    assert "Show version information" in docs
    assert "## Command: git" in docs
    assert "Git operations" in docs
    assert "clone" in docs
    assert "push" in docs
    assert "Clone a repository" in docs
    assert "Push changes" in docs
    assert "Repository URL" in docs
    assert "Force push" in docs


def test_generate_docs_with_aliases():
    """Test documentation with command aliases."""
    app = App(name="myapp")

    @app.command(alias=["s", "srv"])
    def serve():
        """Start the server."""
        pass

    docs = app.generate_docs()

    assert "serve" in docs
    assert "Start the server" in docs
    # Note: Aliases might not be shown in current implementation
    # This is acceptable as the main command name is shown


def test_generate_docs_with_meta_app():
    """Test documentation generation with meta app."""
    from typing import Annotated, Optional

    app = App(name="myapp", help="Main application")

    @app.default
    def main(input_file: str):
        """Process a file.

        Parameters
        ----------
        input_file : str
            Input file path.
        """
        pass

    @app.meta.default
    def meta(
        verbose: bool = False,
        config: Annotated[Optional[str], Parameter(help="Config file")] = None,
    ):
        """Meta app for global options.

        Parameters
        ----------
        verbose : bool
            Enable verbose output.
        config : str
            Configuration file path.
        """
        pass

    actual = app.generate_docs()

    expected = dedent(
        """\
        # myapp

        Main application

        ## Usage

        ```
        Usage: myapp [ARGS] [OPTIONS]
        ```

        ## Parameters

        | Required | Parameter | Description |
        | :------: | --------- | ----------- |
        | ✓ | `INPUT-FILE`, `--input-file` | Input file path.<br><br>Type: `<class 'str'>` |
        |  | `VERBOSE`, `--verbose`, `--no-verbose` | Enable verbose output.<br><br>Type: `<class 'bool'>`<br>Default: `False` |
        |  | `CONFIG`, `--config` | Config file<br><br>Type: `typing.Optional[str]` |
        """
    )

    assert actual == expected


def test_generate_docs_meta_app_with_commands():
    """Test documentation with meta app and subcommands."""
    app = App(name="myapp", help="Main app with meta")

    @app.meta.default
    def meta(
        debug: bool = False,
    ):
        """Global meta options.

        Parameters
        ----------
        debug : bool
            Enable debug mode.
        """
        pass

    @app.command
    def serve(port: int = 8000):
        """Start the server.

        Parameters
        ----------
        port : int
            Port number.
        """
        pass

    @app.command
    def build():
        """Build the project."""
        pass

    actual = app.generate_docs()

    # Meta parameters should appear with the main app
    assert "debug" in actual.lower() or "DEBUG" in actual
    assert "Enable debug mode" in actual

    # Commands should still appear
    assert "serve" in actual
    assert "build" in actual
    assert "Start the server" in actual
    assert "Build the project" in actual


def test_generate_docs_nested_meta_apps():
    """Test documentation with nested apps that have their own meta apps."""
    # Create a subapp with its own meta
    db_app = App(name="db", help="Database commands")

    @db_app.meta.default
    def db_meta(
        connection: str = "sqlite:///:memory:",
    ):
        """Database meta options.

        Parameters
        ----------
        connection : str
            Database connection string.
        """
        pass

    @db_app.command
    def migrate():
        """Run database migrations."""
        pass

    # Main app with its own meta
    app = App(name="myapp", help="Main application")

    @app.meta.default
    def main_meta(
        verbose: bool = False,
    ):
        """Global options.

        Parameters
        ----------
        verbose : bool
            Verbose output.
        """
        pass

    # Register the db app with its meta
    app.command(db_app.meta, name="db")

    docs = app.generate_docs(recursive=True)

    # Check main app meta parameters appear
    assert "verbose" in docs.lower() or "VERBOSE" in docs
    assert "Verbose output" in docs

    # Check db subcommand appears
    assert "## Command: db" in docs
    # When registering db_app.meta, it uses the meta's docstring
    assert "Database meta options" in docs

    # Check nested db commands appear when recursive
    assert "migrate" in docs
    assert "Run database migrations" in docs

    # Check db meta parameters appear with db command
    assert "connection" in docs.lower() or "CONNECTION" in docs
    assert "Database connection string" in docs
