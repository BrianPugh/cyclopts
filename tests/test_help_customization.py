"""Test help customization via Group help_formatter."""

from textwrap import dedent
from typing import Annotated, Any

from rich.box import DOUBLE, SIMPLE, SQUARE
from rich.console import Console

from cyclopts import App, Group, Parameter
from cyclopts.annotations import get_hint_name
from cyclopts.help import ColumnSpec, DefaultFormatter, HelpEntry, PanelSpec, TableSpec
from cyclopts.help.specs import DescriptionColumn, DescriptionRenderer


def _type_renderer(entry: Any) -> str:
    """Render the type field as a human-readable string."""
    type_annotation = entry.type
    if type_annotation is None:
        return ""
    return get_hint_name(type_annotation)


def test_group_custom_table_spec(console: Console):
    """Test that custom table_spec on Group is used."""
    custom_group = Group(
        "Custom Options",
        help="These are custom options.",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_header=True,
                border_style="blue",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(group=custom_group)] = False,
        config: Annotated[str, Parameter(group=custom_group)] = "default.cfg",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
            Usage: test_help_customization [ARGS]

            ╭─ Commands ─────────────────────────────────────────────────────────╮
            │ --help -h  Display this message and exit.                          │
            │ --version  Display application version.                            │
            ╰────────────────────────────────────────────────────────────────────╯
            ╭─ Custom Options ───────────────────────────────────────────────────╮
            │ These are custom options.                                          │
            │                                                                    │
            │ Option             Description                                     │
            │ VERBOSE --verbose  [default: False]                                │
            │   --no-verbose                                                     │
            │ CONFIG --config    [default: default.cfg]                          │
            ╰────────────────────────────────────────────────────────────────────╯
            """
    )
    assert actual == expected


def test_group_custom_panel_spec(console: Console):
    """Test that custom panel_spec on Group is used."""
    custom_group = Group(
        "Styled Options",
        help_formatter=DefaultFormatter(
            panel_spec=PanelSpec(
                box=DOUBLE,
                border_style="cyan",
                padding=(1, 2),
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        flag: Annotated[bool, Parameter(group=custom_group)] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╔═ Styled Options ═══════════════════════════════════════════════════╗
        ║                                                                    ║
        ║  FLAG --flag --no-flag  [default: False]                           ║
        ║                                                                    ║
        ╚════════════════════════════════════════════════════════════════════╝
        """
    )
    assert actual == expected


