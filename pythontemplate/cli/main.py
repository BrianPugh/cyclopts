import typer
from typer import Option
from typing_extensions import Annotated

import pythontemplate

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
# Add functions from other files like:
# app.command()(my_subcommand)


def version_callback(value: bool):
    if not value:
        return
    print(pythontemplate.__version__)
    raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    version: Annotated[
        bool,
        Option(
            "--version",
            "-v",
            callback=version_callback,
            help="Print gnwmanager version.",
        ),
    ] = False,
):
    pass


def run_app():
    app(prog_name="pythontemplate")
