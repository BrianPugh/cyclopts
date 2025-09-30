"""Run Cyclopts applications from Python scripts."""

from typing import Annotated

from cyclopts.cli import app
from cyclopts.loader import load_app_from_script
from cyclopts.parameter import Parameter


@app.command
def run(
    script: Annotated[
        str,
        Parameter(help="Python script path with optional '::app_object' notation."),
    ],
    *args: Annotated[str, Parameter(allow_leading_hyphen=True)],
):
    """Run a Cyclopts application from a Python script.

    All arguments after the script path are passed to the loaded application.

    Examples
    --------
    Run a script:
        cyclopts run myapp.py --verbose foo bar

    Specify app object:
        cyclopts run myapp.py::app --help
    """
    app_obj, app_name = load_app_from_script(script)

    # Execute the loaded app with remaining args
    return app_obj(args)
