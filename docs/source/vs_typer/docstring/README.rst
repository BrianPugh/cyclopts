.. _Typer Docstring Parsing:

=================
Docstring Parsing
=================
Typer performs no docstring parsing.
Frequently, Typer's Argument/Option is only used to provide a ``help`` string.
However, this ``help`` string commonly mirrors the function's docstring.

Consider the following Typer program:

.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.callback()
   def dummy():
       # So that ``foo`` is considered a command.
       pass


   @typer_app.command()
   def foo(bar):
       """Foo Docstring.

       Parameters
       ----------
       bar: str
           Bar parameter docstring.
       """
       pass

.. code-block:: console

   $ my-script --help
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ foo                 Foo Docstring.                                    │
   ╰───────────────────────────────────────────────────────────────────────╯

   $ my-script foo --help
   Foo Docstring.
   Parameters ---------- bar: str     Bar parameter docstring.

   ╭─ Arguments ───────────────────────────────────────────────────────────╮
   │ *    bar      TEXT  [default: None] [required]                        │
   ╰───────────────────────────────────────────────────────────────────────╯

The ``foo`` command's short description was properly parsed from the docstring.
However, it mangles the Numpy-style docstring (or any docstring format for that matter) and doesn't correctly display ``bar``'s help.
Typer just displays the entire docstring.

To achieve the desired result with Typer, we have to explicitly annotate the parameter ``bar``:

.. code-block:: python

   @typer_app.command()
   def foo(bar: Annotated[str, Argument(help="Bar parameter docstring.")]):
       ...

For any serious application, this means that every function parameter must be annotated this way, significantly bloating the function signature.

Compare this to Cyclopts:

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.command()
   def foo(bar):
       """Foo Docstring.

       Parameters
       ----------
       bar: str
           Bar parameter docstring.
       """
       pass

.. code-block:: console

   $ my-script --help
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ foo  Foo Docstring.                                                   │
   ╰───────────────────────────────────────────────────────────────────────╯

   $ my-script foo --help

   Foo Docstring.

   ╭─ Parameters ──────────────────────────────────────────────────────────╮
   │ *  BAR,--bar  Bar parameter docstring. [required]                     │
   ╰───────────────────────────────────────────────────────────────────────╯

Cyclopts did not mangle the docstring into the long description, and it correctly parsed ``bar``'s help.
This ends up significantly simplifying function signatures in the common situation where just a help string needs to be added.
The common case in Cyclopts does not require the lengthy ``Annotated[str, Parameter(help="Bar parameter docstring")]``.

Internally, Cyclopts uses the excellent `docstring_parser`_ library for parsing docstrings. Check their project out!

.. _docstring_parser: https://github.com/rr-/docstring_parser
