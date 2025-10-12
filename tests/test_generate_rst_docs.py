"""Tests for RST documentation generation."""

from typing import Literal

from cyclopts import App


def test_generate_rst_docs_simple_app():
    """Test basic RST documentation generation for a simple app."""
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

    docs = app.generate_docs(output_format="rst")

    assert "=====\nmyapp\n=====" in docs  # Level 1 heading with matching markers
    assert "myapp" in docs
    assert "A simple CLI application" in docs

    assert "Usage:" in docs
    assert "::" in docs  # Literal block marker
    assert "myapp" in docs

    assert "``NAME, --name``" in docs or "name, --name" in docs.lower()
    assert "Your name" in docs
    assert "``VERBOSE, --verbose" in docs or "verbose, --verbose" in docs.lower()
    assert "Enable verbose output" in docs


def test_generate_rst_docs_with_commands():
    """Test RST documentation generation with subcommands."""
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

    docs = app.generate_docs(output_format="rst")

    # Check main structure - heading markers match title length
    assert "=====\nmyapp\n=====" in docs  # Level 1 heading
    assert "myapp" in docs
    assert "CLI with commands" in docs

    # Check commands are documented as sections (not in a list)
    assert "myapp serve" in docs
    assert "myapp build" in docs
    assert "Start the server" in docs
    assert "Build the project" in docs


def test_generate_rst_docs_recursive():
    """Test recursive RST documentation generation."""
    app = App(name="myapp", help="Main app")

    sub = App(name="db", help="Database operations")

    @sub.command
    def migrate(dry_run: bool = False):
        """Run database migrations.

        Parameters
        ----------
        dry_run : bool
            Simulate migrations without applying.
        """
        pass

    app.command(sub)

    docs = app.generate_docs(output_format="rst", recursive=True)

    # Check main app - heading markers match title length
    assert "=====\nmyapp\n=====" in docs
    assert "myapp" in docs

    # Check subcommand is documented as a section
    assert "myapp db" in docs
    assert "Database operations" in docs

    # Check nested command
    assert "migrate" in docs
    assert "Run database migrations" in docs


def test_generate_rst_docs_with_options():
    """Test RST documentation with various parameter types."""
    app = App(name="myapp", help="App with options")

    @app.default
    def main(
        name: str,
        count: int = 1,
        verbose: bool = False,
        output: str | None = None,
        choice: Literal["a", "b", "c"] = "a",
    ):
        """Main command with various options.

        Parameters
        ----------
        name : str
            User name.
        count : int
            Number of iterations.
        verbose : bool
            Enable verbose mode.
        output : Optional[str]
            Output file path.
        choice : str
            Selection choice.
        """
        pass

    docs = app.generate_docs(output_format="rst")

    # Check parameters
    assert "User name" in docs
    assert "Number of iterations" in docs
    assert "Enable verbose mode" in docs
    assert "Output file path" in docs
    assert "Selection choice" in docs

    # Check defaults and choices
    assert "Default:" in docs
    assert "Choices:" in docs or "choices:" in docs.lower()


def test_generate_rst_docs_heading_levels():
    """Test RST documentation with different heading levels."""
    app = App(name="myapp", help="Test app")

    @app.command
    def cmd():
        """A command."""
        pass

    # Test with different heading levels
    docs1 = app.generate_docs(output_format="rst", heading_level=1)
    assert "=====\nmyapp\n=====" in docs1  # Level 1 uses = (matching title length)

    docs2 = app.generate_docs(output_format="rst", heading_level=2)
    assert "myapp\n-----" in docs2  # Level 2 uses - (no overline)
    assert "=====" not in docs2  # Should not have level 1 markers

    docs3 = app.generate_docs(output_format="rst", heading_level=3)
    assert "myapp\n^^^^^" in docs3  # Level 3 uses ^


def test_generate_rst_docs_hidden_commands():
    """Test RST documentation with hidden commands."""
    app = App(name="myapp", help="App with hidden commands")

    @app.command
    def visible():
        """Visible command."""
        pass

    @app.command(show=False)
    def hidden():
        """Hidden command."""
        pass

    # Without include_hidden
    docs = app.generate_docs(output_format="rst", include_hidden=False)
    assert "visible" in docs
    # Check that the hidden command is not documented (not in Commands section)
    assert "myapp hidden" not in docs  # Hidden command should not appear as a section

    # With include_hidden
    docs_with_hidden = app.generate_docs(output_format="rst", include_hidden=True)
    assert "visible" in docs_with_hidden
    assert "myapp hidden" in docs_with_hidden  # Hidden command appears as subcommand section
    assert "Hidden command." in docs_with_hidden  # And its docstring is included


def test_generate_rst_docs_special_characters():
    """Test RST documentation handles special characters properly."""
    app = App(name="my-app", help="App with special chars & symbols")

    @app.command
    def test_cmd(value: str = "default\\value"):
        """Command with backslash in default.

        Parameters
        ----------
        value : str
            Value with special chars.
        """
        pass

    docs = app.generate_docs(output_format="rst")

    # Should handle special characters
    assert "my-app" in docs
    assert "special chars" in docs
    # Backslashes should be escaped in RST
    assert "default\\\\value" in docs or "default\\value" in docs


