#!/usr/bin/env python
"""Example demonstrating help formatting customization.

This example shows various ways to customize the appearance of help panels:
1. Table styling (borders, padding, colors)
2. Panel styling (boxes, borders, padding)
3. Custom column definitions
4. Dynamic column builders
"""

from pathlib import Path
from typing import Annotated

from rich.box import DOUBLE, MINIMAL_HEAVY_HEAD, ROUNDED
from rich.console import Console

from cyclopts import App, Group, Parameter
from cyclopts.help import ColumnSpec, DefaultFormatter, PanelSpec, TableSpec

# === Example 1: Basic table and panel styling ===
# Customize the visual appearance of the help panel
required_group = Group(
    "Required Options",
    help="These options must be provided",
    help_formatter=DefaultFormatter(
        # PanelSpec handles the outer panel/box
        panel_spec=PanelSpec(
            box=DOUBLE,
            border_style="red",
            padding=(0, 2),
        ),
        # TableSpec now only handles table styling
        table_spec=TableSpec(
            border_style="red",
            show_header=True,
            padding=(0, 2, 0, 0),  # Add extra right padding
        ),
    ),
)

# === Example 2: Different styling for different groups ===
optional_group = Group(
    "Optional Settings",
    help="Fine-tune the application behavior",
    help_formatter=DefaultFormatter(
        panel_spec=PanelSpec(
            box=MINIMAL_HEAVY_HEAD,
            border_style="green",
        ),
        table_spec=TableSpec(
            border_style="green",
            padding=(0, 1),
            show_lines=False,  # No lines between rows
        ),
    ),
)

# === Example 3: Custom column definitions ===
# Define custom renderers for extracting and formatting data from HelpEntry objects


def type_renderer(entry):
    """Render the type annotation as a string.

    Renderers receive a HelpEntry and return a ~rich.console.RenderableType (str, Text, etc).
    """
    from cyclopts.annotations import get_hint_name

    if entry.type is None:
        return ""
    return get_hint_name(entry.type)


def names_renderer(entry):
    """Render names and shorts combined.

    HelpEntry has separate 'names' (e.g., ['INPUT-FILE'])
    and 'shorts' (e.g., ['--input-file']) attributes.
    """
    names_str = " ".join(entry.names) if entry.names else ""
    shorts_str = " ".join(entry.shorts) if entry.shorts else ""
    if names_str and shorts_str:
        return names_str + " " + shorts_str
    return names_str or shorts_str


def description_renderer(entry):
    """Render the description.

    Can also use string attribute names like renderer="description"
    instead of a callable renderer function.
    """
    return entry.description if entry.description is not None else ""


# Create a group with completely custom columns
advanced_group = Group(
    "Advanced",
    help_formatter=DefaultFormatter(
        panel_spec=PanelSpec(
            box=ROUNDED,
            border_style="blue",
        ),
        # Table styling is separate from column definitions
        table_spec=TableSpec(
            show_header=True,
            border_style="blue",
            show_lines=True,  # Show lines between rows
        ),
        # Define custom columns with headers and styling
        column_specs=(
            ColumnSpec(renderer=names_renderer, style="cyan bold", header="Flag", max_width=20),
            ColumnSpec(renderer=type_renderer, style="yellow", header="Type", justify="center"),
            ColumnSpec(renderer=description_renderer, header="What it does", overflow="fold"),
        ),
    ),
)


