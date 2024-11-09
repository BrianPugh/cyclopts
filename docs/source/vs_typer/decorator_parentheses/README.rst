=====================
Decorator Parentheses
=====================

A minor nitpick, but all of Typer's decorators require parentheses.


.. code-block:: python

   import typer

   typer_app = typer.Typer()

   # This doesn't work! Missing ()
   @typer_app.command
   def foo():
       pass

Cyclopts works with and without parentheses.

.. code-block:: python

   import cyclopts

   cyclopts_app = cyclopts.App()

   # This works! Missing ()
   @cyclopts_app.command
   def foo():
       pass

   # This also works.
   @cyclopts_app.command()
   def bar():
       pass
