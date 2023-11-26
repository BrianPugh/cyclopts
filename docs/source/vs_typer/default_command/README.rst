.. _Typer Default Command:

===============
Default Command
===============
Typer has an annoying design quirk where if you register a single command, it **won't** expect you to provide the command name in the CLI.

For example:


.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo():
       print("FOO")


   typer_app([], standalone_mode=False)
   # FOO
   typer_app(["foo"], standalone_mode=False)
   # raises exception: Got unexpected extra argument (foo)

Once you add a second command, then the CLI expects the command to be provided:

.. code-block:: python

   typer_app(["foo"], standalone_mode=False)
   # FOO
   typer_app(["bar"], standalone_mode=False)
   # BAR

`This behavior catches many people off guard.`_
If you want a single command, you have to unintuitively declare a ``callback``.
Github user `ajlive's callback solution`_ is copied below.

.. code-block:: python

   @app.callback()
   def dummy_to_force_subcommand() -> None:
       """
       This function exists because Typer won't let you force a single subcommand.
       Since we know we will add other subcommands in the future and don't want to
       break the interface, we have to use this workaround.

       Delete this when a second subcommand is added.
       """
       pass

To avoid this confusion, Cyclopts has two ways of registering a function:

1. ``app.command`` - Register a function as a command.
2. ``app.default`` - Invoked if no registered command can be parsed from the CLI.

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.command
   def foo():
       print("FOO")


   cyclopts_app(["foo"])
   # FOO

.. _This behavior catches many people off guard.: https://github.com/tiangolo/typer/issues/315
.. _ajlive's callback solution: https://github.com/tiangolo/typer/issues/315#issuecomment-1142593959