def test_group_custom_columns(console: Console):
    """Test that custom columns can be specified via DefaultFormatter."""

    def names_renderer(entry):
        """Render names and shorts as a single string."""
        names_str = " ".join(entry.names) if entry.names else ""
        shorts_str = " ".join(entry.shorts) if entry.shorts else ""
        if names_str and shorts_str:
            return names_str + " " + shorts_str
        return names_str or shorts_str

    custom_columns = (
        ColumnSpec(renderer=names_renderer, style="green bold", header="Option"),
        ColumnSpec(renderer=_type_renderer, style="yellow", header="Type"),
        DescriptionColumn,
    )

    custom_group = Group(
        "Advanced Options",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(show_header=True),
        ),
    )

    app = App()

    @app.default
    def main(
        threads: Annotated[int, Parameter(group=custom_group, help="Number of threads")] = 4,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Advanced Options ─────────────────────────────────────────────────╮
        │ Option             Type  Description                               │
        │ THREADS --threads  int   Number of threads [default: 4]            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_default_group_with_custom_spec(app, console):
    """Test that default groups can be created and then customized with specs."""
    # Create a default parameters group and then set its specs
    custom_params_group = Group.create_default_parameters()
    custom_params_group = Group(
        custom_params_group.name,
        sort_key=custom_params_group.sort_key,
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_lines=True,
                box=SQUARE,  # Need a box style for lines to appear
            ),
            panel_spec=PanelSpec(
                box=DOUBLE,
            ),
        ),
    )

    app.group_parameters = custom_params_group

    @app.default
    def main(verbose: bool = False):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╔═ Parameters ═══════════════════════════════════════════════════════╗
        ║ ┌───────────────────┬────────────────────────────────────────────┐ ║
        ║ │VERBOSE --verbose  │[default: False]                            │ ║
        ║ │  --no-verbose     │                                            │ ║
        ║ └───────────────────┴────────────────────────────────────────────┘ ║
        ╚════════════════════════════════════════════════════════════════════╝
        """
    )
    assert actual == expected


def test_command_group_with_custom_spec(console: Console):
    """Test that command groups can have custom specs."""
    # Create a default commands group and then customize it
    custom_commands_group = Group(
        "Commands",
        sort_key=Group.create_default_commands().sort_key,
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                padding=(0, 1),
            ),
        ),
    )

    app = App(group_commands=custom_commands_group)

    @app.command
    def foo():
        """Foo command."""
        pass

    @app.command
    def bar():
        """Bar command."""
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization COMMAND

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ bar        Bar command.                                            │
        │ foo        Foo command.                                            │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_panel_spec_custom_title(console: Console):
    """Test that a custom title in panel_spec overrides the group name."""
    custom_group = Group(
        "Original Name",
        help_formatter=DefaultFormatter(
            panel_spec=PanelSpec(
                title="Custom Title",
                border_style="magenta",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        option: Annotated[str, Parameter(group=custom_group)] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Custom Title ─────────────────────────────────────────────────────╮
        │ OPTION --option  [default: default]                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_mixed_groups_with_different_specs(console: Console):
    """Test multiple groups each with their own custom specs."""
    required_group = Group(
        "Required",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                border_style="red",
            ),
        ),
    )

    optional_group = Group(
        "Optional",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                border_style="green",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        name: Annotated[str, Parameter(group=required_group)],
        verbose: Annotated[bool, Parameter(group=optional_group)] = False,
        debug: Annotated[bool, Parameter(group=optional_group)] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization NAME [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Optional ─────────────────────────────────────────────────────────╮
        │ VERBOSE --verbose         [default: False]                         │
        │   --no-verbose                                                     │
        │ DEBUG --debug --no-debug  [default: False]                         │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Required ─────────────────────────────────────────────────────────╮
        │ *  NAME --name  [required]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_show_lines_with_box(console: Console):
    """Test that lines appear between rows when both show_lines=True and box is set."""
    custom_group = Group(
        "Options",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_lines=True,
                box=SIMPLE,  # Need a box style for lines to appear
                border_style="green",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        first: Annotated[str, Parameter(group=custom_group)] = "one",
        second: Annotated[str, Parameter(group=custom_group)] = "two",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Options ──────────────────────────────────────────────────────────╮
        │                                                                    │
        │  FIRST --first     [default: one]                                  │
        │                                                                    │
        │  SECOND --second   [default: two]                                  │
        │                                                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_with_default_columns(console: Console):
    """Test that default columns now have headers that show when show_header=True."""
    custom_group = Group(
        "Config",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_header=True,  # Headers should now show with default columns
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        param: Annotated[str, Parameter(group=custom_group)] = "value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Config ───────────────────────────────────────────────────────────╮
        │ Option         Description                                         │
        │ PARAM --param  [default: value]                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_suppressed_when_all_empty(console: Console):
    """Test that headers are suppressed when all column headers are empty strings."""
    from cyclopts.help import DescriptionRenderer

    # Create columns with explicitly empty headers
    custom_columns = (
        ColumnSpec(renderer=lambda entry: " ".join(entry.names) if entry.names else "", header="", style="cyan"),
        ColumnSpec(renderer=DescriptionRenderer(), header=""),
    )

    custom_group = Group(
        "Settings",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(
                show_header=True,  # Even with this True, headers shouldn't show if all are empty
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        setting: Annotated[str, Parameter(group=custom_group, help="A configuration setting")] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Settings ─────────────────────────────────────────────────────────╮
        │ SETTING --setting  A configuration setting [default: default]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_with_non_empty_headers(console: Console):
    """Test that headers appear when column headers have text."""

    def names_renderer(entry):
        """Render names and shorts as a single string."""
        names_str = " ".join(entry.names) if entry.names else ""
        shorts_str = " ".join(entry.shorts) if entry.shorts else ""
        if names_str and shorts_str:
            return names_str + " " + shorts_str
        return names_str or shorts_str

    custom_columns = (
        ColumnSpec(renderer=names_renderer, header="Option", style="cyan"),
        DescriptionColumn,
    )

    custom_group = Group(
        "Settings",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(
                show_header=True,
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        setting: Annotated[str, Parameter(group=custom_group, help="A configuration setting")] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Settings ─────────────────────────────────────────────────────────╮
        │ Option             Description                                     │
        │ SETTING --setting  A configuration setting [default: default]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


class SimpleCustomFormatter:
    """A simple custom formatter that wraps content in ASCII borders."""

    def __call__(self, console, options, panel):
        from rich.markdown import Markdown
        from rich.text import Text

        # Create a simple ASCII border around the panel
        console.print("+" + "-" * 68 + "+")
        console.print(f"| {panel.title:^66} |")
        console.print("+" + "-" * 68 + "+")

        # Handle description - convert to plain text if needed
        if panel.description:
            desc_text = ""
            if hasattr(panel.description, "primary_renderable"):
                pr = panel.description.primary_renderable
                if isinstance(pr, Text):
                    desc_text = pr.plain
                elif isinstance(pr, Markdown):
                    desc_text = pr.markup
                else:
                    desc_text = str(pr)
            else:
                desc_text = str(panel.description)
            if desc_text:  # Only print if there's actual text
                console.print(f"| {desc_text:<66} |")

        for entry in panel.entries:
            names = " ".join(entry.names) if entry.names else ""
            shorts = " ".join(entry.shorts) if entry.shorts else ""
            name_part = f"{names} {shorts}".strip()

            # Handle entry description - convert to plain text if needed
            desc = ""
            if entry.description:
                if hasattr(entry.description, "primary_renderable"):
                    pr = entry.description.primary_renderable
                    if isinstance(pr, Text):
                        desc = pr.plain
                    elif isinstance(pr, Markdown):
                        desc = pr.markup
                    else:
                        desc = str(pr)
                else:
                    desc = str(entry.description)

            # Add default value if present
            if entry.default is not None:
                if desc:
                    desc += f" [default: {entry.default}]"
                else:
                    desc = f"[default: {entry.default}]"

            # Format line based on panel format
            if panel.format == "command":
                # Commands: align with padding for readability
                if desc:
                    # Pad the name part to a reasonable width for alignment
                    line = f"{name_part:<20} {desc}"
                else:
                    line = name_part
            else:
                # Parameters: similar padding for consistency
                if desc:
                    line = f"{name_part:<20} {desc}"
                else:
                    line = name_part

            # Use Text object to prevent wrapping
            text_line = Text(f"| {line:<66} |", no_wrap=True)
            console.print(text_line)
        console.print("+" + "-" * 68 + "+")


def test_custom_help_formatter_basic(console: Console):
    """Test that a custom HelpFormatter protocol implementation works."""
    custom_group = Group(
        "Custom Options",
        help="These are custom options.",
        help_formatter=SimpleCustomFormatter(),
    )

    app = App()

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(group=custom_group)] = False,
        config: Annotated[str, Parameter(group=custom_group)] = "default.cfg",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        +--------------------------------------------------------------------+
        |                           Custom Options                           |
        +--------------------------------------------------------------------+
        | These are custom options.                                          |
        | VERBOSE --verbose --no-verbose [default: False]                    |
        | CONFIG --config      [default: default.cfg]                        |
        +--------------------------------------------------------------------+
        """
    )
    assert actual == expected


