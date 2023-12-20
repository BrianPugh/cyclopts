import sys
from pathlib import Path
from typing import List, Optional

import typer

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def compress(
    src: Annotated[Path, typer.Argument(help="File to compress.")],
    dst: Annotated[Path, typer.Argument(help="Path to save compressed data to.")] = Path("out.zip"),
):
    print(f"Compressing data from {src} to {dst}")


print("Typer positional:")
typer_app(["--help"], standalone_mode=False)
# ╭─ Arguments ───────────────────────────────────────────────────────────────╮
# │ *    src      PATH   File to compress. [default: None] [required]         │
# │      dst      [DST]  Path to save compressed data to. [default: out.zip]  │
# ╰───────────────────────────────────────────────────────────────────────────╯

cyclopts_app = cyclopts.App()


@cyclopts_app.default()
def compress(
    src: Annotated[Path, cyclopts.Parameter(help="File to compress.")],
    dst: Annotated[Path, cyclopts.Parameter(help="Path to save compressed data to.")] = Path("out.zip"),
):
    print(f"Compressing data from {src} to {dst}")


cyclopts_app(["--help"])
# ╭─ Parameters ───────────────────────────────────────────────────────╮
# │ *  SRC,--src  File to compress. [required]                         │
# │    DST,--dst  Path to save compressed data to. [default: out.zip]  │
# ╰────────────────────────────────────────────────────────────────────╯
