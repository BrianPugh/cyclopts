========================
Interactive Shell & Help
========================
Cyclopts has a `builtin interactive shell-like feature <../api.html#cyclopts.App.interactive_shell>`__:

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

Special flags like ``--help`` and ``--version`` work in the shell. Because typing dashes is
awkward at a prompt, the bare words ``help`` and ``version`` are also accepted when they directly
follow a command chain (see ``remap_flags`` on :meth:`.App.interactive_shell`), and the help
screen lists them alongside the other commands. A user-defined ``help`` command, or a command
parameter named ``help``, takes precedence over the remap.

.. code-block:: console

   $ python interactive-shell-demo.py
   Interactive shell. Press Ctrl-D to exit.
   cyclopts> help
   Usage: interactive-shell-demo.py COMMAND

   ╭─ Commands ───────────────────────────────────────────────────╮
   │ bar                  Bar Docstring.                          │
   │ foo                  Foo Docstring.                          │
   │ help (--help, -h)    Display this message and exit.          │
   │ version (--version)  Display application version.            │
   ╰──────────────────────────────────────────────────────────────╯
   cyclopts> foo help
   Usage: interactive-shell-demo.py foo P1

   Foo Docstring.

   ╭─ Parameters ─────────────────────────────────────────────────╮
   │ *  P1 --p1  Foo's first parameter. [required]                │
   ╰──────────────────────────────────────────────────────────────╯
   cyclopts> exit

Type ``q``, ``quit``, or ``exit`` (or press Ctrl-D) to leave the shell. Pass ``history_file`` to
persist command history between sessions.