def test_custom_help_formatter_with_optional_methods(console: Console):
    """Test custom formatter with optional render_usage and render_description methods."""

    class FullCustomFormatter:
        """Custom formatter with all optional methods."""

        def render_usage(self, console, options, usage):
            if usage:
                console.print("[CUSTOM USAGE] ", usage)

        def render_description(self, console, options, description):
            if description:
                console.print("[CUSTOM DESC]", description)

        def __call__(self, console, options, panel):
            from rich.markdown import Markdown
            from rich.text import Text

            console.print(f"=== {panel.title} ===")

            if panel.description:
                desc_text = ""
                if hasattr(panel.description, "primary_renderable"):
                    pr = panel.description.primary_renderable
                    if isinstance(pr, Text):
                        desc_text = pr.plain
                    elif isinstance(pr, Markdown):
                        desc_text = pr.markup
                    else:
                        desc_text = str(pr)
                else:
                    desc_text = str(panel.description)
                if desc_text:
                    console.print(f"    {desc_text}")

            for entry in panel.entries:
                names = " ".join(entry.names) if entry.names else ""
                shorts = " ".join(entry.shorts) if entry.shorts else ""
                if shorts:
                    names += " " + shorts

                # Handle entry description - convert to plain text if needed
                desc = ""
                if entry.description:
                    if hasattr(entry.description, "primary_renderable"):
                        pr = entry.description.primary_renderable
                        if isinstance(pr, Text):
                            desc = pr.plain
                        elif isinstance(pr, Markdown):
                            desc = pr.markup
                        else:
                            desc = str(pr)
                    else:
                        desc = str(entry.description)

                # Add default value if present
                if entry.default is not None:
                    if desc:
                        desc += " "
                    desc += f"[default: {entry.default}]"

                console.print(f"  * {names}: {desc}", markup=False)

    app = App(
        help="This is a test application.",
        help_formatter=FullCustomFormatter(),
    )

    custom_group = Group(
        "Options",
        help="Test options group.",
    )

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(group=custom_group)] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        [CUSTOM USAGE]  Usage: test_help_customization [ARGS]

        [CUSTOM DESC]
        This is a test application.

        === Commands ===
          * --help -h: Display this message and exit.
          * --version: Display application version.
        === Options ===
            Test options group.
          * VERBOSE --verbose --no-verbose: [default: False]
        """
    )
    assert actual == expected


def test_multiple_groups_different_formatters(console: Console):
    """Test multiple groups each using different formatter types."""
    from cyclopts.help.formatters import PlainFormatter

    # Custom formatter for first group
    class PrefixFormatter:
        def __call__(self, console, options, panel):
            from rich.markdown import Markdown
            from rich.text import Text

            console.print(f">> {panel.title}")
            for entry in panel.entries:
                names = " ".join(entry.names) if entry.names else ""

                # Handle entry description - convert to plain text if needed
                desc = ""
                if entry.description:
                    if hasattr(entry.description, "primary_renderable"):
                        pr = entry.description.primary_renderable
                        if isinstance(pr, Text):
                            desc = pr.plain
                        elif isinstance(pr, Markdown):
                            desc = pr.markup
                        else:
                            desc = str(pr)
                    else:
                        desc = str(entry.description)

                # Add default value if present
                if entry.default is not None:
                    if desc:
                        desc += f" [default: {entry.default}]"
                    else:
                        desc = f"[default: {entry.default}]"

                console.print(f"   -> {names}: {desc}", markup=False)

    custom_group = Group(
        "Custom Group",
        help_formatter=PrefixFormatter(),
    )

    plain_group = Group(
        "Plain Group",
        help_formatter=PlainFormatter(),
    )

    rich_group = Group(
        "Rich Group",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(border_style="green"),
        ),
    )

    app = App()

    @app.default
    def main(
        opt1: Annotated[str, Parameter(group=custom_group)] = "val1",
        opt2: Annotated[str, Parameter(group=plain_group)] = "val2",
        opt3: Annotated[str, Parameter(group=rich_group)] = "val3",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        >> Custom Group
           -> OPT1 --opt1: [default: val1]
        Plain Group:
          OPT2, --opt2: [default: val2]

        ╭─ Rich Group ───────────────────────────────────────────────────────╮
        │ OPT3 --opt3  [default: val3]                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_custom_formatter_protocol_validation(console: Console):
    """Test that any callable satisfying HelpFormatter protocol works."""

    # Simple function that satisfies the protocol
    def minimal_formatter(console, options, panel):
        console.print(f"[{panel.title}]")
        for entry in panel.entries:
            names = " ".join(entry.names) if entry.names else ""
            console.print(f"  {names}")

    custom_group = Group(
        "Minimal",
        help_formatter=minimal_formatter,
    )

    app = App()

    @app.default
    def main(
        option: Annotated[str, Parameter(group=custom_group)] = "test",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        [Minimal]
          OPTION --option
        """
    )
    assert actual == expected


