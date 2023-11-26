=====================
Decorator Parentheses
=====================

A minor nitpick, but all of Typer's decorators require parentheses.


.. code-block:: python

   # This doesn't work! Missing ()
   @typer_app.command
   def foo():
       pass

Cyclopts works with and without parentheses.

.. code-block:: python

   # This works! Missing ()
   @cyclopts_app.command
   def foo():
       pass


   @cyclopts_app.command()
   def bar():
       pass
