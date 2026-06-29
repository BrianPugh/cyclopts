"""Cyclopts CLI implementation."""

import cyclopts

# Create the main CLI app
app = cyclopts.App(name="cyclopts")
app.register_install_completion_command(
    help="""\
    Register shell-completion for the cyclopts CLI itself.
    """
)


from cyclopts.cli import _complete as _complete
from cyclopts.cli import docs as docs
from cyclopts.cli import run as run
from cyclopts.cli import tree as tree

__all__ = ["app"]