def test_group_formatter_none_fallback(console: Console):
    """Test that groups with formatter=None fall back to app's formatter."""
    app = App(help_formatter=SimpleCustomFormatter())

    # Group with explicit None formatter (should use app.app_formatter -> SimpleCustomFormatter)
    default_group = Group("Fallback to App.help_formatter Group", help_formatter=None)

    # Group with its own formatter
    custom_group = Group("Explicitly DefaultFormatter Group", help_formatter="default")

    @app.default
    def main(
        opt1: Annotated[str, Parameter(group=default_group)] = "default1",
        opt2: Annotated[str, Parameter(group=custom_group)] = "custom1",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        +--------------------------------------------------------------------+
        |                              Commands                              |
        +--------------------------------------------------------------------+
        | --help -h            Display this message and exit.                |
        | --version            Display application version.                  |
        +--------------------------------------------------------------------+
        ╭─ Explicitly DefaultFormatter Group ────────────────────────────────╮
        │ OPT2 --opt2  [default: custom1]                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        +--------------------------------------------------------------------+
        |                Fallback to App.help_formatter Group                |
        +--------------------------------------------------------------------+
        | OPT1 --opt1          [default: default1]                           |
        +--------------------------------------------------------------------+
        """
    )
    assert actual == expected


def test_custom_formatter_receives_correct_arguments(console: Console):
    """Test that custom formatter receives correct console, options, and panel."""
    captured_args = {}

    class ValidatingFormatter:
        def __call__(self, console_arg, options_arg, panel_arg):
            # Capture arguments for validation
            captured_args["console"] = console_arg
            captured_args["options"] = options_arg
            captured_args["panel"] = panel_arg

            # Verify panel structure
            assert hasattr(panel_arg, "title")
            assert hasattr(panel_arg, "entries")
            assert hasattr(panel_arg, "description")

            # Render something to verify it works
            console_arg.print(f"Panel: {panel_arg.title}")
            assert len(panel_arg.entries) == 1
            entry = panel_arg.entries[0]
            assert "test" in " ".join(entry.names).lower() and "param" in " ".join(entry.names).lower()
            console_arg.print(f"  Entry: {' '.join(entry.names)}")

    custom_group = Group(
        "Validated Group",
        help="Group with validation.",
        help_formatter=ValidatingFormatter(),
    )

    app = App()

    @app.default
    def main(
        test_param: Annotated[str, Parameter(group=custom_group)] = "value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()

    # Verify captured arguments
    assert captured_args["console"] is console
    assert captured_args["options"] is not None
    assert captured_args["panel"].title == "Validated Group"

    # Check description - handle InlineText object
    from rich.markdown import Markdown
    from rich.text import Text

    panel_desc = captured_args["panel"].description
    if hasattr(panel_desc, "primary_renderable"):
        pr = panel_desc.primary_renderable
        if isinstance(pr, Text):
            desc_text = pr.plain
        elif isinstance(pr, Markdown):
            desc_text = pr.markup
        else:
            desc_text = str(pr)
    else:
        desc_text = str(panel_desc)
    assert desc_text == "Group with validation."

    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        Panel: Validated Group
          Entry: TEST-PARAM --test-param
        """
    )
    assert actual == expected


