"""Generate documentation for Cyclopts applications."""

from pathlib import Path
from typing import Annotated, Literal, Optional

from cyclopts.cli import app
from cyclopts.group import Group
from cyclopts.loader import load_app_from_script
from cyclopts.parameter import Parameter
from cyclopts.utils import UNSET


def _format_group_validator(argument_collection):
    format_arg = argument_collection.get("--format")
    output_arg = argument_collection.get("--output")

    if format_arg.value is UNSET:
        if output_arg.value is UNSET:
            raise ValueError('"--format" must be specified when output path is not provided.')

        suffix = output_arg.value.suffix.lower()
        if suffix in (".md", ".markdown"):
            format_arg.value = "markdown"
        elif suffix in (".html", ".htm"):
            format_arg.value = "html"
        elif suffix in (".rst", ".rest"):
            format_arg.value = "rst"
        else:
            raise ValueError(
                f'Cannot infer format from output extension "{suffix}". Please specify "--format" explicitly.'
            )


format_group = Group(validator=_format_group_validator)


@app.command(default_parameter=Parameter(negative=""))
def generate_docs(
    script: str,
    output: Annotated[Optional[Path], Parameter(group=format_group)] = None,
    *,
    format: Annotated[Optional[Literal["markdown", "html", "rst"]], Parameter(group=format_group)] = None,
    recursive: bool = True,
    include_hidden: bool = False,
    heading_level: int = 1,
):
    """Generate documentation for a Cyclopts application.

    Parameters
    ----------
    script : str
        Python script path, optionally with '::app_object' notation to specify
        the App object. If not specified, will search for App objects in the
        script's global namespace.
    output : Optional[Path]
        Output file path. If not specified, prints to stdout.
    format : Optional[Literal["markdown", "html", "rst"]]
        Output format for documentation. If not specified, inferred from output
        file extension (.md/.markdown for markdown, .html/.htm for html,
        .rst/.rest for reStructuredText).
    recursive : bool
        Include documentation for subcommands recursively.
    include_hidden : bool
        Include hidden commands in documentation.
    heading_level : int
        Starting heading level for markdown format.
    """
    assert format is not None  # Handled by _format_group_validator

    # Load the App object from the script
    app_obj, _ = load_app_from_script(script)

    # Generate documentation
    docs_content = app_obj.generate_docs(
        output_format=format,
        recursive=recursive,
        include_hidden=include_hidden,
        heading_level=heading_level,
    )

    if output:
        output.write_text(docs_content)
    else:
        print(docs_content)
