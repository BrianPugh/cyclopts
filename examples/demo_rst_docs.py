#!/usr/bin/env python
"""Demo of RST documentation generation for Cyclopts CLI apps."""

from pathlib import Path
from typing import Optional

from cyclopts import App

app = App(
    name="mytool",
    help="A demonstration CLI tool with RST documentation generation.",
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


@app.default
def main(
    verbose: bool = False,
    quiet: bool = False,
    config: Optional[str] = None,
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
    """
    if verbose:
        print("Verbose mode enabled")
    if quiet:
        print("Quiet mode enabled")
    if config:
        print(f"Using config: {config}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-docs":
        # Generate RST documentation
        docs = app.generate_docs(output_format="rst")

        # Write to file or stdout
        if len(sys.argv) > 2:
            output_file = Path(sys.argv[2])
            output_file.write_text(docs)
            print(f"RST documentation written to {output_file}")
        else:
            print(docs)
    else:
        app()
