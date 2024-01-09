========
Commands
========

For a given Cyclopts application, there are 2 primary registering actions:

1. :meth:`@app.default <cyclopts.App.default>` -
   Registers an action for when no valid command is provided by the CLI.
   This was previously demonstrated in :ref:`Getting Started`.

   A sub-app **cannot** be registered with :meth:`@app.default <cyclopts.App.default>`.

   The default :meth:`app.default <cyclopts.App.default>` handler runs :meth:`app.help_print <cyclopts.App.help_print>`.

2. :meth:`@app.command <cyclopts.App.command>` - Registers a function or :class:`.App` as a command.
   Commands require explicit CLI invocation.

This section will detail how to use the ``@app.command`` decorator.

---------------------
Registering a Command
---------------------
The :meth:`@app.command <cyclopts.App.command>` decorator adds a command to a Cyclopts application.
The registered command can either be a function, or another Cyclopts application.


.. code-block:: python

   from cyclopts import App

   app = App()
   sub_app = App(name="foo")
   app.command(sub_app)  # Registers sub_app to command "foo"
   # Or, as a one-liner:  app.command(sub_app := App(name="foo"))


   @app.command
   def fizz(n: int):
       print(f"FIZZ: {n}")


   @sub_app.command
   def bar(n: int):
       print(f"BAR: {n}")


   # Alternatively, access subapps from app like a dictionary.
   @app["foo"].command
   def baz(n: int):
       print(f"BAZ: {n}")


   app()

.. code-block:: console

   $ my-script fizz 3
   FIZZ: 3

   $ my-script foo bar 4
   BAR: 4

   $ my-script foo baz 5
   BAZ: 5

.. _Changing Name:

-------------
Changing Name
-------------
By default, a command is registered to the function name with underscores replaced with hyphens.
Any leading or trailing underscore/hyphens will also be stripped.
For example, ``def _foo_bar()`` will become the command ``foo-bar``.

The name can be manually changed in the :meth:`@app.command <cyclopts.App.command>` decorator:

.. code-block:: python

   @app.command(name="bar")
   def foo():
       print("Hello World!")


   app(["bar"])
   # Hello World!

-----------
Adding Help
-----------
There are a few ways to adding a help string to a command:

1. If the function has a docstring, the short description will be
   used as the help string for the command.

2. If the registered command is a sub app, the sub app's ``help`` field
   will be used.

   .. code-block:: python

      sub_app = App(name="foo", help="Help text for foo.")
      app.command(sub_app)

3. The ``help`` field of ``@app.command``. If provided, the docstring or subapp help field will **not** be used.

.. code-block

.. code-block:: console

   app = cyclopts.App()


   @app.command
   def foo():
       """Help string for foo."""
       pass


   @app.command(help="Help string for bar.")
   def bar():
       pass

   $ my-script --help
   ╭─ Commands ─────────────────────╮
   │ foo  Help string for foo.      │
   │ bar  Help string for bar.      │
   ╰────────────────────────────────╯

--------------------------
Decorated Function Details
--------------------------
Cyclopts **does not modify the decorated function in any way**.
The returned function is the exact same function being decorated.
There is minimal overhead, and the function can be used exactly as if it were not decorated by Cyclopts.
