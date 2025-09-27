"""Cyclopts CLI implementation."""

import cyclopts

# Create the main CLI app
app = cyclopts.App(name="cyclopts")


# Explicitly import command modules
from cyclopts.cli import docs  # noqa: F401

__all__ = ["app"]
