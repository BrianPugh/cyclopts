.. _Commands:

========
Commands
========

There are 2 function-registering decorators:

1. :meth:`@app.default <cyclopts.App.default>` -
   Registers an action for when no registered command is provided.
   This was previously demonstrated in :ref:`Getting Started`.

   A sub-app **cannot** be registered with :meth:`@app.default <cyclopts.App.default>`.
   The default :meth:`app.default <cyclopts.App.default>` handler runs :meth:`app.help_print <cyclopts.App.help_print>`.

2. :meth:`@app.command <cyclopts.App.command>` - Registers a function or :class:`.App` as a command.

This section will detail how to use the :meth:`@app.command <cyclopts.App.command>` decorator.

---------------------
Registering a Command
---------------------
The :meth:`@app.command <cyclopts.App.command>` decorator adds a **command** to a Cyclopts application.

.. code-block:: python

   from cyclopts import App

   app = App()


   @app.command
   def fizz(n: int):
       print(f"FIZZ: {n}")


   @app.command
   def buzz(n: int):
       print(f"BUZZ: {n}")


   app()

.. code-block:: console

   $ my-script fizz 3
   FIZZ: 3

   $ my-script buzz 4
   BUZZ: 4

   $ my-script fuzz
   ╭─ Error ────────────────────────────────────────────────────────────────────╮
   │ Unknown command "fuzz". Did you mean "fizz"?                               │
   ╰────────────────────────────────────────────────────────────────────────────╯

------------------------
Registering a SubCommand
------------------------
The :meth:`@app.command <cyclopts.App.command>` method can also register another Cyclopts :class:`.App` as a command.

.. code-block:: python

   from cyclopts import App

   app = App()
   sub_app = App(name="foo")  # "foo" would be a better variable name than "sub_app".
   # "sub_app" in this example emphasizes the name comes from name="foo".
   app.command(sub_app)  # Registers sub_app to command "foo"
   # Or, as a one-liner:  app.command(sub_app := App(name="foo"))


   @sub_app.command
   def bar(n: int):
       print(f"BAR: {n}")


   # Alternatively, access subapps from app like a dictionary.
   @app["foo"].command
   def baz(n: int):
       print(f"BAZ: {n}")


   app()


.. code-block:: console

   $ my-script foo bar 3
   BAR: 3

   $ my-script foo bar 4
   BAZ: 4

The subcommand may have it's own registered ``default`` action.
Cyclopts's command structure is fully recursive.

.. _Command Changing Name:

-------------
Changing Name
-------------
By default, a command is registered to the function name with underscores replaced with hyphens.
Any leading or trailing underscore/hyphens will also be stripped.
For example, the function ``_foo_bar()`` will become the command ``foo-bar``.
This automatic command name transform can be configured by :attr:`App.name_transform <cyclopts.App.name_transform>`.
For example, to make CLI command names be identical to their python function name counterparts, we can configure :class:`~cyclopts.App` as follows:

.. code-block:: python

   app = App(name_transform=lambda s: s)

Alternatively, the name can be manually changed in the :meth:`@app.command <cyclopts.App.command>` decorator.
Manually set names are not subject to :attr:`App.name_transform <cyclopts.App.name_transform>`.

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
   This is generally the preferred method.

2. If the registered command is a sub app, the sub app's :attr:`help <cyclopts.App.help>` field
   will be used.

   .. code-block:: python

      sub_app = App(name="foo", help="Help text for foo.")
      app.command(sub_app)

3. The :attr:`help <cyclopts.App.help>` field of :meth:`@app.command <cyclopts.App.command>`. If provided, the docstring or subapp help field will **not** be used.

.. code-block:: python

   app = cyclopts.App()


   @app.command
   def foo():
       """Help string for foo."""
       pass


   @app.command(help="Help string for bar.")
   def bar():
       """This got overridden."""

.. code-block:: console

   $ my-script --help
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ bar        Help string for bar.                                       │
   │ foo        Help string for foo.                                       │
   │ --help,-h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰───────────────────────────────────────────────────────────────────────╯

-----
Async
-----
Cyclopts works with async functions too, it will run async function with ``asyncio.run``

.. code-block:: python

   app = cyclopts.App()


   @app.command
   async def foo():
       await asyncio.sleep(10)


   app()


--------------------------
Decorated Function Details
--------------------------
Cyclopts **does not modify the decorated function in any way**.
The returned function is the exact same function being decorated.
There is minimal overhead, and the function can be used exactly as if it were not decorated by Cyclopts.
