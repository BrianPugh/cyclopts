#!/usr/bin/env python3
"""Example demonstrating Sphinx extension with distinct command headings.

This example shows how to use the new directive options:
- :flatten-commands: - Keep all commands at the same heading level
- :command-prefix: - Add a prefix to command headings
- :generate-anchors: - Generate RST reference labels

To generate documentation with these options in your Sphinx docs:

.. cyclopts:: examples.sphinx_distinct_headings:app
   :flatten-commands: true
   :command-prefix: "Command: "
   :generate-anchors: true
"""

from pathlib import Path
from typing import Optional

from cyclopts import App

# Create the main application
app = App(name="myapp", help="Example CLI with subcommands", version="1.0.0")

# Create subcommands
database_app = App(name="database", help="Database management commands")
deploy_app = App(name="deploy", help="Deployment commands")


@app.command
def init(
    path: Path = Path(),
    template: str = "default",
    *,
    force: bool = False,
) -> None:
    """Initialize a new project.

    Parameters
    ----------
    path : Path
        Directory to initialize the project in.
    template : str
        Template to use for initialization.
    force : bool
        Force initialization even if directory is not empty.
    """
    print(f"Initializing project at {path} with template '{template}'")
    if force:
        print("  (forced initialization)")


@database_app.command
def migrate(version: Optional[str] = None, *, dry_run: bool = False) -> None:
    """Run database migrations.

    Parameters
    ----------
    version : str, optional
        Specific migration version to target.
    dry_run : bool
        Show what would be migrated without actually doing it.
    """
    if dry_run:
        print("Dry run - no changes will be made")
    if version:
        print(f"Migrating database to version {version}")
    else:
        print("Migrating database to latest version")


@database_app.command
def backup(output: Path, *, compress: bool = True) -> None:
    """Create a database backup.

    Parameters
    ----------
    output : Path
        Output file for the backup.
    compress : bool
        Compress the backup file.
    """
    print(f"Creating database backup at {output}")
    if compress:
        print("  (with compression)")


@deploy_app.command
def staging(
    version: str = "latest",
    *,
    skip_tests: bool = False,
) -> None:
    """Deploy to staging environment.

    Parameters
    ----------
    version : str
        Version to deploy.
    skip_tests : bool
        Skip running tests before deployment.
    """
    if not skip_tests:
        print("Running tests...")
    print(f"Deploying version {version} to staging")


@deploy_app.command
def production(
    version: str,
    *,
    backup_first: bool = True,
    verify: bool = True,
) -> None:
    """Deploy to production environment.

    Parameters
    ----------
    version : str
        Specific version to deploy (required for production).
    backup_first : bool
        Create a backup before deployment.
    verify : bool
        Verify deployment after completion.
    """
    if backup_first:
        print("Creating backup before deployment...")
    print(f"Deploying version {version} to production")
    if verify:
        print("Verifying deployment...")


# Register subcommands
app.command(database_app)
app.command(deploy_app)


if __name__ == "__main__":
    app()