# === Example 4: Dynamic column builder ===
# Create columns dynamically based on console width and entries
def custom_column_builder(console, options, entries):
    """Build columns dynamically based on runtime context.

    This function receives:
    - console: Rich Console instance (for width calculations)
    - options: Console rendering options
    - entries: List of HelpEntry objects to be displayed

    Returns a tuple of ColumnSpec objects.
    """
    # Calculate max width based on console size
    max_width = int(console.width * 0.4)

    # Only show asterisk column if there are required parameters
    columns = []
    if any(e.required for e in entries):
        # Add asterisk column for required indicators
        columns.append(
            ColumnSpec(
                renderer=lambda entry: "★" if entry.required else " ",
                header="",
                width=2,
                style="bold yellow",
            )
        )

    # Add name column
    columns.append(
        ColumnSpec(
            renderer=names_renderer,
            header="Option",
            style="cyan",
            max_width=max_width,
        )
    )

    # Add description column
    columns.append(
        ColumnSpec(
            renderer=description_renderer,
            header="Description",
            overflow="fold",
        )
    )

    return tuple(columns)


# Group using the dynamic column builder
dynamic_group = Group(
    "Dynamic Options",
    help="Options with dynamically generated columns",
    help_formatter=DefaultFormatter(
        table_spec=TableSpec(
            show_header=True,
            border_style="magenta",
        ),
        column_specs=custom_column_builder,  # Pass the builder function
    ),
)

# Create the app
app = App(
    name="fancy-cli",
    help="A CLI application with customized help formatting",
)


@app.default
def main(
    # Required parameters
    input_file: Annotated[
        Path,
        Parameter(group=required_group, help="Path to the input file to process"),
    ],
    output_dir: Annotated[
        Path,
        Parameter(group=required_group, help="Directory where results will be saved"),
    ],
    # Optional parameters
    verbose: Annotated[
        bool,
        Parameter(group=optional_group, help="Enable verbose output"),
    ] = False,
    threads: Annotated[
        int,
        Parameter(group=optional_group, help="Number of worker threads"),
    ] = 4,
    # Advanced parameters with custom columns
    buffer_size: Annotated[
        int,
        Parameter(group=advanced_group, help="Size of the internal buffer in KB"),
    ] = 1024,
    experimental: Annotated[
        bool,
        Parameter(
            group=advanced_group,
            help="Enable experimental features that may be unstable",
        ),
    ] = False,
    # Dynamic group parameters
    cache: Annotated[
        bool,
        Parameter(group=dynamic_group, help="Enable caching for faster processing"),
    ] = True,
    timeout: Annotated[
        int,
        Parameter(group=dynamic_group, help="Operation timeout in seconds"),
    ] = 30,
    # Regular parameter (will use default formatting)
    version: Annotated[
        bool,
        Parameter(help="Show version and exit"),
    ] = False,
):
    """Process files with custom formatting.

    This application demonstrates how to customize help panel appearance
    using the new API where:
    - TableSpec handles table styling (borders, padding, colors)
    - PanelSpec handles panel/box styling
    - Columns are defined separately in DefaultFormatter
    """
    print(f"Processing {input_file} -> {output_dir}")
    if verbose:
        print(f"Using {threads} threads")
        print(f"Buffer size: {buffer_size}KB")
        if experimental:
            print("Experimental features enabled")
        if cache:
            print("Caching enabled")
        print(f"Timeout: {timeout}s")


@app.command
def analyze():
    """Analyze the processed data."""
    print("Analyzing...")


@app.command
def report():
    """Generate a report from the analysis."""
    print("Generating report...")


if __name__ == "__main__":
    # Print the help to show the customization
    console = Console()
    print("=" * 70)
    print("HELP OUTPUT WITH CUSTOMIZED FORMATTING:")
    print("=" * 70)
    app.help_print(console=console)

    print("\n" + "=" * 70)
    print("KEY FEATURES DEMONSTRATED:")
    print("=" * 70)
    print("1. Required Options: Red double-border box with extra padding")
    print("2. Optional Settings: Green minimal box with different padding")
    print("3. Advanced: Custom columns with headers (Flag, Type, Description)")
    print("4. Dynamic Options: Columns built dynamically with star indicators")
    print("5. Parameters: Default formatting for comparison")
    print("\nNOTE: TableSpec now only handles table styling,")
    print("      while columns are defined separately in DefaultFormatter")

    # Uncomment to run the actual app
    # app()
