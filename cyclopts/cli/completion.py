"""Shell completion CLI commands."""

import sys
from pathlib import Path
from typing import Annotated, Literal

from cyclopts.cli import app
from cyclopts.loader import load_app_from_script
from cyclopts.parameter import Parameter


@app.command
def generate_completion(
    script: Annotated[
        str,
        Parameter(help="Python script path with optional '::app_object' notation."),
    ],
    shell: Annotated[
        Literal["zsh"],
        Parameter(help="Shell type for completion."),
    ] = "zsh",
    output: Annotated[
        Path | None,
        Parameter(
            alias="-o",
            help="Output file. If not specified, prints to stdout.",
        ),
    ] = None,
):
    """Generate shell completion script for a Cyclopts application.

    Examples
    --------
    Generate and print to stdout:
        cyclopts generate-completion myapp.py::app

    Save to file:
        cyclopts generate-completion myapp.py::app -o _myapp

    Auto-detect app:
        cyclopts generate-completion myapp.py
    """
    app_obj, app_name = load_app_from_script(script)

    if shell == "zsh":
        from cyclopts.completion.zsh import generate_completion_script

        script_content = generate_completion_script(app_obj, app_name)
    else:
        raise ValueError(f"Unsupported shell: {shell}")

    if output:
        output.write_text(script_content)
        print(f"Completion script written to {output}", file=sys.stderr)
    else:
        print(script_content)
