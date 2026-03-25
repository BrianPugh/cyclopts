.. _Parse Mode:

==========
Parse Mode
==========
When using :ref:`Meta Apps <Meta App>`, you may run into situations where:

- A parent and subcommand both define a parameter with the same name (e.g., both use ``-v``),
  and you need the CLI to determine which ``-v`` belongs to which command based on its position.
- You want ``myapp --verbose subcommand`` to work, but ``myapp subcommand --verbose`` to be
  rejected because ``--verbose`` belongs to the parent, not the subcommand.

The :attr:`.App.parse_mode` setting controls how parameters are scoped across command levels.

There are two modes:

- ``"fallthrough"`` **(default)**: Unmatched parameters fall through to parent levels. If a subcommand doesn't recognize a parameter, cyclopts checks whether a parent meta app defines it. When both levels define the same flag, the child wins.

- ``"strict"``: Parameters only bind to the command level where they appear. A meta-app parameter placed after a subcommand is rejected with a helpful error message.

----------------
Fallthrough Mode
----------------
In the default ``"fallthrough"`` mode, meta-app parameters can appear **anywhere** in the
token stream. This is convenient because users don't need to know which flags
belong to which level.

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   @app.meta.default
   def main(
       *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
       verbose: Annotated[bool, Parameter(alias="-v")] = False,
   ):
       if verbose:
           print("[verbose mode]")
       app(tokens)

   @app.command
   def greet(name: str, *, version: Annotated[bool, Parameter(alias="-v")] = False):
       """Greet someone."""
       if version:
           print("[version flag]")
       print(f"Hello, {name}!")

   app.meta()

The ``--verbose`` flag can be placed before or after the subcommand:

.. code-block:: console

   $ my-script --verbose greet Alice
   [verbose mode]
   Hello, Alice!

   $ my-script greet --verbose Alice
   [verbose mode]
   Hello, Alice!

When both the meta app and the subcommand define a parameter with the same name (``-v``), the
**child wins** for flags placed after the subcommand:

.. code-block:: console

   $ my-script -v greet Alice
   [verbose mode]
   Hello, Alice!

   $ my-script greet -v Alice
   [version flag]
   Hello, Alice!

   $ my-script -v greet -v Alice
   [verbose mode]
   [version flag]
   Hello, Alice!

-----------
Strict Mode
-----------
In ``"strict"`` mode, parameters are scoped to the command level where they appear.
Each parameter **must** be placed directly after the command it belongs to — placing
a parent-level parameter after a subcommand is rejected with a helpful error message.

This is useful when:

- Migrating from Click or Typer, which use strict scoping by default.
- Subcommands need to redefine a flag name for a different purpose.
- You want to prevent users from accidentally passing parent-level flags in the wrong position.

.. code-block:: python

   app = App(parse_mode="strict")

   @app.meta.default
   def main(
       *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
       verbose: Annotated[bool, Parameter(alias="-v")] = False,
   ):
       if verbose:
           print("[verbose mode]")
       app(tokens)

   @app.command
   def greet(name: str, *, version: Annotated[bool, Parameter(alias="-v")] = False):
       """Greet someone."""
       if version:
           print("[version flag]")
       print(f"Hello, {name}!")

   app.meta()

Parameters **must** be placed directly after the command they belong to.
``--verbose`` belongs to the root app, so it **must** appear directly after ``my-script``:

.. code-block:: console

   $ my-script --verbose greet Alice
   [verbose mode]
   Hello, Alice!

   $ my-script greet --verbose Alice
   ╭─ Error ────────────────────────────────────────────────────╮
   │ Unknown option: "--verbose". Did you mean to place it      │
   │ directly after "my-script"?                                │
   ╰────────────────────────────────────────────────────────────╯

When both levels share a name, each ``-v`` **must** be placed directly after the command it belongs to:

.. code-block:: console

   $ my-script -v greet -v Alice
   [verbose mode]
   [version flag]
   Hello, Alice!

----------
Help Pages
----------
In strict mode, subcommand help pages only show parameters that are valid for that
command — parent meta-app parameters are excluded.

.. code-block:: console

   $ my-script greet --help
   Usage: my-script greet [OPTIONS] NAME

   Greet someone.

   ╭─ Parameters ───────────────────────────────────────────────╮
   │ *  NAME --name                [required]                   │
   │    --version -v --no-version  [default: False]             │
   ╰────────────────────────────────────────────────────────────╯

In fallthrough mode, the same help page would also include ``--verbose`` from the meta app.

-----------
Inheritance
-----------
``parse_mode`` is inherited by child apps. Setting it on the root app applies to all subcommands
unless explicitly overridden:

.. code-block:: python

   app = App(parse_mode="strict")

   # All subcommands inherit parse_mode="strict"
   sub = App(name="sub")
   app.command(sub)

   # Override for a specific subcommand
   special = App(name="special", parse_mode="fallthrough")
   app.command(special)
