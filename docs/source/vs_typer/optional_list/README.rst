.. _Typer Optional Lists:

==============
Optional Lists
==============
Typer does not handle optional lists particularly well.
In Typer, if a list argument is not provided via the CLI, an empty list is passed to the command by default.
While this might be acceptable in some scenarios, it can be unexpected and differs semantically from the default value.
Because lists are mutable, and `setting mutable defaults is strongly discouraged`_, setting list parameters' default to ``None`` is common practice.
This approach can also help differentiate between the intention of using a default list and explicitly requesting an empty list.

Consider the following Typer example:


.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo(favorite_numbers: Optional[List[int]] = None):
       if favorite_numbers is None:
           favorite_numbers = [1, 2, 3]
       print(f"My favorite numbers are: {favorite_numbers}")


   typer_app(["--favorite-numbers", "100", "--favorite-numbers", "200"], standalone_mode=False)
   # My favorite numbers are: [100, 200]
   typer_app([], standalone_mode=False)
   # My favorite numbers are: []

In this example, we expect the default list ``[1, 2, 3]`` to be used when no input is provided.
However, Typer supplies an empty list instead of ``None``.

Cyclopts has a more intuitive solution.
If no CLI option is specified, no argument is bound, so the parameter's default value ``None`` is used.
If we wish to pass an empty iterable (e.g. :class:`set` or :class:`list`), Cyclopts provides an ``--empty-*`` flag for each iterable parameter.
This feature is configurable via :attr:`.Parameter.negative_iterable`.

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.default()
   def foo(favorite_numbers: Optional[List[int]] = None):
       if favorite_numbers is None:
           favorite_numbers = [1, 2, 3]
       print(f"My favorite numbers are: {favorite_numbers}")


   cyclopts_app(["--favorite-numbers", "100", "--favorite-numbers", "200"])
   # My favorite numbers are: [100, 200]
   cyclopts_app([])
   # My favorite numbers are: [1, 2, 3]
   cyclopts_app(["--empty-favorite-numbers"])
   # My favorite numbers are: []

.. _setting mutable defaults is strongly discouraged: https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
