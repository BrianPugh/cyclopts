.. _Commands:

========
Commands
========

There are two different ways of registering functions:

1. :meth:`app.default <cyclopts.App.default>` -
   Registers an action for when no registered command is provided.
   This was previously demonstrated in :ref:`Getting Started`.

   A sub-app **cannot** be registered with :meth:`app.default <cyclopts.App.default>`.
   If no ``default`` command is registered, Cyclopts will display the help-page.

2. :meth:`app.command <cyclopts.App.command>` - Registers a function or :class:`.App` as a command.

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

We can now control which command runs from the CLI:

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
The :meth:`app.command <cyclopts.App.command>` method can also register another Cyclopts :class:`.App` as a command.

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

   $ my-script foo baz 4
   BAZ: 4

The subcommand may have their own registered ``default`` action.
Cyclopts's command structure is fully recursive.

.. _Command Changing Name:

---------------------
Changing Command Name
---------------------
By default, commands are registered to the python function's name with underscores replaced with hyphens.
Any leading or trailing underscores will be stripped.
For example, the function ``_foo_bar()`` will become the command ``foo-bar``.
This renaming is done because CLI programs generally tend to use hyphens instead of underscores.
The name transform can be configured by :attr:`App.name_transform <cyclopts.App.name_transform>`.
For example, to make CLI command names be identical to their python function name counterparts, we can configure :class:`~cyclopts.App` as follows:

.. code-block:: python

   from cyclopts import App

   app = App(name_transform=lambda s: s)

   @app.command
   def foo_bar():  # will now be "foo_bar" instead of "foo-bar"
       print("running function foo_bar")

   app()

.. code-block:: console

   $ my-script foo_bar
   running function foo_bar


Alternatively, the name can be **manually** changed in the :meth:`@app.command <cyclopts.App.command>` decorator.
Manually set names are **not** subject to :attr:`App.name_transform <cyclopts.App.name_transform>`.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command(name="bar")
   def foo():  # function name will NOT be used.
       print("Hello World!")

   app()

.. code-block:: console

   $ my-script bar
   Hello World!

Finally, if you would like to register an **additional** name to the Cyclopts-derived names, you can set an :attr:`~.App.alias`:

.. code-block:: python

    from cyclopts import App

    app = App()

    @app.command(alias="bar")
    def foo():  # both "foo" and "bar" will trigger this function.
        print("Running foo.")

    app()

.. code-block:: console

    $ my-script foo
    Running bar.

    $ my-script bar
    Running bar.

-----------
Adding Help
-----------
There are a few ways to add a help string to a command:

1. If the function has a docstring, the **short description** will be used as the help string for the command.
   This is generally the preferred method of providing help strings.

2. If the registered command is a sub app, the sub app's :attr:`help <cyclopts.App.help>` field will be used.

   .. code-block:: python

      sub_app = App(name="foo", help="Help text for foo.")
      app.command(sub_app)

3. The :attr:`help <cyclopts.App.help>` field of :meth:`@app.command <cyclopts.App.command>`. If provided, the docstring or subapp help field will **not** be used.

   .. code-block:: python

      from cyclopts import App

      app = App()

      @app.command
      def foo():
          """Help string for foo."""
          pass

      @app.command(help="Help string for bar.")
      def bar():
          """This got overridden."""

      app()

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
Cyclopts also works with **async** commands:

.. code-block:: python

   import asyncio
   from cyclopts import App

   app = App()

   @app.command
   async def foo():
       await asyncio.sleep(10)

   app()

Cyclopts' calling behavior depends on whether or not it's already running in an async context:

* **In a synchronous context**: Creates a new event loop and executes the coroutine, returning the result directly.
* **In an async context**: Returns the coroutine for the caller to await.

This allows the same ``app()`` call to work seamlessly in both contexts:

.. code-block:: python

   # Synchronous normal python - executes immediately
   result = app()  # Runs the async command in a new event loop and returns the result

   # Async context - returns coroutine
   async def main():
       result = await app()  # Returns coroutine that must be awaited

   asyncio.run(main())

--------------------------
Decorated Function Details
--------------------------
Cyclopts **does not modify the decorated function in any way**.
The returned function is the **exact same function** being decorated and can be used exactly as if it were not decorated by Cyclopts.
