.. _Command Chaining:

================
Command Chaining
================

Cyclopts does not natively support command chaining, but the :ref:`Meta App` makes it easy to implement yourself.

With Delimiter
==============

In this example, we use a special delimiter token (e.g. ``"AND"``) to separate commands.

.. code-block:: python

   import itertools
   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   @app.command
   def foo(val: int):
       print(f"FOO {val=}")

   @app.command
   def bar(flag: bool):
       print(f"BAR {flag=}")

   @app.meta.default
   def main(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       # tokens is ``["foo", "123", "AND", "foo", "456", "AND", "bar", "--flag"]``
       delimiter = "AND"

       groups = [list(group) for key, group in itertools.groupby(tokens, lambda x: x == delimiter) if not key] or [[]]
       # groups is ``[['foo', '123'], ['foo', '456'], ['bar', '--flag']]``

       for group in groups:
           # Execute each group
           app(group)

   if __name__ == "__main__":
       app.meta(["foo", "123", "AND", "foo", "456", "AND", "bar", "--flag"])
       # FOO val=123
       # FOO val=456
       # BAR flag=True

Without Delimiter
=================

If your command names and argument values never collide, you can split tokens at recognized command names without requiring a delimiter.

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()


   def split_commands(app, tokens):
       """Split tokens into groups, starting a new group at each known command name."""
       groups = []
       for token in tokens:
           if token in app:
               groups.append([])
           if groups:
               groups[-1].append(token)
       return groups or [[]]


   @app.command
   def foo(val: int):
       print(f"FOO {val=}")

   @app.command
   def bar(flag: bool):
       print(f"BAR {flag=}")

   @app.meta.default
   def main(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       for group in split_commands(app, tokens):
           app(group)

   if __name__ == "__main__":
       app.meta(["foo", "123", "bar", "--flag"])
       # FOO val=123
       # BAR flag=True

.. warning::

   If an argument value matches a command name, it will be incorrectly treated as a new command boundary.
   Use the delimiter approach if this could be an issue for your application.