def test_plain_formatter_with_rich_text(console: Console):
    """Test PlainFormatter handling of Rich Text objects with .plain property."""
    from cyclopts.help.formatters import PlainFormatter

    # Create a group with PlainFormatter
    plain_group = Group(
        "Plain Options",
        help="Test group with rich text",
        help_formatter=PlainFormatter(),
    )

    app = App()

    @app.default
    def main(
        option: Annotated[str, Parameter(group=plain_group, help="Test option")] = "value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    # Commands group still uses default formatter, only Plain Options uses PlainFormatter
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        Plain Options:
          OPTION, --option: Test option [default: value]

        """
    )
    assert actual == expected


def test_plain_formatter_empty_panel(console: Console):
    """Test PlainFormatter skips empty panels."""
    from cyclopts.help import HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    formatter = PlainFormatter()

    # Create an empty panel
    empty_panel = HelpPanel(
        title="Empty Panel", description="This panel has no entries", entries=[], format="parameter"
    )

    # This should not output anything
    with console.capture() as capture:
        formatter(console, console.options, empty_panel)

    assert capture.get() == ""


def test_plain_formatter_no_title(console: Console):
    """Test PlainFormatter with panel without title."""
    from cyclopts.help import HelpEntry, HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    formatter = PlainFormatter()

    # Create a panel without title
    panel = HelpPanel(
        title="",
        description="",
        entries=[
            HelpEntry(
                names=("--option",),
                shorts=(),
                description="Test option",
                default="value",
            )
        ],
        format="parameter",
    )

    with console.capture() as capture:
        formatter(console, console.options, panel)

    actual = capture.get()
    # When panel has no title, PlainFormatter still indents entries with 2 spaces
    expected = "  --option: Test option [default: value]\n\n"
    assert actual == expected


def test_plain_formatter_render_methods(console: Console):
    """Test PlainFormatter render_usage and render_description methods."""
    from cyclopts.help.formatters import PlainFormatter

    app = App(
        help="Test application with plain formatter.",
        help_formatter=PlainFormatter(indent_width=4),
    )

    @app.default
    def main(
        verbose: bool = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS]

        Test application with plain formatter.

        Commands:
            --help, -h: Display this message and exit.
            --version: Display application version.

        Parameters:
            VERBOSE, --verbose, --no-verbose: [default: False]

        """
    )
    assert actual == expected


