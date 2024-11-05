===============================
Positional or Keyword Arguments
===============================
A limitation of Typer is that a parameter cannot be both positional and keyword.

For example, lets say we want to implement a ``mv``\-like program that takes in a source path, and a destination path:

.. code-block:: python

   typer_app = typer.Typer()

   @typer_app.command()
   def mv(src, dst):
       print(f"Moving {src} -> {dst}")

   typer_app(["foo", "bar"], standalone_mode=False)
   # Moving foo -> bar

The code works when supplying the inputs as positional arguments, but fails when trying to specify them as keywords.

.. code-block:: python

   print("Typer keyword:")
   typer_app(["--src", "foo", "--dst", "bar"], standalone_mode=False)
   # No such option: --src

Cyclopts handles both situations:

.. code-block:: python

   cyclopts_app = cyclopts.App()

   @cyclopts_app.default()
   def mv(src, dst):
       print(f"Moving {src} -> {dst}")

   cyclopts_app(["foo", "bar"])
   # Moving foo -> bar
   cyclopts_app(["--src", "foo", "--dst", "bar"])
   # Moving foo -> bar
