MkDocs Integration
==================

Cyclopts provides builtin `MkDocs <https://www.mkdocs.org/>`_ support.

.. warning::

   The MkDocs plugin is **experimental** and may have breaking changes in future releases.
   If you encounter any issues or have feedback, please `report them on GitHub <https://github.com/BrianPugh/cyclopts/issues>`_.

.. contents:: Table of Contents
   :local:
   :depth: 2

Quick Start
-----------

1. Install Cyclopts with MkDocs support:

   .. code-block:: bash

      pip install cyclopts[mkdocs]

2. Add the plugin to your MkDocs configuration (``mkdocs.yml``):

   .. code-block:: yaml

      plugins:
        - cyclopts

3. Use the directive in your Markdown files:

   .. code-block:: markdown

      ::: cyclopts
          module: mypackage.cli:app

Directive Usage
---------------

Basic Syntax
~~~~~~~~~~~~

The ``::: cyclopts`` directive uses YAML format and accepts a module path to your Cyclopts ``App`` object:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app

Module Path Formats
~~~~~~~~~~~~~~~~~~~

The directive accepts two module path formats:

1. **Explicit format** (``module.path:app_name``):

   .. code-block:: markdown

      ::: cyclopts
          module: mypackage.cli:app

      ::: cyclopts
          module: myapp.commands:main_app

      ::: cyclopts
          module: src.cli:cli

   This explicitly specifies which ``App`` object to document.

2. **Automatic discovery** (``module.path``):

   .. code-block:: markdown

      ::: cyclopts
          module: mypackage.cli

      ::: cyclopts
          module: myapp.main

   The plugin will search the module for an ``App`` instance, looking for common names like ``app``, ``cli``, or ``main``.

Directive Options
-----------------

The directive supports several options to customize the generated documentation. All options use standard YAML syntax:

``module`` - Module Path (Required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The module path to your Cyclopts App instance:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app

This is the only required option.

``heading_level`` - Heading Level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the starting heading level for the generated documentation (1-6, default: 2):

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       heading_level: 3

This is useful when you need to adjust the heading hierarchy. The default of 2 works well for most cases where the directive is placed under a page title.

``recursive`` - Include Subcommands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control whether to document subcommands recursively (default: true):

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       recursive: false

Set to ``false`` to only document the top-level commands.

``include_hidden`` - Show Hidden Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Include commands marked with ``show=False`` in the documentation:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       include_hidden: true

By default, hidden commands are not included in the generated documentation.

``flatten_commands`` - Generate Flat Command Hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate all commands at the same heading level instead of nested hierarchy:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       flatten_commands: true

This creates distinct, equally-weighted headings for each command and subcommand, making them easier to reference and navigate in the documentation. Without this option, subcommands are nested with incrementing heading levels.

``generate_toc`` - Generate Table of Contents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control whether to generate a table of contents for multi-command apps (default: true):

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       generate_toc: false

This is useful when you want to suppress the automatic table of contents, especially when using multiple directives on the same page or when you have your own navigation structure.

``code_block_title`` - Render Titles as Inline Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Render command titles with inline code formatting (backticks) instead of plain text:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       code_block_title: true

When enabled, command titles are rendered as ``#### `command-name``` instead of ``#### command-name``. This makes command names appear with monospace formatting, which can be useful for certain documentation themes or to make command names stand out visually.

``commands`` - Filter Specific Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Document only specific commands from your CLI application:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       commands:
         - init
         - build
         - deploy

This will only document the specified commands. You can also use nested command paths with dot notation:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       commands:
         - db.migrate
         - db.backup
         - api

Or use inline YAML list syntax:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       commands: [db.migrate, db.backup, api]

- ``db.migrate`` - Documents only the ``migrate`` subcommand under ``db``
- ``db.backup`` - Documents only the ``backup`` subcommand under ``db``
- ``api`` - Documents the ``api`` command and all its subcommands

You can use either underscore or dash notation in command names - they will be normalized automatically.

``exclude_commands`` - Exclude Specific Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exclude specific commands from the documentation:

.. code-block:: markdown

   ::: cyclopts
       module: mypackage.cli:app
       exclude_commands:
         - debug
         - internal-test

This is useful for hiding internal or debug commands from user-facing documentation. Like ``commands``, this also supports nested command paths with dot notation and inline YAML list syntax.

Complete Example
----------------

Here's a complete example showing a CLI application and its MkDocs documentation:

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

MkDocs Configuration (``mkdocs.yml``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   site_name: MyApp Documentation
   site_description: Documentation for MyApp CLI

   theme:
     name: readthedocs

   plugins:
     - search
     - cyclopts

   nav:
     - Home: index.md
     - CLI Reference: cli-reference.md
     - User Guide: guide.md

   markdown_extensions:
     - admonition
     - codehilite
     - toc:
         permalink: true

Documentation File (``docs/cli-reference.md``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   # CLI Reference

   This section documents all available CLI commands.

   ::: cyclopts
       module: myapp.cli:app
       heading_level: 2
       recursive: true

   The above directive will automatically generate documentation for all
   commands, including their parameters, types, defaults, and help text.

Advanced Usage
--------------

Using Flat Command Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you want each command to have its own distinct heading for better navigation:

.. code-block:: markdown

   # CLI Command Reference

   ::: cyclopts
       module: myapp.cli:app
       flatten_commands: true

   This generates all commands at the same heading level (not nested),
   making it easier to navigate and reference specific commands.

Selective Command Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Split your CLI documentation across multiple sections or pages:

.. code-block:: markdown

   ## Database Commands

   The following commands manage database operations:

   ::: cyclopts
       module: myapp.cli:app
       commands: [db]
       recursive: true

   ## API Management

   Commands for controlling the API server:

   ::: cyclopts
       module: myapp.cli:app
       commands: [api]
       recursive: true

   ## Development Tools

   Utilities for development (excluding internal debug commands):

   ::: cyclopts
       module: myapp.cli:app
       commands: [dev]
       exclude_commands: [dev.debug, dev.internal]
       recursive: true

This approach allows you to:

- Organize large CLI applications into logical sections
- Document different command groups on separate pages
- Exclude internal or debug commands from user documentation
- Create targeted documentation for different audiences

See Also
--------

* :doc:`/sphinx_integration` - Sphinx integration (similar functionality)
* :doc:`/help` - Customizing help output
* :doc:`/commands` - Creating commands and subcommands
* :doc:`/parameters` - Parameter types and validation
* `MkDocs Documentation <https://www.mkdocs.org/>`_ - Official MkDocs documentation
