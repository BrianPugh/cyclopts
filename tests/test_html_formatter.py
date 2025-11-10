"""Tests for the HtmlFormatter."""

from textwrap import dedent

from cyclopts._markup import escape_html, extract_text
from cyclopts.help import HelpEntry, HelpPanel
from cyclopts.help.formatters.html import HtmlFormatter


def test_html_formatter_empty_panel():
    """Test that empty panels produce no output."""
    formatter = HtmlFormatter()
    panel = HelpPanel(format="command", title="Commands")

    formatter(None, None, panel)
    output = formatter.get_output()

    assert output == ""


def test_html_formatter_command_panel():
    """Test command panel formatting as HTML table."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(names=("serve",), description="Start the server"),
            HelpEntry(names=("build",), shorts=("-b",), description="Build the project"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Check structure
    assert '<section class="help-panel">' in output
    assert "Commands" in output
    # Check structure contains list
    assert "<ul" in output
    assert "<code>serve</code>" in output
    assert "<code>build</code>" in output
    assert "<code>-b</code>" in output
    assert "Start the server" in output
    assert "Build the project" in output


def test_html_formatter_parameter_panel():
    """Test parameter panel formatting as HTML table."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                names=("--port",),
                shorts=("-p",),
                description="Port number",
                required=True,
                type="int",
                default="8080",
            ),
            HelpEntry(
                names=("--verbose",),
                shorts=("-v",),
                description="Enable verbose mode",
                required=False,
                choices=("true", "false"),
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Check structure
    assert '<section class="help-panel">' in output
    assert "Parameters" in output
    # Check structure contains list
    assert "<ul" in output

    # Check required marker
    assert '<span class="metadata-item metadata-required">Required</span>' in output

    # Check parameter details
    assert "<code>--port</code>" in output
    assert "<code>-p</code>" in output
    assert "Port number" in output
    assert "<code>8080</code>" in output

    assert "<code>--verbose</code>" in output
    assert "Enable verbose mode" in output


def test_html_formatter_heading_level():
    """Test custom heading levels."""
    formatter = HtmlFormatter(heading_level=3)
    panel = HelpPanel(
        format="command", title="Commands", entries=[HelpEntry(names=("test",), description="Test command")]
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    assert "Commands" in output
    assert "<code>test</code>" in output
    assert "Test command" in output


def test_html_formatter_with_panel_description():
    """Test panel with description."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="command",
        title="Commands",
        description="Available commands for the application",
        entries=[HelpEntry(names=("test",), description="Test command")],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    assert '<div class="panel-description">Available commands for the application</div>' in output


def test_html_formatter_render_usage():
    """Test usage rendering."""
    formatter = HtmlFormatter()
    usage = "myapp [OPTIONS] COMMAND"

    formatter.render_usage(None, None, usage)
    output = formatter.get_output()

    expected = dedent("""\
        <div class="usage-block">
        <pre class="usage">Usage: myapp [OPTIONS] COMMAND</pre>
        </div>
        """)

    assert output == expected


def test_html_formatter_render_description():
    """Test description rendering."""
    formatter = HtmlFormatter()
    description = "This is a CLI application for doing awesome things."

    formatter.render_description(None, None, description)
    output = formatter.get_output()

    expected = '<div class="description">This is a CLI application for doing awesome things.</div>\n'

    assert output == expected


def test_html_formatter_reset():
    """Test that reset clears the output buffer."""
    formatter = HtmlFormatter()

    # Add some content
    formatter.render_description(None, None, "Test description")
    assert formatter.get_output() != ""

    # Reset and check it's empty
    formatter.reset()
    assert formatter.get_output() == ""


def testescape_html():
    """Test HTML escaping function."""
    # Basic escaping
    assert escape_html("<script>alert('XSS')</script>") == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    assert escape_html("foo & bar") == "foo &amp; bar"
    assert escape_html('"quoted"') == "&quot;quoted&quot;"

    # Handle None
    assert escape_html(None) == ""
    assert escape_html("") == ""


def test_extract_text():
    """Test text extraction from various objects."""
    # Test None
    assert extract_text(None) == ""

    # Test string
    assert extract_text("hello world") == "hello world"

    # Test object with __str__
    class TestObj:
        def __str__(self):
            return "test object"

    assert extract_text(TestObj()) == "test object"


def test_parameter_table_with_all_metadata():
    """Test parameter table with all possible metadata fields."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                names=("--config",),
                shorts=("-c",),
                description="Configuration file path",
                required=True,
                type="Path",
                choices=("/etc/app.conf", "~/.app.conf", "./app.conf"),
                env_var=("APP_CONFIG", "CONFIG_PATH"),
                default="/etc/app.conf",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Check all metadata is present
    assert "Configuration file path" in output
    assert "<code>/etc/app.conf</code>" in output
    assert "<code>~/.app.conf</code>" in output
    assert "<code>./app.conf</code>" in output
    assert "<code>APP_CONFIG</code>" in output
    assert "<code>CONFIG_PATH</code>" in output


def test_parameter_table_no_required_column():
    """Test parameter table when no parameters are required."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="parameter",
        title="Options",
        entries=[
            HelpEntry(
                names=("--debug",),
                description="Enable debug mode",
                type="bool",
                default="False",
            ),
            HelpEntry(
                names=("--quiet",),
                shorts=("-q",),
                description="Suppress output",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Should be using list format now
    # Check structure contains list
    assert "<ul" in output
    assert "<code>--debug</code>" in output
    assert "<code>--quiet</code>" in output


def test_command_with_no_description():
    """Test command entry with no description."""
    formatter = HtmlFormatter()
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(names=("test",)),  # No description
            HelpEntry(names=("run",), description="Run the application"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Both commands should be in table
    assert "<code>test</code>" in output
    assert "<code>run</code>" in output
    assert "Run the application" in output


def test_multiple_panels_accumulate():
    """Test that multiple panels accumulate in the formatter."""
    formatter = HtmlFormatter()

    # First panel
    panel1 = HelpPanel(
        format="command", title="Commands", entries=[HelpEntry(names=("help",), description="Show help")]
    )

    # Second panel
    panel2 = HelpPanel(
        format="parameter",
        title="Global Options",
        entries=[
            HelpEntry(names=("--verbose",), description="Verbose output", type="bool"),
        ],
    )

    formatter(None, None, panel1)
    formatter(None, None, panel2)
    output = formatter.get_output()

    # Both panels should be in output
    assert "Commands" in output
    assert "Global Options" in output
    assert "<code>help</code>" in output
    assert "<code>--verbose</code>" in output


def test_html_injection_prevention():
    """Test that user input is properly escaped to prevent HTML injection."""
    formatter = HtmlFormatter()

    # Try to inject HTML through description
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(
                names=("<script>alert('XSS')</script>",),
                description="<b>Bold</b> and <i>italic</i> text",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    # Check that HTML is escaped
    assert "&lt;script&gt;" in output
    assert "&lt;b&gt;" in output
    assert "&lt;i&gt;" in output
    # Should not contain raw HTML
    assert "<script>" not in output
    assert "<b>Bold</b>" not in output
