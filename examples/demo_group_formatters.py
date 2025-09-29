#!/usr/bin/env python
"""Demo of different formatters for different groups.

This example shows how Groups can have their own formatters with custom configuration.
"""

from typing import Annotated, Optional

from rich.box import HEAVY

from cyclopts import App, Group, Parameter
from cyclopts.help import DefaultFormatter, PanelSpec, TableSpec
from cyclopts.help.formatters import PlainFormatter

# Create app with default Rich formatter
app = App(
    name="mytool",
    help="A demonstration of per-group formatter customization.",
    version="1.0.0",
)

# Create a group with a customized Rich formatter
fancy_group = Group.create_ordered(
    name="Advanced Options",
    help="These options use fancy Rich formatting with custom table/panel specs.",
    help_formatter=DefaultFormatter(
        panel_spec=PanelSpec(
            box=HEAVY,
            border_style="blue",
            padding=(1, 2),
        ),
        table_spec=TableSpec(
            padding=(0, 3),
            show_lines=True,
        ),
    ),
)

# Create a group with plain formatter for accessibility
simple_group = Group.create_ordered(
    name="Basic Options",
    help="These options use plain text formatting for better accessibility.",
    help_formatter=PlainFormatter(indent_width=4, max_width=80),
)


@app.default
def main(
    verbose: bool = False,
    config: Optional[str] = None,
    debug: Annotated[bool, Parameter(group=fancy_group)] = False,
    trace: Annotated[bool, Parameter(group=fancy_group)] = False,
    output: Annotated[str, Parameter(group=simple_group)] = "output.txt",
    format: Annotated[str, Parameter(group=simple_group)] = "json",
):
    """Main entry point with mixed formatting groups.

    Parameters
    ----------
    verbose : bool
        Enable verbose output (uses app's default formatter).
    config : str
        Configuration file path (uses app's default formatter).
    debug : bool
        Enable debug mode (uses fancy Rich formatter).
    trace : bool
        Enable trace logging (uses fancy Rich formatter).
    output : str
        Output file path (uses plain formatter).
    format : str
        Output format (uses plain formatter).
    """
    print("Running with mixed formatter groups!")
    if verbose:
        print("Verbose mode enabled")
    if debug:
        print("Debug mode enabled")
    if trace:
        print("Trace mode enabled")
    print(f"Output will be written to: {output}")
    print(f"Output format: {format}")

    # Show help to demonstrate the different formatters
    app.parse_args(["--help"])


@app.command
def process(
    input_file: str,
    algorithm: str = "fast",
    threads: Annotated[int, Parameter(group=fancy_group)] = 4,
    memory_limit: Annotated[str, Parameter(group=fancy_group)] = "1GB",
    quiet: Annotated[bool, Parameter(group=simple_group)] = False,
    dry_run: Annotated[bool, Parameter(group=simple_group)] = False,
):
    """Process data with various options.

    Parameters
    ----------
    input_file : str
        Input file to process.
    algorithm : str
        Processing algorithm to use.
    threads : int
        Number of processing threads (fancy formatting).
    memory_limit : str
        Maximum memory usage (fancy formatting).
    quiet : bool
        Suppress output (plain formatting).
    dry_run : bool
        Simulate without actual processing (plain formatting).
    """
    print(f"Processing {input_file} with {algorithm} algorithm")
    print(f"Using {threads} threads with {memory_limit} memory limit")
    if quiet:
        print("Running in quiet mode")
    if dry_run:
        print("DRY RUN - no actual processing")


if __name__ == "__main__":
    app()
