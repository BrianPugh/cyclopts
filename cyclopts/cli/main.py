"""Main Cyclopts CLI application."""

import cyclopts

app = cyclopts.App(name="cyclopts")


@app.default
def main():
    """Cyclopts CLI - Command line tools for Cyclopts application development."""
    print("Cyclopts CLI - Coming soon!")
    print("Use --help to see available commands")
