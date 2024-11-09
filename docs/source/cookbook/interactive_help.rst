========================
Interactive Shell & Help
========================
Cyclopts has a builtin :meth:`interactive shell-like feature<cyclopts.App.interactive_shell>`:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command
   def foo(p1):
       """Foo Docstring.

       Parameters
       ----------
       p1: str
           Foo's first parameter.
       """
       print(f"foo {p1}")

   @app.command
   def bar(p1):
       """Bar Docstring.

       Parameters
       ----------
       p1: str
           Bar's first parameter.
       """
       print(f"bar {p1}")

   # A blocking call, launching an interactive shell.
   app.interactive_shell(prompt="cyclopts> ")


To make the application still work as-expected from the CLI, it is more appropriate to set a command (or ``@app.default``) to launch the shell:

.. code-block:: python

   @app.command
   def shell():
       app.interactive_shell()

   if __name__ == "__main__":
       app()  # Don't call ``app.interactive_shell()`` here.

Special flags like ``--help`` and ``--version`` work in the shell, but could be a bit awkward for the root-help:

.. code-block:: console

   $ python interactive-shell-demo.py
   Interactive shell. Press Ctrl-D to exit.
   cyclopts> --help
   Usage: interactive-shell-demo.py COMMAND

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ --version      Display application version.                   │
   │ --help     -h  Display this message and exit.                 │
   ╰───────────────────────────────────────────────────────────────╯
   ╭─ Commands ────────────────────────────────────────────────────╮
   │ bar  Bar Docstring.                                           │
   │ foo  Foo Docstring.                                           │
   ╰───────────────────────────────────────────────────────────────╯
   cyclopts> foo --help
   Usage: interactive-shell-demo.py foo [ARGS] [OPTIONS]

   Foo Docstring

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  P1,--p1  Foo's first parameter. [required]                 │
   ╰───────────────────────────────────────────────────────────────╯
   cyclopts>

To resolve this, we can explicitly add a ``help`` command:

.. code-block:: python

   @app.command
   def help():
       """Display the help screen."""
       app.help_print()

.. code-block:: console

   $ python interactive-shell-demo.py
   Interactive shell. Press Ctrl-D to exit.
   cyclopts> help
   Usage: interactive-shell-demo.py COMMAND

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ --version      Display application version.                   │
   │ --help     -h  Display this message and exit.                 │
   ╰───────────────────────────────────────────────────────────────╯
   ╭─ Commands ────────────────────────────────────────────────────╮
   │ bar   Bar Docstring.                                          │
   │ foo   Foo Docstring.                                          │
   │ help  Display the help screen.                                │
   ╰───────────────────────────────────────────────────────────────╯
