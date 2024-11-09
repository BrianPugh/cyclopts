.. _Args & Kwargs:

=============
Args & Kwargs
=============

In python, a function can consume a variable number of positional and keyword arguments:

.. code-block:: python

   def foo(normal_required_variable, *args, **kwargs):
       pass

There is **nothing special** about the names ``args`` and ``kwargs``;
the functionality is derived from the leading ``*`` and ``**``.
``args`` and ``kwargs`` are the defacto standard names for these variables.
In this document, we'll usually just refer to them as ``*args`` and ``**kwargs``.

Cyclopts commands may consume a variable number of positional and keyword arguments.
The priority ruleset is as follows:

1. ``--keyword`` CLI arguments first get matched to normal variable parameters.

2. Unmatched keywords get consumed by ``**kwargs``, if specified.

3. All remaining tokens get consumed by ``*args``, if specified.
   A prevalant use-case is in a typical :ref:`Meta App`.

.. _Args & Kwargs - Args:

--------------------------
Args (Variable Positional)
--------------------------
A variable number of positional arguments consume all remaining positional arguments from the command-line.
Individual elements are converted to the annotated type.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command
   def foo(name: str, *favorite_numbers: int):
       print(f"{name}'s favorite numbers are: {favorite_numbers}")

   app()


.. code-block:: console

   $ my-script foo Brian
   Brian's favorite numbers are: ()

   $ my-script foo Brian 777
   Brian's favorite numbers are: (777,)

   $ my-script foo Brian 777 2
   Brian's favorite numbers are: (777, 2)

.. _Args & Kwargs - Kwargs:

--------------------------
Kwargs (Variable Keywords)
--------------------------
A variable number of keyword arguments consume all remaining CLI tokens starting with ``--``.
Individual values are converted to the annotated type.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command
   def add(**country_to_capitols):
       for country, capitol in country_to_capitols.items():
           print(f"Adding {country} with capitol {capitol}.")

   app()


.. code-block:: console

   $ my-script add --united-states="Washington, D.C." --canada=Ottawa
   Adding united-states with capitol Washington, D.C..
   Adding canada with capitol Ottawa.
