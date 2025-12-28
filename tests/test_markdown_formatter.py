"""Tests for the MarkdownFormatter."""

from textwrap import dedent

from cyclopts.help import HelpEntry, HelpPanel, MarkdownFormatter


def test_markdown_formatter_empty_panel():
    """Test that empty panels produce no output."""
    formatter = MarkdownFormatter()
    panel = HelpPanel(format="command", title="Commands")

    formatter(None, None, panel)
    output = formatter.get_output()

    assert output == ""


def test_markdown_formatter_command_panel_table():
    """Test command panel formatting (always uses list style now)."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(positive_names=("serve",), description="Start the server"),
            HelpEntry(positive_names=("build",), positive_shorts=("-b",), description="Build the project"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        * `serve`: Start the server
        * `build (-b)`: Build the project

        """)

    assert output == expected


def test_markdown_formatter_command_panel_list():
    """Test command panel formatting as a list."""
    formatter = MarkdownFormatter(table_style="list")
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(positive_names=("serve",), description="Start the server"),
            HelpEntry(positive_names=("build",), positive_shorts=("-b",), description="Build the project"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        * `serve`: Start the server
        * `build (-b)`: Build the project

        """)

    assert output == expected


def test_markdown_formatter_parameter_panel_table():
    """Test parameter panel formatting as a table."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                positive_names=("--port",),
                positive_shorts=("-p",),
                description="Port number",
                required=True,
                type="int",
                default="8080",
            ),
            HelpEntry(
                positive_names=("--verbose",),
                positive_shorts=("-v",),
                description="Enable verbose mode",
                required=False,
                choices=("true", "false"),
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Parameters

        * `--port, -p`: Port number  **[required]**  *[default: 8080]*
        * `--verbose, -v`: Enable verbose mode  *[choices: true, false]*

        """)

    assert output == expected


def test_markdown_formatter_parameter_panel_list():
    """Test parameter panel formatting as a list."""
    formatter = MarkdownFormatter(table_style="list")
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                positive_names=("--port",),
                positive_shorts=("-p",),
                description="Port number",
                required=True,
                type="int",
                default="8080",
            ),
            HelpEntry(
                positive_names=("--verbose",),
                description="Enable verbose mode",
                env_var=("VERBOSE",),
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Parameters

        * `--port, -p`: Port number  **[required]**  *[default: 8080]*
        * `--verbose`: Enable verbose mode  *[env: VERBOSE]*

        """)

    assert output == expected


def test_markdown_formatter_heading_level():
    """Test custom heading levels."""
    formatter = MarkdownFormatter(heading_level=3)
    panel = HelpPanel(
        format="command", title="Commands", entries=[HelpEntry(positive_names=("test",), description="Test command")]
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ### Commands

        * `test`: Test command

        """)

    assert output == expected


def test_markdown_formatter_with_panel_description():
    """Test panel with description."""
    formatter = MarkdownFormatter()
    panel = HelpPanel(
        format="command",
        title="Commands",
        description="Available commands for the application",
        entries=[HelpEntry(positive_names=("test",), description="Test command")],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        Available commands for the application

        * `test`: Test command

        """)

    assert output == expected


def test_markdown_formatter_render_usage():
    """Test usage rendering."""
    formatter = MarkdownFormatter()
    usage = "myapp [OPTIONS] COMMAND"

    formatter.render_usage(None, None, usage)
    output = formatter.get_output()

    expected = dedent("""\
        ```
        Usage: myapp [OPTIONS] COMMAND
        ```

        """)

    assert output == expected


def test_markdown_formatter_render_description():
    """Test description rendering."""
    formatter = MarkdownFormatter()
    description = "This is a CLI application for doing awesome things."

    formatter.render_description(None, None, description)
    output = formatter.get_output()

    expected = dedent("""\
        This is a CLI application for doing awesome things.

        """)

    assert output == expected


def test_markdown_formatter_reset():
    """Test that reset clears the output buffer."""
    formatter = MarkdownFormatter()

    # Add some content
    formatter.render_description(None, None, "Test description")
    assert formatter.get_output() != ""

    # Reset and check it's empty
    formatter.reset()
    assert formatter.get_output() == ""


