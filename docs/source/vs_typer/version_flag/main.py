import sys

import typer

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

import cyclopts

typer_app = typer.Typer()


def version_callback(value: bool):
    if not value:
        return
    print(typer.__version__)
    raise typer.Exit()


@typer_app.callback()
def common(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            help="Print version.",
        ),
    ] = False,
):
    print("Callback body executed.")


print("Typer:")
typer_app(["--version"], standalone_mode=False)
# 0.9.0


# If ``version`` is not specified, Cyclopts will attempt to use
# ``your_library.__version__`` based on the module ``App`` is instantiated in.
# If the discovery fails, Cyclopts will fallback to ``0.0.0``
cyclopts_app = cyclopts.App(version=typer.__version__)

print("Cyclopts:")
cyclopts_app(["--version"])
# 0.9.0
