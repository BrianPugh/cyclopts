"""Tests for HTML documentation generation."""

import tempfile
from pathlib import Path
from typing import Annotated, Optional

from cyclopts import App, Parameter


def test_generate_html_docs_simple_app():
    """Test basic HTML documentation generation for a simple app."""
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

    docs = app.generate_docs(output_format="html")

    # Check HTML structure
    assert "<!DOCTYPE html>" in docs
    assert "<html" in docs
    assert "<head>" in docs
    assert "<title>myapp - CLI Documentation</title>" in docs
    assert "<style>" in docs  # CSS should be embedded
    assert '<body id="top">' in docs

    # Check content is present
    assert "myapp" in docs
    assert "A simple CLI application" in docs
    assert "Usage" in docs

    # Check parameters are documented
    assert "Your name" in docs
    assert "Enable verbose output" in docs


def test_generate_html_docs_with_commands():
    """Test HTML documentation generation with subcommands."""
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

    docs = app.generate_docs(output_format="html")

    # Check main content
    assert "myapp" in docs
    assert "CLI with commands" in docs

    # Check commands are documented
    assert "serve" in docs
    assert "build" in docs
    assert "Start the server" in docs
    assert "Build the project" in docs
    assert "Port number" in docs
    assert "Output directory" in docs


def test_generate_html_docs_with_choices():
    """Test HTML documentation with parameter choices."""
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

    docs = app.generate_docs(output_format="html")

    # Should show available choices in HTML
    assert "choices:" in docs
    assert "<code>red</code>" in docs
    assert "<code>green</code>" in docs
    assert "<code>blue</code>" in docs


def test_generate_html_docs_write_to_file():
    """Test writing HTML documentation to a file."""
    app = App(name="myapp", help="Test app")

    @app.default
    def main():
        """Main command."""
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "docs" / "cli.html"

        # Generate HTML docs
        docs = app.generate_docs(output_format="html")

        # Write to file manually
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(docs)

        # Check file was created
        assert output_path.exists()
        content = output_path.read_text()

        # Should be complete HTML document
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert '<h1 class="app-title">myapp</h1>' in content

        # Content should match what we wrote
        assert docs == content


def test_generate_html_docs_format_explicit():
    """Test explicitly generating HTML format."""
    app = App(name="myapp", help="Test app")

    # Test explicitly specifying HTML format
    docs_html = app.generate_docs(output_format="html")
    assert "<!DOCTYPE html>" in docs_html
    assert "<html" in docs_html
    assert '<h1 class="app-title">myapp</h1>' in docs_html


def test_generate_html_docs_with_meta_app():
    """Test HTML documentation generation with meta app."""
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

    docs = app.generate_docs(output_format="html")

    # Check parameters are included
    assert "input" in docs.lower()
    assert "Input file path" in docs
    assert "verbose" in docs.lower()
    assert "Enable verbose output" in docs
    assert "config" in docs.lower()
    assert "Config file" in docs


def test_generate_html_docs_html_escaping():
    """Test that special characters are properly escaped in HTML."""
    app = App(name="myapp", help='Test <script> & "quotes"')

    @app.command
    def test():
        """Command with <b>HTML</b> & special chars."""
        pass

    docs = app.generate_docs(output_format="html")

    # Check that special characters are escaped
    assert "&lt;script&gt;" in docs
    assert "&amp;" in docs
    assert "&quot;quotes&quot;" in docs
    assert "&lt;b&gt;HTML&lt;/b&gt;" in docs

    # Should not contain unescaped HTML
    assert "<script>" not in docs
    assert "<b>HTML</b>" not in docs


def test_generate_html_docs_css_included():
    """Test that CSS styles are included in the HTML output."""
    app = App(name="myapp", help="Test app")

    docs = app.generate_docs(output_format="html")

    # Check that CSS is included
    assert "<style>" in docs
    assert "body {" in docs  # Basic CSS present

    # Check for responsive design
    assert "@media" in docs

    # Check for dark mode support
    assert "prefers-color-scheme: dark" in docs


def test_generate_html_docs_standalone_false():
    """Test generating non-standalone HTML (no <html> wrapper)."""
    from cyclopts.docs.html import generate_html_docs

    app = App(name="myapp", help="Test app")

    @app.default
    def main():
        """Main command."""
        pass

    # Generate non-standalone HTML
    docs = generate_html_docs(app, standalone=False)

    # Should not have HTML document wrapper
    assert "<!DOCTYPE html>" not in docs
    assert "<html" not in docs
    assert "<head>" not in docs
    assert "<body>" not in docs

    # Should still have content
    assert '<div class="cli-documentation">' in docs
    assert '<h1 class="app-title">myapp</h1>' in docs


def test_generate_html_docs_invalid_format():
    """Test that invalid output format raises ValueError."""
    import pytest

    app = App(name="myapp", help="Test app")

    with pytest.raises(ValueError, match='Unsupported format "pdf"'):
        app.generate_docs(output_format="pdf")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match='Unsupported format "latex"'):
        app.generate_docs(output_format="latex")  # type: ignore[arg-type]


def test_generate_html_docs_flatten_commands():
    """Test flatten_commands option for HTML documentation."""
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
    docs_hierarchical = app.generate_docs(output_format="html", flatten_commands=False)

    # Main app should be h1
    assert '<h1 class="app-title">myapp</h1>' in docs_hierarchical
    # Subcommands should be h2
    assert '<h2 id="myapp-sub1" class="command-title">' in docs_hierarchical
    assert '<h2 id="myapp-sub2" class="command-title">' in docs_hierarchical
    # Nested commands should be h3
    assert '<h3 id="myapp-sub1-nested1" class="command-title">' in docs_hierarchical
    assert '<h3 id="myapp-sub1-nested2" class="command-title">' in docs_hierarchical
    assert '<h3 id="myapp-sub2-nested3" class="command-title">' in docs_hierarchical

    # With flatten_commands - all at same level
    docs_flat = app.generate_docs(output_format="html", flatten_commands=True)

    # Main app should be h1
    assert '<h1 class="app-title">myapp</h1>' in docs_flat
    # Subcommands should be h1 (flattened)
    assert '<h1 id="myapp-sub1" class="command-title">' in docs_flat
    assert '<h1 id="myapp-sub2" class="command-title">' in docs_flat
    # Nested commands should also be h1 (flattened)
    assert '<h1 id="myapp-sub1-nested1" class="command-title">' in docs_flat
    assert '<h1 id="myapp-sub1-nested2" class="command-title">' in docs_flat
    assert '<h1 id="myapp-sub2-nested3" class="command-title">' in docs_flat
    # Should NOT have h2 or h3 command headings
    assert '<h2 id="myapp-sub' not in docs_flat
    assert '<h3 id="myapp-sub' not in docs_flat