def test_markdown_escape_special_characters():
    """Test that special markdown characters are properly escaped."""
    from cyclopts._markup import escape_markdown

    # Should escape pipe for table compatibility
    assert escape_markdown("foo | bar") == "foo \\| bar"

    # Should not escape if it looks like markdown already
    assert escape_markdown("**bold**") == "**bold**"
    assert escape_markdown("`code`") == "`code`"
    assert escape_markdown("[link](url)") == "[link](url)"

    # Should handle empty/None
    assert escape_markdown("") == ""
    assert escape_markdown(None) is None


def test_extract_text():
    """Test text extraction from various objects."""
    from cyclopts._markup import extract_text

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
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                positive_names=("--config",),
                positive_shorts=("-c",),
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

    expected = dedent("""\
        ## Parameters

        * `--config, -c`: Configuration file path  **[required]**  *[choices: /etc/app.conf, ~/.app.conf, ./app.conf]*  *[env: APP_CONFIG, CONFIG_PATH]*  *[default: /etc/app.conf]*

        """)

    assert output == expected


def test_parameter_table_no_required_column():
    """Test parameter table when no parameters are required."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="parameter",
        title="Options",
        entries=[
            HelpEntry(
                positive_names=("--debug",),
                description="Enable debug mode",
                type="bool",
                default="False",
            ),
            HelpEntry(
                positive_names=("--quiet",),
                positive_shorts=("-q",),
                description="Suppress output",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Options

        * `--debug`: Enable debug mode  *[default: False]*
        * `--quiet, -q`: Suppress output

        """)

    assert output == expected


def test_parameter_with_no_description():
    """Test parameters with no description."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(
                positive_names=("--flag",),
                type="bool",
                default="True",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Parameters

        * `--flag`:   *[default: True]*

        """)

    assert output == expected


def test_command_table_empty_description():
    """Test command table with entry having no description."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(positive_names=("test",)),  # No description
            HelpEntry(positive_names=("run",), description="Run the application"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        * `test`:
        * `run`: Run the application

        """)

    assert output == expected


def test_command_list_with_shorts_and_aliases():
    """Test command list with short options and aliases in parentheses."""
    formatter = MarkdownFormatter(table_style="list")
    panel = HelpPanel(
        format="command",
        title="Available Commands",
        entries=[
            HelpEntry(
                positive_names=("serve", "server"),
                positive_shorts=("s",),
                description="Start the development server",
            ),
            HelpEntry(
                positive_names=("test",),
                positive_shorts=("t", "T"),
                description="Run tests",
            ),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Available Commands

        * `serve (server, s)`: Start the development server
        * `test (t, T)`: Run tests

        """)

    assert output == expected


def test_multiple_panels_accumulate():
    """Test that multiple panels accumulate in the formatter."""
    formatter = MarkdownFormatter()

    # First panel
    panel1 = HelpPanel(
        format="command", title="Commands", entries=[HelpEntry(positive_names=("help",), description="Show help")]
    )

    # Second panel
    panel2 = HelpPanel(
        format="parameter",
        title="Global Options",
        entries=[
            HelpEntry(positive_names=("--verbose",), description="Verbose output", type="bool"),
        ],
    )

    formatter(None, None, panel1)
    formatter(None, None, panel2)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        * `help`: Show help

        ## Global Options

        * `--verbose`: Verbose output

        """)

    assert output == expected


def test_escape_markdown_in_descriptions():
    """Test that pipe characters are escaped in table cells."""
    formatter = MarkdownFormatter(table_style="table")
    panel = HelpPanel(
        format="command",
        title="Commands",
        entries=[
            HelpEntry(positive_names=("pipe",), description="Use | to separate values"),
        ],
    )

    formatter(None, None, panel)
    output = formatter.get_output()

    expected = dedent("""\
        ## Commands

        * `pipe`: Use | to separate values

        """)

    assert output == expected
