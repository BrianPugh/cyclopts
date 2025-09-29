#!/usr/bin/env python
"""Demo of command filtering in RST documentation and Sphinx directives."""

from cyclopts import App

# Create main app
app = App(name="myapp", help="A complex CLI application")

# Database commands
db_app = App(name="db", help="Database management commands")


@db_app.command
def migrate():
    """Run database migrations."""
    print("Running migrations...")


@db_app.command
def backup():
    """Backup the database."""
    print("Creating backup...")


@db_app.command
def restore():
    """Restore database from backup."""
    print("Restoring database...")


# API commands
api_app = App(name="api", help="API server commands")


@api_app.command
def start():
    """Start the API server."""
    print("Starting API server...")


@api_app.command
def stop():
    """Stop the API server."""
    print("Stopping API server...")


@api_app.command
def restart():
    """Restart the API server."""
    print("Restarting API server...")


# Development commands
dev_app = App(name="dev", help="Development tools")


@dev_app.command
def lint():
    """Run code linters."""
    print("Running linters...")


@dev_app.command
def test():
    """Run tests."""
    print("Running tests...")


@dev_app.command
def debug():
    """Start debug mode (internal use only)."""
    print("Debug mode activated...")


# Add all subcommands to main app
app.command(db_app)
app.command(api_app)
app.command(dev_app)


# Simple top-level command
@app.command
def status():
    """Show application status."""
    print("Application is running")


if __name__ == "__main__":
    import sys

    if "--demo-filters" in sys.argv:
        from cyclopts.docs.rst import generate_rst_docs

        print("=" * 60)
        print("FULL DOCUMENTATION (no filters)")
        print("=" * 60)
        docs = generate_rst_docs(app, recursive=True)
        print(docs[:500] + "...")

        print("\n" + "=" * 60)
        print("FILTERED: Only database commands")
        print("=" * 60)
        docs = generate_rst_docs(app, recursive=True, commands_filter=["db"])
        print(docs[:500] + "...")

        print("\n" + "=" * 60)
        print("FILTERED: Specific nested commands")
        print("=" * 60)
        docs = generate_rst_docs(app, recursive=True, commands_filter=["db.migrate", "api.start", "status"])
        print(docs[:800] + "...")

        print("\n" + "=" * 60)
        print("EXCLUDED: Debug and internal commands")
        print("=" * 60)
        docs = generate_rst_docs(app, recursive=True, exclude_commands=["dev.debug", "db.restore"])
        print(docs[:500] + "...")

        print("\n" + "=" * 60)
        print("For Sphinx integration, use the directive options:")
        print("=" * 60)
        print("""
.. cyclopts:: myapp:app
   :commands: db, api.start
   :exclude-commands: dev.debug
   :recursive:
        """)
    else:
        app()
