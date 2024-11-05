=============
Help Defaults
=============
In Typer's ``--help`` display, default values are unhelpfully shown for required arguments.

.. code-block:: python

   import typer

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

It doesn't make any sense to show a default for a parameter that is required and has no default.
Cyclopts fixes this:

.. code-block:: python

   import cyclopts

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

Additionally, if the default value is :obj:`None`, cyclopts's default configuration will **not** display ``[default: None]``.
Doing so doesn't convey much meaning to the end-user.
Typically :obj:`None` is a sentinel value who's true value gets set inside the function.

Additionally, the cleaner, docstring-centric way of writing this program with Cyclopts would be:

.. code-block:: python

   import cyclopts
   from pathlib import Path

   cyclopts_app = cyclopts.App()

   @cyclopts_app.default()
   def compress(src: Path, dst: Path = Path("out.zip")):
       """Compress a file.

       Parameters
       ----------
       src: Path
          File to compress.
       dst: Path
          Path to save compressed data to.
       """
       print(f"Compressing data from {src} to {dst}")

   cyclopts_app(["--help"])
   # ╭─ Parameters ───────────────────────────────────────────────────────╮
   # │ *  SRC,--src  File to compress. [required]                         │
   # │    DST,--dst  Path to save compressed data to. [default: out.zip]  │
   # ╰────────────────────────────────────────────────────────────────────╯