def test_generate_rst_docs_flatten_commands():
    """Test flatten_commands option for RST documentation."""
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
    docs_hierarchical = app.generate_docs(output_format="rst", flatten_commands=False)

    # Main app should be level 1 (=====)
    assert "=====\nmyapp\n=====" in docs_hierarchical
    # Subcommands should be level 2 (-----)
    # Note: RST implementation uses short titles (not full command path)
    assert "sub1\n----" in docs_hierarchical
    assert "sub2\n----" in docs_hierarchical
    # Nested commands should be level 3 (^^^^^)
    assert "sub1 nested1\n^^^^^^^^^^^^" in docs_hierarchical
    assert "sub1 nested2\n^^^^^^^^^^^^" in docs_hierarchical
    assert "sub2 nested3\n^^^^^^^^^^^^" in docs_hierarchical

    # With flatten_commands - all at same level
    docs_flat = app.generate_docs(output_format="rst", flatten_commands=True)

    # Main app should be level 1 (=====)
    assert "=====\nmyapp\n=====" in docs_flat
    # All subcommands should also be level 1 (=====)
    # Note: RST implementation uses short titles (not full command path)
    assert "====\nsub1\n====" in docs_flat
    assert "====\nsub2\n====" in docs_flat
    # All nested commands should also be level 1 (=====)
    assert "============\nsub1 nested1\n============" in docs_flat
    assert "============\nsub1 nested2\n============" in docs_flat
    assert "============\nsub2 nested3\n============" in docs_flat
    # Should NOT have level 2 or level 3 markers for commands
    # (Level 2 uses single underline, level 3 uses ^^^^)
    # Check that subcommands don't use level 2 markers (----)
    assert "sub1\n----" not in docs_flat
    assert "sub2\n----" not in docs_flat
    # Check that nested commands don't use level 3 markers (^^^^)
    assert "sub1 nested1\n^^^^^^^^^^^^" not in docs_flat


def test_generate_rst_docs_usage_strings_match_help():
    """Test that RST usage strings match the actual help output."""
    app = App(name="myapp", help="Main CLI application")

    @app.command
    def serve(host: str = "localhost", port: int = 8000):
        """Start the development server.

        Parameters
        ----------
        host : str
            Host to bind to.
        port : int
            Port to listen on.
        """
        pass

    @app.command
    def build(output: str, verbose: bool = False):
        """Build the project.

        Parameters
        ----------
        output : str
            Output directory.
        verbose : bool
            Enable verbose output.
        """
        pass

    # Generate RST docs
    docs = app.generate_docs(output_format="rst", recursive=True)

    # Verify usage strings are present and correctly formatted
    # The serve command should show: myapp serve [ARGS]
    assert "Usage: myapp serve [ARGS]" in docs

    # The build command should show: myapp build OUTPUT [ARGS]
    # with OUTPUT as a required argument shown explicitly
    assert "Usage: myapp build OUTPUT [ARGS]" in docs

    # The key thing we're testing is that the usage strings match the actual
    # help output format, not the old manually-constructed generic patterns
    # like "myapp serve [ARGS] [OPTIONS]" that were created in the old code

    # Verify that required arguments are shown explicitly by name
    lines = docs.split("\n")
    usage_lines = [line.strip() for line in lines if "Usage:" in line]

    # For the build command with required OUTPUT parameter
    build_usage = [line for line in usage_lines if "myapp build" in line]
    assert len(build_usage) > 0, "Should have usage line for build command"
    # Should show OUTPUT explicitly, not hide it in generic [ARGS]
    assert "OUTPUT" in build_usage[0]


def test_generate_rst_docs_usage_with_positional_args():
    """Test RST usage strings correctly show positional arguments."""
    app = App(name="tool", help="A tool")

    @app.command
    def process(input_file: str, output_file: str, verbose: bool = False):
        """Process files.

        Parameters
        ----------
        input_file : str
            Input file path.
        output_file : str
            Output file path.
        verbose : bool
            Verbose mode.
        """
        pass

    docs = app.generate_docs(output_format="rst")

    # Should show the actual parameter names in usage
    assert "Usage: tool process" in docs
    # Should have INPUT-FILE and OUTPUT-FILE explicitly listed
    # The key point is that required positional args are shown by name
    assert "INPUT-FILE OUTPUT-FILE" in docs or "INPUT_FILE OUTPUT_FILE" in docs


def test_generate_rst_docs_usage_with_varargs():
    """Test RST usage strings correctly show variable arguments."""
    app = App(name="cmd", help="Command")

    @app.command
    def run(script: str, *args: str):
        """Run a script with arguments.

        Parameters
        ----------
        script : str
            Script to run.
        args : str
            Additional arguments.
        """
        pass

    docs = app.generate_docs(output_format="rst")

    # Should show SCRIPT and [ARGS...] or similar
    assert "Usage: cmd run" in docs
    assert "SCRIPT" in docs
    # Variable args are typically shown as [ARGS...] or ARGS...
    assert "[ARGS" in docs or "ARGS" in docs
