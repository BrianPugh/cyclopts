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

``:heading-level:`` - Heading Level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the starting heading level for the generated documentation (1-6, default: 2):

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :heading-level: 3

This is useful when you need to adjust the heading hierarchy. The default of 2 works well for most cases where the directive is placed under a page title.

``:max-heading-level:`` - Maximum Heading Level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the maximum heading level to use (1-6, default: 6):

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :max-heading-level: 4

Headings deeper than this level will be capped at this value. This is useful for deeply nested command hierarchies where you want to prevent headings from becoming too small.

``:no-recursive:`` - Exclude Subcommands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Disable recursive documentation of subcommands (by default, subcommands are included):

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :no-recursive:

When this flag is present, only the top-level commands are documented.

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
      :flatten-commands:

This creates distinct, equally-weighted headings for each command and subcommand, making them easier to reference and navigate in the documentation. Without this option, subcommands are nested with incrementing heading levels.

``:code-block-title:`` - Render Titles as Inline Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Render command titles with inline code formatting instead of plain text:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :code-block-title:

When this flag is present, command titles are rendered with monospace formatting, which can be useful for certain documentation themes or to make command names stand out visually.

``:commands:`` - Filter Specific Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Document only specific commands from your CLI application:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :commands: init, build, deploy

This will only document the specified commands. You can also use nested command paths with dot notation:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :commands: db.migrate, db.backup, api

- ``db.migrate`` - Documents only the ``migrate`` subcommand under ``db``
- ``db.backup`` - Documents only the ``backup`` subcommand under ``db``
- ``api`` - Documents the ``api`` command and all its subcommands

You can use either underscore or dash notation in command names - they will be normalized automatically.

``:exclude-commands:`` - Exclude Specific Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exclude specific commands from the documentation:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :exclude-commands: debug, internal-test

This is useful for hiding internal or debug commands from user-facing documentation. Like ``:commands:``, this also supports nested command paths with dot notation.

``:skip-preamble:`` - Skip Description and Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Skip the description and usage sections for the target command when filtering to a single command:

.. code-block:: rst

   .. cyclopts:: mypackage.cli:app
      :commands: deploy
      :skip-preamble:

When you filter to a single command using ``:commands:`` and provide your own section heading in the RST, you may not want the directive to generate the command's description and usage block. Adding ``:skip-preamble:`` suppresses these sections while still generating the command's parameters and subcommands.

This is useful when you want to write your own introduction for a command section:

.. code-block:: rst

   Deployment
   ==========

   Deploy your application to production with these commands.

   .. cyclopts:: mypackage.cli:app
      :commands: deploy
      :skip-preamble:

Without ``:skip-preamble:``, the output would include both your introduction and the command's docstring description, which can be redundant.

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
      :flatten-commands:
      :code-block-title:

   This generates:

   - All commands at the same heading level (not nested)
   - Command titles with monospace formatting
   - Automatic reference labels for cross-linking

   You can then reference specific commands:

   See :ref:`cyclopts-myapp-deploy` for deployment options.
   The :ref:`cyclopts-myapp-init` command sets up your project.

Selective Command Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Split your CLI documentation across multiple sections or pages:

.. code-block:: rst

   Database Commands
   =================

   The following commands manage database operations:

   .. cyclopts:: myapp.cli:app
      :commands: db

   API Management
   ==============

   Commands for controlling the API server:

   .. cyclopts:: myapp.cli:app
      :commands: api

   Development Tools
   =================

   Utilities for development (excluding internal debug commands):

   .. cyclopts:: myapp.cli:app
      :commands: dev
      :exclude-commands: dev.debug, dev.internal

This approach allows you to:

- Organize large CLI applications into logical sections
- Document different command groups on separate pages
- Exclude internal or debug commands from user documentation
- Create targeted documentation for different audiences

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
