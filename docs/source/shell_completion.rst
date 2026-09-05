================
Shell Completion
================

Cyclopts provides shell completion (tab completion) for bash, zsh, and fish shells.

Development & Standalone Scripts
==================================

Shell completion systems (bash, zsh, fish) can only provide completion for **installed commands** (executables in your ``$PATH``), not for arbitrary Python scripts like ``python myapp.py``. This is a fundamental limitation of how shells work.

To work around this during development, Cyclopts provides a ``cyclopts run`` command that acts as a wrapper:

.. code-block:: console

   $ cyclopts run myapp.py --help
   $ cyclopts run myapp.py:app --verbose

Since ``cyclopts`` itself is an installed command, the shell can provide completion for it. The ``cyclopts run`` command then loads and executes your script, giving you completion for your development scripts without needing to package and install them.

**Script Path Format:**

- ``cyclopts run script.py`` - Auto-detects the App object. If an App object cannot be determined, it will raise an error.
- ``cyclopts run script.py:app`` - Explicitly specifies the App object to run

This is particularly useful during development before packaging your application.

**Virtual Environment Behavior:**

``cyclopts run`` imports your script directly into the **same Python process** (no subprocess is created). This means:

- It uses whatever Python interpreter is currently running ``cyclopts``
- Your script has access to all packages installed in the current environment
- You must install ``cyclopts`` in your project's virtual environment
- To use: activate your venv, then run ``cyclopts run script.py``

.. code-block:: console

   $ source .venv/bin/activate  # or your venv activation method
   $ cyclopts run myapp.py

.. note::
   Completion for your script's commands comes through the ``cyclopts`` CLI completion.
   Install it once with: ``cyclopts --install-completion``

.. warning::
   **Performance:** ``cyclopts run`` uses **dynamic completion**, which imports your script and calls Python on **every tab press**. This can be slow if your script has heavy imports.

   To mitigate slow imports during development, consider using :ref:`Lazy Loading` for your commands. For production or frequent use, install **static completion** using the methods below. Static completion is pre-generated and does not call Python, making it instantaneous.

To install completion specifically for your standalone script (without using ``cyclopts run``), you can use the Manual Installation approach below with your script's App object.

Installation
============

Programmatic Installation (Recommended)
----------------------------------------

Add completion installation to your CLI application using :meth:`App.register_install_completion_command <cyclopts.App.register_install_completion_command>`:

.. code-block:: python

   from cyclopts import App

   app = App(name="myapp")
   app.register_install_completion_command()

   # Your commands here...

   if __name__ == "__main__":
       app()

Users can then install completion by running:

.. code-block:: console

   myapp --install-completion

Manual Installation
-------------------

For programmatic control, use :meth:`App.install_completion <cyclopts.App.install_completion>` directly:

.. code-block:: python

   from cyclopts import App
   from pathlib import Path

   app = App(name="myapp")

   # Install for current shell
   install_path = app.install_completion()
   print(f"Installed completion to {install_path}")

   # Install for specific shell
   install_path = app.install_completion(shell="zsh")

   # Install to custom location
   install_path = app.install_completion(
       shell="bash",
       output=Path("/custom/path/completion.sh"),
   )

Default Installation Paths
---------------------------

- **Zsh**: ``~/.zsh/completions/_cyclopts_<app_name>``
- **Bash**: ``~/.local/share/bash-completion/completions/<app_name>``
- **Fish**: ``~/.config/fish/completions/<app_name>.fish``

Script Generation
=================

To generate a completion script without installing it, use :meth:`App.generate_completion <cyclopts.App.generate_completion>`:

.. code-block:: python

   from cyclopts import App

   app = App(name="myapp")
   script = app.generate_completion(shell="zsh")
   print(script)

Shell Configuration
===================

By default, Cyclopts modifies your shell RC file to enable completion:

- **Zsh**: Adds to ``~/.zshrc``
- **Bash**: Adds to ``~/.bashrc``
- **Fish**: No modification needed (automatically loads from ``~/.config/fish/completions/``)

After installation, restart your shell or source the RC file.

To install without modifying shell RC files, use:

.. code-block:: python

   app.register_install_completion_command(add_to_startup=False)

Custom Completers
=================

Static completion can only offer values that are known when the completion script is generated.
Sometimes, valid values are only known at runtime; for these cases, attach a **completer callback** to a parameter.
The callback is invoked when the user presses ``<TAB>``, enabling **runtime value completion** for bash, zsh, and fish.

