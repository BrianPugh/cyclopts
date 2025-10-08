================
Shell Completion
================

Cyclopts provides shell completion (tab completion) for bash, zsh, and fish shells.

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
