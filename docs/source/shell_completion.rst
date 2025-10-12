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

- **Zsh**: ``~/.zsh/completions/_<app_name>``
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
