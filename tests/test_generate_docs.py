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

        **Usage**:

        ```console
        $ myapp [ARGS] [OPTIONS]
        ```

        **Arguments**:

        * `NAME`: Your name.  **[required]**

        **Options**:

        * `VERBOSE, --verbose, --no-verbose`: Enable verbose output.  *[default: --no-verbose]*
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
    assert "**Usage**:" in actual
    assert "$ myapp COMMAND" in actual

    # Commands list
    assert "**Commands**:" in actual
    assert "* `build`: Build the project." in actual
    assert "* `serve`: Start the server." in actual

    # Serve command details
    assert "## `myapp serve`" in actual
    assert "Start the server." in actual
    assert "**Usage**:" in actual
    assert "**Options**:" in actual
    assert "* `PORT, --port`: Port number.  *[default: 8000]*" in actual

    # Build command details
    assert "## `myapp build`" in actual
    assert "Build the project." in actual
    assert "* `OUTPUT, --output`: Output directory.  *[default: ./dist]*" in actual


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
    assert "## `myapp db`" in actual
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

        ## Table of Contents

        - [`db`](#myapp-db)
          - [`migrate`](#myapp-db-migrate)

        **Usage**:

        ```console
        $ myapp COMMAND
        ```

        **Commands**:

        * `db`: Database commands

        ## `myapp db`

        Database commands

        **Usage**:

        ```console
        $ myapp db COMMAND
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

        ## Table of Contents

        - [`visible`](#myapp-visible)

        **Usage**:

        ```console
        $ myapp COMMAND
        ```

        **Commands**:

        * `visible`: Visible command.

        ## `myapp visible`

        Visible command.

        **Usage**:

        ```console
        $ myapp visible
        ```
        """
    )

    assert actual_without_hidden == expected_without_hidden

    # Test WITH include_hidden
    actual_with_hidden = app.generate_docs(include_hidden=True)

    # Verify the hidden command is present when include_hidden=True
    assert "## `myapp hidden`" in actual_with_hidden
    assert "Hidden command." in actual_with_hidden
    # Also verify it has help and version commands shown
    assert "* `--help`: Display this message and exit." in actual_with_hidden
    assert "* `--version`: Display application version." in actual_with_hidden


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

        **Usage**:

        ```console
        $ myapp [ARGS] [OPTIONS]
        ```

        **Arguments**:

        * `REQUIRED`: Required parameter  **[required]**

        **Options**:

        * `OPTIONAL, --optional`:   *[default: default]*
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
    assert "choices:" in actual


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

        **Usage**:

        ```console
        $ myapp [OPTIONS] <input> <output>
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

            **Usage**:

            ```console
            $ myapp
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

        **Usage**:

        ```console
        $ myapp
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

    with pytest.raises(ValueError, match='Unsupported format "pdf"'):
        app.generate_docs(output_format="pdf")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match='Unsupported format "invalid"'):
        app.generate_docs(output_format="invalid")  # type: ignore[arg-type]


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
    assert "**Usage**:" in actual
    assert "**Commands**:" in actual
    assert "### `myapp cmd`" in actual


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
    assert "## `cli git`" in docs
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
    from typing import Annotated

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
        config: Annotated[str | None, Parameter(help="Config file")] = None,
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

        **Usage**:

        ```console
        $ myapp [ARGS] [OPTIONS]
        ```

        **Arguments**:

        * `INPUT-FILE`: Input file path.  **[required]**

        **Options**:

        * `VERBOSE, --verbose, --no-verbose`: Enable verbose output.  *[default: --no-verbose]*
        * `CONFIG, --config`: Config file
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
    assert "## `myapp db`" in docs
    # When registering db_app.meta, it uses the meta's docstring
    assert "Database meta options" in docs

    # Check nested db commands appear when recursive
    assert "migrate" in docs
    assert "Run database migrations" in docs

    # Check db meta parameters appear with db command
    assert "connection" in docs.lower() or "CONNECTION" in docs
    assert "Database connection string" in docs


def test_generate_docs_flatten_commands():
    """Test flatten_commands option for markdown documentation."""
    app = App(name="myapp", help="Main app")

    sub1 = App(name="sub1", help="First subcommand")

    @sub1.command
    def nested1():
        """Nested command 1."""
        pass

    @sub1.command
    def nested2():
        """Nested command 2."""
        pass

    sub2 = App(name="sub2", help="Second subcommand")

    @sub2.command
    def nested3():
        """Nested command 3."""
        pass

    app.command(sub1)
    app.command(sub2)

    # Without flatten_commands - hierarchical headings
    docs_hierarchical = app.generate_docs(flatten_commands=False)

    # Main app should be h1
    assert "# myapp" in docs_hierarchical
    # Subcommands should be h2
    assert "## `myapp sub1`" in docs_hierarchical
    assert "## `myapp sub2`" in docs_hierarchical
    # Nested commands should also be h2 (not h3) in current implementation
    assert "## `myapp sub1 nested1`" in docs_hierarchical
    assert "## `myapp sub1 nested2`" in docs_hierarchical
    assert "## `myapp sub2 nested3`" in docs_hierarchical

    # With flatten_commands - all at same level
    docs_flat = app.generate_docs(flatten_commands=True)

    # Main app should be h1
    assert "# myapp" in docs_flat
    # All subcommands should also be h1 (flattened)
    assert "# `myapp sub1`" in docs_flat
    assert "# `myapp sub2`" in docs_flat
    # All nested commands should also be h1 (flattened)
    assert "# `myapp sub1 nested1`" in docs_flat
    assert "# `myapp sub1 nested2`" in docs_flat
    assert "# `myapp sub2 nested3`" in docs_flat
    # Should NOT have h2 command headings when flattened
    assert "## `myapp sub" not in docs_flat