.. warning::

   Completing the value of a completer-backed parameter launches your Python program in a fresh process to run the completer. Each such ``<TAB>`` pays interpreter startup plus every import your program performs at module load, *before* the completer callback runs. (Completing command names, option names, and static choices stays entirely in-shell and pays none of this.) Heavy, non-lazy top-level imports (``numpy``, ``pandas``, ``torch``, ...) make those completions noticeably sluggish.

   To keep completion responsive, avoid heavy module-level imports, import expensive dependencies lazily inside the functions that use them, and use :ref:`Lazy Loading` for commands with heavy dependencies.

.. note::

   Runtime value completion, like static completion, only works for installed commands. Shells can only complete executables found in ``$PATH``, so your application must be installed as a command before runtime completion will function.

Basic Usage
-----------

A completer is a callable that accepts a single :class:`~cyclopts.completion.CompletionContext` argument. Use ``ctx.incomplete`` to get the partial word the user has typed, and return either a single string, or an iterable of strings and/or ``(value, description)`` tuples:

.. code-block:: python

   from typing import Annotated

   from cyclopts import App, Parameter

   app = App(name="deployer")

   USERS = ["alice", "bob", "carol"]


   def complete_user(ctx):
       return [u for u in USERS if u.startswith(ctx.incomplete)]


   @app.command
   def grant(user: Annotated[str, Parameter(completer=complete_user)]): ...


   app()

When the user types ``deployer grant al<TAB>``, Cyclopts calls ``complete_user`` with ``ctx.incomplete == "al"`` and offers ``alice``. Returning a plain string is also allowed, which is convenient when the completer resolves to exactly one value.

Descriptions
------------

To display descriptions alongside completions, return ``(value, description)`` tuples. zsh and fish render these in the completion menu; bash shows the values only.

.. code-block:: python

   def complete_environment(ctx):
       return [("dev", "Development"), ("prod", "Production")]

Dependent Completions
---------------------

Often the valid values for a parameter depend on another parameter already supplied on the command line. Access those values through the :class:`~cyclopts.completion.CompletionContext` by indexing with the option name (``ctx["--region"]``), its bare name (``ctx["region"]``), or the Python field name. The returned object exposes:

- ``.value`` -- the best-effort coerced Python value. Sourced like a real invocation: CLI tokens, then the parameter's ``env_var``, then config sources, then its default (:obj:`~cyclopts.UNSET` if none of those apply or coercion fails).
- ``.raw`` -- the raw typed string, or :obj:`None` if not provided
- ``.provided`` -- :obj:`True` if the argument was explicitly given (CLI, env var, or config)

Use ``ctx.get(name, default)`` to return a default instead of raising for an unknown name.

The following example completes ``--cluster`` based on the already-typed ``--region``:

.. code-block:: python

   from typing import Annotated

   from cyclopts import App, Parameter

   app = App(name="deployer")

   CLUSTERS = {"us-east": ["web-prod", "web-staging"], "us-west": ["data-prod", "data-dev"]}


   def complete_cluster(ctx):
       return CLUSTERS.get(ctx["--region"].value, [])


   @app.command
   def deploy(
       *,
       region: str = "us-east",
       cluster: Annotated[str, Parameter(completer=complete_cluster)] = "",
   ): ...


   app()

See :attr:`.Parameter.completer` and :class:`~cyclopts.completion.CompletionContext` for full API details.

Troubleshooting
---------------

Runtime completion swallows all errors so that a broken completer can never corrupt the shell's candidate list, which also means a misbehaving completer silently produces nothing. To see what the engine is doing, set ``CYCLOPTS_COMPLETION_DEBUG`` and invoke the hidden ``__complete`` command by hand the way the shell does -- passing the words after the program name, with an empty final argument for the word being completed:

.. code-block:: console

   $ CYCLOPTS_COMPLETION_DEBUG=1 deployer __complete deploy --region us-east --cluster ""
   [cyclopts:completion] words=['deploy', '--region', 'us-east', '--cluster', ''] ...
   [cyclopts:completion] resolved command=('deploy',) unused=['--region', 'us-east', '--cluster']
   [cyclopts:completion] active argument='--cluster' completer='complete_cluster'
   [cyclopts:completion] completer returned 1 candidate(s): [('va-1', '')]
   va-1

The diagnostics print to stderr (the candidates still print to stdout), and a completer that raises has its full traceback surfaced instead of swallowed.
