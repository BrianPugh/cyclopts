=====================
Argument vs Parameter
=====================
In Typer, the actual difference between the ``Argument`` and ``Option`` classes aren't very clear.
Generally, it can be said that:

* Options are **optional** and are provided as keyword arguments, preceding with a `--`.

* Arguments are **required** and provided as positional arguments.

One could argue (in fact, I am!) that the delivery mechanism (positional or keyword) can be determined by the function signature.

Consider the following function signatures:

.. code-block:: python

   def pos_or_keyword(a, b):
       pass


   def pos_only(a, b, /):
       pass


   def keyword_only(*, a, b=2):
       pass


   def mixture(a, /, b, *, c=3):
       pass

If you aren't familiar with these declarations, refer to the official PEP570_, or `a more user-friendly tutorial`_.

From these function signatures, we can deduce:

1. Which parameters are position-only, keyword-only, or both.

2. Which parameters are required, by their lack of defaults.

Because of these builtin python mechanisms, Cyclopts just has a single ``Parameter`` class used for providing additional parameter metadata.

I believe that Typer's separate ``Argument`` and ``Option`` classes are a relic from when they must be supplied as a parameter's proxy default value.

.. code-block:: python

   app = typer.Typer()


   @app.command()
   def foo(a=Argument(), b=Option(default=2)):
       pass

When used as such, we lose the ability to define the function signature with position-only or keyword-only markers.
We also lose the ability to directly inspect which parameters are optional by having "real" defaults and which ones are required.

.. _PEP570: https://peps.python.org/pep-0570/
.. _a more user-friendly tutorial: https://realpython.com/lessons/positional-only-arguments/
