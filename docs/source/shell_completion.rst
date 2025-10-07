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
      install_path = app.install_completion()
      print(f"Installed completion to {install_path}")

      # Install for specific shell
      install_path = app.install_completion(shell="zsh")

      # Install to custom location
      from pathlib import Path
      install_path = app.install_completion(
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
  - Path: ``~/.local/share/bash-completion/completions/<app_name>``
  - Note: Requires bash-completion v2.8+ for automatic loading

**Fish**
  - Path: ``~/.config/fish/completions/<app_name>.fish``

Shell Configuration
===================

After installation, you may need to configure your shell:

Zsh
---

By default, Cyclopts adds a source line to your ``~/.zshrc`` to ensure completion works out-of-the-box.

After installation, restart your shell:

.. code-block:: bash

   source ~/.zshrc

**Advanced Configuration:**

If you have your ``$fpath`` properly configured for zsh completions, you can install without modifying your ``~/.zshrc``:

.. code-block:: python

   app.register_install_completion(add_to_startup=False)

Then add to your ``~/.zshrc`` or ``~/.zprofile`` if not already present:

.. code-block:: bash

   fpath=(~/.zsh/completions $fpath)
   autoload -Uz compinit && compinit

Bash
----

By default, Cyclopts adds a source line to your ``~/.bashrc`` to ensure completion works out-of-the-box. This approach is compatible with all bash configurations.

After installation, restart your shell:

.. code-block:: bash

   source ~/.bashrc

**Advanced Configuration:**

If you have bash-completion v2.8+ properly configured, completions can auto-load from ``~/.local/share/bash-completion/completions/`` without modifying your ``~/.bashrc``:

.. code-block:: python

   app.register_install_completion(add_to_startup=False)

**Installing bash-completion:**

- **macOS**: ``brew install bash-completion@2``
- **Debian/Ubuntu**: ``apt install bash-completion``
- **Fedora/RHEL**: ``dnf install bash-completion``

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
