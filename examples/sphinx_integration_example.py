#!/usr/bin/env python
"""
Example: Integrating Cyclopts with Sphinx Documentation
========================================================

This example demonstrates how to use the Cyclopts Sphinx extension to
automatically generate CLI documentation in your Sphinx docs.

Setup Steps:
------------

1. Install Sphinx (if not already installed):
   pip install sphinx

2. In your Sphinx conf.py, add the Cyclopts extension:
   extensions = ['cyclopts.sphinx_ext']

3. In your RST documentation files, use the cyclopts directive:

   .. cyclopts:: mypackage.cli:app
      :heading-level: 2
      :recursive: true
      :include-hidden: false

Directive Options:
------------------

- ``:heading-level:`` - Starting heading level (1-6)
- ``:recursive:`` - Include subcommands recursively (default: true)
- ``:include-hidden:`` - Include hidden commands in documentation

Module Path Formats:
--------------------

The directive accepts module paths in two formats:

1. Explicit: ``module.path:app_name``
   Specifies exactly which App object to document

2. Automatic: ``module.path``
   Searches the module for an App instance (looks for 'app', 'cli', 'main')

Example CLI Application:
------------------------

Below is a sample CLI application that could be documented with Sphinx.
"""

from pathlib import Path
from typing import Literal, Optional

from cyclopts import App

# Create the main application
app = App(
    name="doctools",
    help="Documentation tools CLI - example for Sphinx integration",
    version="1.0.0",
)

# Database subcommands
db_app = App(name="db", help="Database management commands")


@db_app.command
def migrate(version: Optional[str] = None, *, dry_run: bool = False):
    """Run database migrations.

    Parameters
    ----------
    version : str, optional
        Target migration version. If not specified, migrates to latest.
    dry_run : bool
        Show what would be migrated without making changes.
    """
    print(f"Migrating database to version {version or 'latest'}")
    if dry_run:
        print("(Dry run - no changes made)")


@db_app.command
def backup(output: Path = Path("backup.sql"), *, compress: bool = True):
    """Create a database backup.

    Parameters
    ----------
    output : Path
        Output file for the backup.
    compress : bool
        Compress the backup file with gzip.
    """
    print(f"Backing up database to {output}")
    if compress:
        print("Compressing backup...")


# API subcommands
api_app = App(name="api", help="API server management")


@api_app.command
def start(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    reload: bool = False,
    workers: int = 1,
):
    """Start the API server.

    Parameters
    ----------
    host : str
        Host to bind the server to.
    port : int
        Port to listen on.
    reload : bool
        Enable auto-reload on code changes.
    workers : int
        Number of worker processes.
    """
    print(f"Starting API server on {host}:{port}")
    if reload:
        print("Auto-reload enabled")
    print(f"Running with {workers} worker(s)")


@api_app.command(show=False)  # Hidden command
def debug():
    """Debug mode for the API server (hidden command)."""
    print("Running in debug mode...")


# Main app commands
@app.command
def init(
    project_name: str,
    template: Literal["basic", "advanced", "minimal"] = "basic",
    *,
    force: bool = False,
):
    """Initialize a new project.

    Parameters
    ----------
    project_name : str
        Name of the project to create.
    template : {"basic", "advanced", "minimal"}
        Project template to use.
    force : bool
        Overwrite existing project if it exists.
    """
    print(f"Initializing project '{project_name}' with template '{template}'")
    if force:
        print("Force mode: will overwrite existing files")


@app.command
def config(key: Optional[str] = None, value: Optional[str] = None):
    """View or set configuration values.

    Parameters
    ----------
    key : str, optional
        Configuration key to get/set.
    value : str, optional
        Value to set for the key.
    """
    if key is None:
        print("Showing all configuration...")
    elif value is None:
        print(f"Getting config value for '{key}'")
    else:
        print(f"Setting {key} = {value}")


# Register subcommands
app.command(db_app)
app.command(api_app)


if __name__ == "__main__":
    # Example of generating docs programmatically
    import sys

    if "--generate-sphinx-example" in sys.argv:
        # Create example Sphinx files
        docs_dir = Path("example_sphinx_docs")
        docs_dir.mkdir(exist_ok=True)

        # Create a minimal conf.py
        conf_py = docs_dir / "conf.py"
        conf_py.write_text("""
# Sphinx configuration for Cyclopts example
import sys
from pathlib import Path

# Add parent directory to path so we can import our app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Sphinx extensions
extensions = [
    'cyclopts.sphinx_ext',  # Cyclopts integration
    'sphinx.ext.autodoc',    # For documenting Python code
]

# Project information
project = 'Doctools CLI'
author = 'Example Author'
version = '1.0.0'

# HTML theme
html_theme = 'sphinx_rtd_theme'  # or 'alabaster'
""")

        # Create index.rst with cyclopts directive
        index_rst = docs_dir / "index.rst"
        index_rst.write_text("""
Doctools Documentation
======================

Welcome to the Doctools CLI documentation!

CLI Reference
-------------

The following documentation is automatically generated from the CLI application:

.. cyclopts:: sphinx_integration_example:app
   :recursive: true

API Documentation
-----------------

You can also document your Python API alongside your CLI:

.. automodule:: sphinx_integration_example
   :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
""")

        print(f"Created example Sphinx documentation in {docs_dir}/")
        print("\nTo build the documentation:")
        print(f"  cd {docs_dir}")
        print("  sphinx-build . _build/html")
        print("\nThen open _build/html/index.html in your browser")

    else:
        # Run the CLI normally
        app()
