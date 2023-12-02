====
Help
====

A help screen is standard for every CLI application.
Cyclopts by-default adds ``--help`` and ``-h`` flags to the application:

.. code-block:: console

   $ my-application --help
   Usage: my-application COMMAND

   My application short description.

   ╭─ Parameters ───────────────────────────────────────────────────────╮
   │ --version      Display application version.                        │
   │ --help     -h  Display this message and exit.                      │
   ╰────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ─────────────────────────────────────────────────────────╮
   │ foo  Foo help string.                                              │
   │ bar  Bar help string.                                              │
   ╰────────────────────────────────────────────────────────────────────╯

Cyclopts derives the components of the help string from a variety of sources.
The source resolution order is as follows (as applicable):

1. The ``help`` field in the :meth:`@app.command <cyclopts.App.command>` decorator.
   When registering an :class:`App <cyclopts.App>` object, supplying ``help`` via the :meth:`@app.command <cyclopts.App.command>` decorator is forbidden to reduce ambiguity and will raise a ``ValueError``.

   .. code-block:: python

      app = cyclopts.App()


      @app.command(help="This is the highest precedence help-string for 'bar'.")
      def bar():
          pass

2. The ``help`` field of :class:`App <cyclopts.App>`.

   .. code-block:: python

      app = cyclopts.App(help="This help string has highest precedence at the app-level.")

      sub_app = cyclopts.App(help="This is the help string for the 'foo' subcommand.")
      app.command(sub_app, name="foo")
      app.command(sub_app, name="foo", help="This is illegal and raises a ValueError.")


3. The ``__doc__`` docstring of the registered :meth:`@app.default <cyclopts.App.default>` command.

   .. code-block:: python

      app = cyclopts.App()
      app.command(cyclopts.App(), name="foo")


      @app.default
      def bar():
          """This is the primary application docstring."""


      @app["foo"].default
      def foo_handler():
          """This will be shown for the "foo" command."""


4. This resolution order, but of the :ref:`Meta App`.

   .. code-block:: python

      app = cyclopts.App()


      @app.meta.default
      def bar():
          """This is the primary application docstring."""


The ``--help`` flags can be changed to different name(s) via the ``help_flags`` parameter.

.. code-block:: python

   app = cyclopts.App(help_flags="--show-help")
   app = cyclopts.App(help_flags=["--send-help", "--send-help-plz", "-h"])

To disable the ``--help`` flag, set ``help_flags`` to an empty string or iterable.

.. code-block:: python

   app = cyclopts.App(help_flags="")
   app = cyclopts.App(help_flags=[])
