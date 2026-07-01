"""Display a tree of a Cyclopts application's commands."""

from typing import Annotated

from rich.console import Console

from cyclopts.cli import app
from cyclopts.loader import load_app_from_script
from cyclopts.parameter import Parameter


@app.command
def tree(
    script: str,
    /,
    *,
    description: Annotated[bool, Parameter(alias="-d")] = True,
    max_depth: Annotated[int | None, Parameter(alias="-m")] = None,
):
    """Display a tree of a Cyclopts application's commands.

    Parameters
    ----------
    script : str
        Python script path, optionally with ``':app_object'`` notation to specify
        the App object. If not specified, will search for App objects in the
        script's global namespace.
    description : bool
        Show each command's short description next to its name.
    max_depth : Optional[int]
        Maximum subcommand depth to display. ``None`` (default) shows all.
    """
    app_obj, _ = load_app_from_script(script)
    Console().print(app_obj.command_tree(description=description, max_depth=max_depth))