def test_plain_formatter_parameter_with_metadata(console: Console):
    """Test PlainFormatter with parameters having env_var, required."""
    from typing import Literal

    from cyclopts.help.formatters import PlainFormatter

    plain_group = Group(
        "Settings",
        help_formatter=PlainFormatter(),
    )

    app = App()

    @app.default
    def main(
        mode: Annotated[
            Literal["fast", "slow", "medium"], Parameter(group=plain_group, help="Operation mode", env_var="MODE")
        ],
        output: Annotated[
            str,
            Parameter(
                group=plain_group,
                help="Output file",
                required=True,
            ),
        ],
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    # Commands group uses default formatter
    expected = dedent(
        """\
        Usage: test_help_customization MODE OUTPUT

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        Settings:
          MODE, --mode: Operation mode [choices: fast, slow, medium] [env var:
        MODE] [required]
          OUTPUT, --output: Output file [required]

        """
    )
    assert actual == expected


def test_plain_formatter_command_multiple_names(console: Console):
    """Test PlainFormatter with command having multiple names."""
    from cyclopts.help.formatters import PlainFormatter

    app = App(help_formatter=PlainFormatter())

    @app.command(name=["list", "ls", "show"])
    def list_cmd():
        """List items."""
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization COMMAND

        Commands:
          list: List items.
          ls
          show
          --help, -h: Display this message and exit.
          --version: Display application version.

        """
    )
    assert actual == expected


def test_plain_formatter_command_only_shorts(console: Console):
    """Test PlainFormatter with entries having only short names."""
    from cyclopts.help import HelpEntry, HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    formatter = PlainFormatter()

    panel = HelpPanel(
        title="Options",
        description="",
        entries=[
            HelpEntry(
                names=(),
                shorts=("-v", "-vv"),
                description="Verbose output",
            )
        ],
        format="command",
    )

    with console.capture() as capture:
        formatter(console, console.options, panel)

    actual = capture.get()
    expected = dedent(
        """\
        Options:
          -v -vv: Verbose output

        """
    )
    assert actual == expected


def test_plain_formatter_rich_renderable(console: Console):
    """Test PlainFormatter with Rich renderable objects."""
    from rich.table import Table

    from cyclopts.help import HelpEntry, HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    formatter = PlainFormatter()

    # Create a Rich table as description
    table = Table(title="Test Table")
    table.add_column("Name")
    table.add_column("Value")
    table.add_row("test", "123")

    panel = HelpPanel(
        title="Rich Content",
        description=table,
        entries=[
            HelpEntry(
                names=("--option",),
                shorts=(),
                description="Test",
            )
        ],
        format="parameter",
    )

    # Note: PlainFormatter doesn't print panel description, only entries
    with console.capture() as capture:
        formatter(console, console.options, panel)

    actual = capture.get()
    expected = dedent(
        """\
        Rich Content:
          --option: Test

        """
    )
    assert actual == expected


def test_plain_formatter_none_values(console: Console):
    """Test PlainFormatter handles None values gracefully."""
    from cyclopts.help import HelpEntry, HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    formatter = PlainFormatter()

    panel = HelpPanel(
        title="Test",
        description=None,
        entries=[
            HelpEntry(
                names=("--test",),
                shorts=(),
                description=None,  # No description
                default=None,  # No default
            )
        ],
        format="parameter",
    )

    with console.capture() as capture:
        formatter(console, console.options, panel)

    actual = capture.get()
    expected = dedent(
        """\
        Test:
          --test

        """
    )
    assert actual == expected


def test_plain_formatter_fallback_str_conversion(console: Console):
    """Test PlainFormatter fallback to str() for unknown objects."""
    from cyclopts.help import HelpEntry, HelpPanel
    from cyclopts.help.formatters import PlainFormatter

    class CustomObject:
        def __str__(self):
            return "Custom description"

    formatter = PlainFormatter()

    panel = HelpPanel(
        title="Custom",
        description=CustomObject(),  # Object without __rich_console__ or .plain
        entries=[
            HelpEntry(
                names=("--custom",),
                shorts=(),
                description=CustomObject(),
            )
        ],
        format="parameter",
    )

    with console.capture() as capture:
        formatter(console, console.options, panel)

    actual = capture.get()
    expected = dedent(
        """\
        Custom:
          --custom: Custom description

        """
    )
    assert actual == expected


def test_description_renderer_newline_metadata():
    """Test DescriptionRenderer with newline_metadata=True."""
    from rich.console import Console

    # Create a test entry with metadata
    entry = HelpEntry(
        names=("verbose",),
        shorts=("--verbose",),
        description="Enable verbose output",
        env_var=("VERBOSE", "VERB"),
        default="False",
        choices=("true", "false"),
        required=False,
    )

    # Test with newline_metadata=True
    renderer = DescriptionRenderer(newline_metadata=True)
    result = renderer(entry)

    # Render to string for testing
    console = Console(width=80, force_terminal=False, legacy_windows=False)
    with console.capture() as capture:
        console.print(result, end="")

    output = capture.get()

    # Check that metadata is on separate lines
    lines = output.strip().split("\n")
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}: {lines}"

    assert lines[0] == "Enable verbose output"
    assert lines[1] == "[choices: true, false]"
    assert lines[2] == "[env var: VERBOSE, VERB]"
    assert lines[3] == "[default: False]"


def test_description_renderer_inline_metadata():
    """Test DescriptionRenderer with newline_metadata=False (default)."""
    from rich.console import Console

    # Create a test entry with metadata
    entry = HelpEntry(
        names=("verbose",),
        shorts=("--verbose",),
        description="Enable verbose output",
        env_var=("VERBOSE",),
        default="False",
        required=False,
    )

    # Test with newline_metadata=False (default)
    renderer = DescriptionRenderer(newline_metadata=False)
    result = renderer(entry)

    # Render to string for testing
    console = Console(width=80, force_terminal=False, legacy_windows=False)
    with console.capture() as capture:
        console.print(result, end="")

    output = capture.get()

    # Check that metadata is inline (all on one line)
    lines = output.strip().split("\n")
    assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"
    assert "Enable verbose output [env var: VERBOSE] [default: False]" in output


def test_with_newline_metadata_classmethod(console: Console):
    """Test DefaultFormatter.with_newline_metadata() classmethod."""
    app = App(help_formatter=DefaultFormatter.with_newline_metadata())

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(help="Enable verbose output", env_var="VERBOSE")] = False,
        config: Annotated[str, Parameter(help="Config file path", env_var=["CONFIG", "CFG"])] = "config.yaml",
        output: Annotated[str | None, Parameter(help="Output file")] = None,
    ):
        """Test application with newline metadata."""
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()

    # Check that metadata appears on separate lines
    assert "[env var: VERBOSE]" in actual
    assert "[default: False]" in actual
    assert "[env var: CONFIG, CFG]" in actual
    assert "[default: config.yaml]" in actual

    # Check structure - metadata should be on its own line
    lines = actual.split("\n")
    for i, line in enumerate(lines):
        if "Enable verbose output" in line:
            # Next lines should contain the metadata
            assert "[env var: VERBOSE]" not in line, "Metadata should not be inline"
            # Find the env var line (should be within next few lines)
            found_env = False
            found_default = False
            for j in range(i + 1, min(i + 4, len(lines))):
                if "[env var: VERBOSE]" in lines[j]:
                    found_env = True
                if "[default: False]" in lines[j]:
                    found_default = True
            assert found_env, "Should find env var on separate line"
            assert found_default, "Should find default on separate line"
            break


def test_default_formatter_regular_inline(console: Console):
    """Test that regular DefaultFormatter still shows metadata inline."""
    app = App(help_formatter=DefaultFormatter())

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(help="Enable verbose output", env_var="VERBOSE")] = False,
    ):
        """Test application with inline metadata."""
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()

    # Check that metadata is inline with description
    # Due to line wrapping in narrow console, we just check they're not on separate lines
    lines = actual.split("\n")

    # Find the line with "Enable verbose output"
    for i, line in enumerate(lines):
        if "Enable verbose output" in line:
            # Check that env var is on same or immediately continued line (not indented on new line)
            if "[env var: VERBOSE]" in line:
                # It's inline on the same line
                pass
            elif i + 1 < len(lines) and "[env var: VERBOSE]" in lines[i + 1]:
                # It wrapped to next line - check it's not indented like newline mode
                next_line = lines[i + 1]
                # In newline mode it would start directly with bracket
                # In inline mode it continues at the column position
                assert not next_line.lstrip().startswith("[env var"), "Should not be on its own line like newline mode"
            break
    else:
        assert False, "Should find description in output"


def test_description_renderer_no_extra_whitespace():
    """Test that DescriptionRenderer with newline_metadata doesn't add extra spaces."""
    from rich.console import Console

    entry = HelpEntry(
        names=("test",),
        description="Test description",
        env_var=("TEST_VAR",),
        default="value",
    )

    renderer = DescriptionRenderer(newline_metadata=True)
    result = renderer(entry)

    console = Console(width=80, force_terminal=False, legacy_windows=False)
    with console.capture() as capture:
        console.print(result, end="")

    output = capture.get()
    lines = output.strip().split("\n")

    # Check that metadata lines start with bracket (no indentation)
    for line in lines[1:]:  # Skip the description line
        if line.strip():  # Skip empty lines
            # The line should start with "[metadata...]" with no indentation
            assert line.startswith("["), f"Line should not be indented: {repr(line)}"
