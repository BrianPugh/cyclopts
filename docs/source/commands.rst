========
Commands
========

For a given cyclopts application, there are 2 primary registering actions:

1. :meth:`@app.command <cyclopts.App.command>` - Registers a function or :class:`App <cyclopts.App>` as a command.
   Commands require explicit CLI invocation.

2. :meth:`@app.default <cyclopts.App.default>` - Registers a function when no valid command is provided by the CLI.


----------------
Register Command
----------------
The :meth:`app.command <cyclopts.App.command>` method adds a command to a Cyclopts application.
The registered command can either be a function, or another Cyclopts application.


.. code-block:: python

   from cyclopts import App

   app = App()
   sub_app = App(name="foo")
   app.command(sub_app)


   @sub_app.command
   def bar(n: int):
       print(f"BAR: {n}")


   @sub_app.command
   def baz(n: int):
       print(f"BAZ: {n}")


   app()

.. code-block:: console

   $ python scratch2.py foo bar 5
   BAR: 5
   $ python scratch2.py foo baz 5
   BAZ: 5


----------------
Register Default
----------------
You **cannot** register a subapp via :meth:`app.default <cyclopts.App.default>`.
The default :meth:`app.default <cyclopts.App.default>` handler runs :meth:`app.help_print <cyclopts.App.help_print>`.

-------------
Changing Name
-------------
By default, a command is registered to the function name with underscores replaced with hyphens.
For example, ``def foo_bar()`` will become the command ``foo-bar``.
The name can be manually in the :meth:`command <cyclopts.App.command>` decorator by setting the ``name`` parameter.

.. code-block:: python

   @app.command(name="bar")
   def foo():
       print("Hello World!")


   app(["bar"])
   # Hello World!

-----------
Adding Help
-----------
There are two ways to add help.
Docstring.
field.

--------------------------
Decorated Function Details
--------------------------
Cyclopts **does not modify the decorated function in any way**.
When decorated with :meth:`@app.default <cyclopts.App.default>`` or :meth:`@app.command <cyclopts.App.command>`, the function is only registered
to an internal dictionary.
There is minimal overhead, and the function can be used exactly as if it were not decorated by Cyclopts.
