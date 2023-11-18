================
Command Chaining
================
Command chaining is a complicated topic due to ambiguities when translating CLI parameters into function parameters.
For simple cases, Typer behaves exactly as expected:


.. code-block:: python

   typer_app = typer.Typer(chain=True)


   @typer_app.command()
   def foo():
       print("FOO")


   @typer_app.command()
   def bar():
       print("BAR")


   typer_app(["foo", "foo", "bar"])
   # FOO
   # FOO
   # BAR

However, lets make this command slightly more complicated:

First, with cha

.. code-block:: python

   typer_app = typer.Typer(chain=False)


   @typer_app.command()
   def foo(a: str, flag: bool = False):
       print(f"FOO {a=} {flag=}")


   @typer_app.command()
   def bar():
       print(f"BAR {a=} {flag=}")

Lets first run this code with ``chain=False``.

.. code-block:: console

   $ python main.py foo fizz --flag
   FOO a='fizz' flag=True

And now again, but setting ``chain=True``.

.. code-block:: console

   $ python main.py foo fizz
   FOO a='fizz' flag=False
   $ python main.py foo fizz --flag
   UsageError: No such command '--flag'.
   $ python main.py foo --flag fizz
   FOO a='fizz' flag=True

Typer internally uses Click, and click has the following to say on command chaining:


   When using multi command chaining you can only have one command (the last) use nargs=-1 on an argument. It is also not possible to nest multi commands below chained multicommands. Other than that there are no restrictions on how they work. They can accept options and arguments as normal. The order between options and arguments is limited for chained commands. Currently only --options argument order is allowed.

The ambiguity arises from parsing order-of-operations:

1. The first argument **must** be a command. This is parsed and resolved.
2. Traditionally, the next step is to scan for ``--keyword``'s.
   However, this may accidentally parse parameters from subsequent chained commands.
3.
1. The CLI parser needs to figure out ``--keyword`` and their associated token values.
2.
What happened?

.. code-block:: python
