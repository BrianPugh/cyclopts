#!/usr/bin/env python
"""Demo of plain text help formatter for improved accessibility."""

from typing import Optional

from cyclopts import App
from cyclopts.help.formatters import PlainFormatter

app = App(
    name="mytool",
    help="A demonstration CLI tool with accessible plain text help.",
    help_formatter=PlainFormatter(),  # Use plain text formatter
    version="1.0.0",
)


@app.command
def init(
    path: str = ".",
    template: str = "default",
    force: bool = False,
):
    """Initialize a new project.

    Creates a new project structure at the specified path
    using the selected template.

    Parameters
    ----------
    path : str
        Directory where the project will be initialized.
    template : str
        Project template to use (default, minimal, full).
    force : bool
        Overwrite existing files if they exist.
    """
    print(f"Initializing project at {path} with template {template}")
    if force:
        print("Force mode enabled - will overwrite existing files")


@app.command
def build(
    source: str = "src",
    output: str = "dist",
    minify: bool = True,
    watch: bool = False,
):
    """Build the project.

    Compiles and packages the project from source files
    into the distribution directory.

    Parameters
    ----------
    source : str
        Source directory containing project files.
    output : str
        Output directory for built artifacts.
    minify : bool
        Minify the output files for production.
    watch : bool
        Watch for changes and rebuild automatically.
    """
    print(f"Building from {source} to {output}")
    if minify:
        print("Minification enabled")
    if watch:
        print("Watching for changes...")


@app.command
def deploy(
    environment: str,
    dry_run: bool = False,
    config: Optional[str] = None,
):
    """Deploy the application to the specified environment.

    Parameters
    ----------
    environment : str
        Target environment (dev, staging, production).
    dry_run : bool
        Simulate deployment without making actual changes.
    config : str
        Path to deployment configuration file.
    """
    print(f"Deploying to {environment}")
    if dry_run:
        print("DRY RUN - no actual changes will be made")
    if config:
        print(f"Using config from {config}")


@app.command
def clean(
    all: bool = False,
    cache: bool = True,
    logs: bool = False,
):
    """Clean build artifacts and temporary files.

    Parameters
    ----------
    all : bool
        Remove all generated files including configs.
    cache : bool
        Clear cache directories.
    logs : bool
        Remove log files.
    """
    if all:
        print("Cleaning all generated files")
    else:
        if cache:
            print("Clearing cache")
        if logs:
            print("Removing logs")


@app.default
def main(
    verbose: bool = False,
    quiet: bool = False,
    config: Optional[str] = None,
    jobs: int = 1,
):
    """Main entry point with global options.

    These options apply to all commands.

    Parameters
    ----------
    verbose : bool
        Enable verbose output for debugging.
    quiet : bool
        Suppress non-essential output.
    config : str
        Global configuration file path.
    jobs : int
        Number of parallel jobs for operations.
    """
    print("Welcome to mytool!")
    if verbose:
        print("Verbose mode enabled")
    if quiet:
        print("Quiet mode enabled")
    if config:
        print(f"Using config: {config}")
    print(f"Running with {jobs} parallel job(s)")


if __name__ == "__main__":
    app()
