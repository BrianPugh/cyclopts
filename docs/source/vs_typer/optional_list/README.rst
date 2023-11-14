==============
Optional Lists
==============
Typer does not handle optional lists well.
If no elements are provided via the CLI, an empty list will be provided to the command.
Frequently, this is fine behavior, but it's unexpected and semantically different.
Because lists are mutable, and `setting mutable defaults is strongly discouraged`_, setting list parameters to ``None`` is common practice.
Setting a list parameter to ``None`` in some may indicate to use a default list instead of an empty list.

Consider the following example:


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

Here, the desired behavior is to have a default list ``favorite_numbers = [1, 2, 3]``.
However, supplying an empty list means to have no ``favorite_numbers``.
Typer supplies an empty list instead of the expected default ``None``.

Cyclopts behaves as expected in this scenario.
By default, a ``--empty-*`` flag is provideded for each iterable (``set``, ``list``) parameter, in case an empty value is actually desired.

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
