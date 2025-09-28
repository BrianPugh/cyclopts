Sphinx Integration
==================

Cyclopts provides builtin `Sphinx <https://www.sphinx-doc.org/>`_ support.

.. contents:: Table of Contents
   :local:
   :depth: 2

Quick Start
-----------

1. Add the extension to your Sphinx configuration (``docs/conf.py``):

   .. code-block:: python

      extensions = [
          'cyclopts.sphinx_ext',  # Add this line
          # ... your other extensions
      ]

2. Use the directive in your RST files:

   .. code-block:: rst

      .. cyclopts:: mypackage.cli:app
         :prog: my-cli

Directive Usage
---------------

Basic Syntax
~~~~~~~~~~~~

The ``cyclopts`` directive accepts a module path to your Cyclopts ``App`` object:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app

Module Path Formats
~~~~~~~~~~~~~~~~~~~

The directive accepts two module path formats:

1. **Explicit format** (``module.path:app_name``):

   .. code-block:: rst

      .. cyclopts:: mypackage.cli:app
      .. cyclopts:: myapp.commands:main_app
      .. cyclopts:: src.cli:cli

   This explicitly specifies which ``App`` object to document.

2. **Automatic discovery** (``module.path``):

   .. code-block:: rst

      .. cyclopts:: mypackage.cli
      .. cyclopts:: myapp.main

   The extension will search the module for an ``App`` instance, looking for common names like ``app``, ``cli``, or ``main``.

Directive Options
-----------------

The directive supports several options to customize the generated documentation:

``:prog:`` - Program Name
~~~~~~~~~~~~~~~~~~~~~~~~~~

Override the program name displayed in usage examples:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :prog: awesome-tool

This will show ``awesome-tool`` in usage examples instead of the default program name.

``:heading-level:`` - Heading Level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the starting heading level for the generated documentation (1-6):

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :heading-level: 2

This is useful when embedding CLI docs within a larger document structure.

``:recursive:`` - Include Subcommands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control whether to document subcommands recursively (default: true):

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :recursive: false

Set to ``false`` to only document the top-level commands.

``:include-hidden:`` - Show Hidden Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Include commands marked with ``show=False`` in the documentation:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :include-hidden: true

By default, hidden commands are not included in the generated documentation.

``:flatten-commands:`` - Generate Flat Command Hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate all commands at the same heading level instead of nested hierarchy:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :flatten-commands: true

This creates distinct, equally-weighted headings for each command and subcommand, making them easier to reference and navigate in the documentation. Without this option, subcommands are nested with incrementing heading levels.

``:command-prefix:`` - Add Prefix to Command Headings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add a prefix to all command headings in the generated documentation:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :command-prefix: Command:

This will prefix all command headings with "Command:" (e.g., "Command: deploy", "Command: init"). Useful for consistent formatting or when integrating CLI docs with other content.

Automatic Reference Labels
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Sphinx directive automatically generates RST reference labels for all commands, enabling cross-referencing throughout your documentation. The anchor format is ``cyclopts-{app-name}-{command-path}``, which prevents naming conflicts when documenting multiple CLIs.

For example:
- Root application: ``cyclopts-myapp``
- Subcommand: ``cyclopts-myapp-deploy``
- Nested subcommand: ``cyclopts-myapp-deploy-production``

You can reference these commands elsewhere in your documentation using ``:ref:`cyclopts-myapp-deploy```.

Complete Example
----------------

Here's a complete example showing a CLI application and its Sphinx documentation:

CLI Application (``myapp/cli.py``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from typing import Optional
   from cyclopts import App

   app = App(
       name="myapp",
       help="My awesome CLI application",
       version="1.0.0"
   )

   @app.command
   def init(path: Path = Path("."), template: str = "default"):
       """Initialize a new project.

       Parameters
       ----------
       path : Path
           Directory where the project will be created
       template : str
           Project template to use
       """
       print(f"Initializing project at {path}")

   @app.command
   def build(source: Path, output: Optional[Path] = None, *, minify: bool = False):
       """Build the project.

       Parameters
       ----------
       source : Path
           Source directory
       output : Path, optional
           Output directory (defaults to source/dist)
       minify : bool
           Minify the output files
       """
       output = output or source / "dist"
       print(f"Building from {source} to {output}")

   if __name__ == "__main__":
       app()

Sphinx Configuration (``docs/conf.py``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import sys
   from pathlib import Path

   # Add your package to the path
   sys.path.insert(0, str(Path(__file__).parent.parent))

   # Extensions
   extensions = [
       'cyclopts.sphinx_ext',
       'sphinx.ext.autodoc',  # For API docs
       'sphinx.ext.napoleon',  # For NumPy-style docstrings
   ]

   # Project info
   project = 'MyApp'
   author = 'Your Name'
   version = '1.0.0'

   # HTML theme
   html_theme = 'sphinx_rtd_theme'

Documentation File (``docs/cli.rst``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: rst

   CLI Reference
   =============

   This section documents all available CLI commands.

   .. cyclopts:: myapp.cli:app
      :prog: myapp
      :recursive: true

   The above directive will automatically generate documentation for all
   commands, including their parameters, types, defaults, and help text.

Advanced Usage
--------------

Using Distinct Command Headings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you want each command to have its own distinct heading for better navigation and referencing:

.. code-block:: rst

   CLI Command Reference
   =====================

   .. cyclopts:: myapp.cli:app
      :prog: myapp
      :flatten-commands: true
      :command-prefix: "Command: "

   This generates:

   - All commands at the same heading level (not nested)
   - Each command prefixed with "Command: "
   - Automatic reference labels for cross-linking

   You can then reference specific commands:

   See :ref:`cyclopts-myapp-deploy` for deployment options.
   The :ref:`cyclopts-myapp-init` command sets up your project.

Output Formats
--------------

While the Sphinx directive uses RST internally, you can also generate documentation programmatically in multiple formats:

.. code-block:: python

   from myapp.cli import app

   # Generate reStructuredText
   rst_docs = app.generate_docs(output_format="rst")

   # Generate Markdown
   md_docs = app.generate_docs(output_format="markdown")

   # Generate HTML
   html_docs = app.generate_docs(output_format="html")

This is useful for generating documentation outside of Sphinx, such as for GitHub README files or other documentation systems.

See Also
--------

* :doc:`/help` - Customizing help output
* :doc:`/commands` - Creating commands and subcommands
* :doc:`/parameters` - Parameter types and validation
* `Sphinx Documentation <https://www.sphinx-doc.org/>`_ - Official Sphinx documentation
