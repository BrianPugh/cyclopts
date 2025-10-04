================
Shell Completion
================

Cyclopts provides shell completion (tab completion) for bash, zsh, and fish shells. This feature allows users to press TAB to autocomplete commands, options, and arguments in their terminal.

Installation
============

There are two ways to enable shell completion:

1. **Programmatic Installation (Recommended)**

   Add completion installation to your CLI application using :meth:`App.register_install_completion`:

   .. code-block:: python

      from cyclopts import App

      app = App(name="myapp")
      app.register_install_completion()

      # Your commands here...

      if __name__ == "__main__":
          app()

   Users can then install completion by running:

   .. code-block:: bash

      myapp --install-completion

   The installation script will auto-detect the current shell and install to the appropriate location.

2. **Manual Installation**

   For programmatic control, use :meth:`App.install_completion` directly:

   .. code-block:: python

      from cyclopts import App

      app = App(name="myapp")

      # Install for current shell
      install_path, shell = app.install_completion()
      print(f"Installed {shell} completion to {install_path}")

      # Install for specific shell
      install_path, shell = app.install_completion(shell="zsh")

      # Install to custom location
      from pathlib import Path
      install_path, shell = app.install_completion(
          shell="bash",
          output=Path("/custom/path/completion.sh")
      )

Script Generation
=================

To generate a completion script without installing it, use :meth:`App.generate_completion`:

.. code-block:: python

   from cyclopts import App

   app = App(name="myapp")

   # Generate zsh completion script
   script = app.generate_completion(shell="zsh")
   print(script)

Default Installation Paths
===========================

When no custom output path is specified, completion scripts are installed to:

**Zsh**
  - Path: ``~/.zsh/completions/_<app_name>``
  - Note: Ensure ``~/.zsh/completions`` is in your ``$fpath``

**Bash**
  - Path: ``~/.bash_completion``

**Fish**
  - Path: ``~/.config/fish/completions/<app_name>.fish``

Shell Configuration
===================

After installation, you may need to configure your shell:

Zsh
---

Add to your ``~/.zshrc`` or ``~/.zprofile``:

.. code-block:: bash

   fpath=(~/.zsh/completions $fpath)
   autoload -Uz compinit && compinit

Then restart your shell:

.. code-block:: bash

   exec zsh

Bash
----

Add to your ``~/.bashrc``:

.. code-block:: bash

   [ -f ~/.bash_completion ] && source ~/.bash_completion

Then reload your configuration:

.. code-block:: bash

   source ~/.bashrc

Fish
----

Fish automatically loads completions from ``~/.config/fish/completions/``. Just restart your shell:

.. code-block:: bash

   source ~/.config/fish/config.fish

API Reference
=============

.. automethod:: cyclopts.App.generate_completion
   :noindex:

.. automethod:: cyclopts.App.install_completion
   :noindex:

.. automethod:: cyclopts.App.register_install_completion
   :noindex:
