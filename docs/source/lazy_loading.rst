.. _Lazy Loading:

============
Lazy Loading
============

Lazy loading allows you to register commands **using import path strings instead of direct function references**.
This defers importing command modules until they are actually executed, which could significantly improve CLI startup time for large applications that have expensive per-command imports.

-----------
Basic Usage
-----------

Instead of importing and registering a function directly:

.. code-block:: python

   from cyclopts import App
   from myapp.commands.users import create, delete, list_users  # Imported immediately

   app = App()
   user_app = App(name="user")

   user_app.command(create)
   user_app.command(delete)
   user_app.command(list_users, name="list")

   app.command(user_app)

Use an import path string:

.. code-block:: python

   from cyclopts import App

   app = App()
   user_app = App(name="user")

   # No imports! Modules loaded only when commands execute
   user_app.command("myapp.commands.users:create")
   user_app.command("myapp.commands.users:delete")
   user_app.command("myapp.commands.users:list_users", name="list")

   app.command(user_app)

The import path format is ``"module.path:function_name"``, similar to setuptools entry points.

Lazy commands are resolved/imported when:

- the user runs that specific command.
- python code directly accesses the command; e.g. ``app["command_name"]``.

Notably, **help generation does not trigger imports**. Cyclopts uses AST-based docstring extraction
to display help for lazy commands without importing their modules (see :ref:`Help Text and Docstrings`).

In order to benefit from lazy loading, you have to make sure that the files are **not imported by other means** when your CLI starts up.

------------------
Import Path Format
------------------

The import path string has two parts separated by a colon (``:``):

**Module Path** (before the ``:``)
  The Python **module** to import, using dot notation (e.g., ``myapp.commands.users``).

**Attribute Name** (after the ``:``)
  The function or :class:`.App` to get from the module using :func:`getattr`.

Examples:

.. code-block:: python

   # Simple function in a module
   app.command("myapp.commands:create_user")

   # Import an App instance, exposed to the CLI as "admin"
   app.command("myapp.admin:admin_app", name="admin")

.. note::
   The attribute name (after ``:``) is the **actual Python name**, not the CLI command name.
   Use the ``name`` parameter to specify a different CLI command name.

----------------------
Name vs Function Name
----------------------

The ``name`` parameter specifies **how the command appears in the CLI**, while the import path
specifies **what code to execute**. They can be completely different:

.. code-block:: python

   from cyclopts import App

   user_app = App(name="user")

   # Function name: "list_users"
   # CLI command name: "list-users"
   user_app.command("myapp.commands.users:list_users")

   # Function name: "delete"
   # CLI command name: "remove"
   user_app.command("myapp.commands.users:delete", name="remove")

.. code-block:: console

   $ myapp user list-users --limit 10
   # Imports and runs myapp.commands.users:list_users

   $ myapp user remove --username alice
   # Imports and runs myapp.commands.users:delete

If ``name`` is not specified, Cyclopts derives it from the function name with
:attr:`App.name_transform <cyclopts.App.name_transform>` applied (typically converting underscores to hyphens).

--------------
Error Handling
--------------

If an import path/configuration is invalid, the error occurs **when the command is executed**, not when it's registered:

.. code-block:: python

   from cyclopts import App

   app = App()

   # This won't error immediately - registration succeeds
   app.command("nonexistent.module:func")

   app()

.. code-block:: console

   $ myapp func
   # Now the error occurs:
   ImportError: Cannot import module 'nonexistent.module'

To catch import errors early, you can use :meth:`~cyclopts.App.resolve_commands` during testing:

.. code-block:: python

   from myapp import app  # Your app with lazy commands

   def test_lazy_commands_are_valid():
       # This resolves all direct lazy subcommands and will fail if any path is wrong
       app.resolve_commands()

-----------------------
Groups and Lazy Loading
-----------------------

.. tip:: **TL;DR:** Define :class:`~cyclopts.Group` objects used by commands in your main CLI module, NOT in lazy-loaded modules.

:class:`.Group` objects defined in **unresolved lazy modules** won't be available
until those modules are **explicitly imported**. To avoid this, define :class:`~cyclopts.Group` objects in non-lazy modules (particularly important for **command groups**).

.. code-block:: python

   # myapp/cli.py (always imported)
   from cyclopts import App, Group

   # Define Group objects here
   admin_group = Group("Admin Commands", validator=require_admin_role)
   db_group = Group("Database", default_parameter=Parameter(envvar_prefix="DB_"))

   app = App()

   # Lazy commands can reference the Group objects
   app.command("myapp.admin:create_user", group=admin_group)
   app.command("myapp.admin:delete_user", group=admin_group)
   app.command("myapp.db:migrate", group=db_group)

.. code-block:: python

   # myapp/admin.py (lazy-loaded)
   from cyclopts import App, Group

   # BAD: This Group won't be available to other commands until this module is imported
   admin_group = Group("Admin Commands", validator=require_admin_role)

   def create_user():
       ...

If you reference a group by string (e.g., ``group="Admin Commands"``) and the :class:`~cyclopts.Group` object
with that name is only defined in an unresolved lazy module, the group won't be available
until that lazy module is imported. This means that:

- Validators defined on the lazy-loaded :class:`~cyclopts.Group` won't be applied to commands in other modules.
- :attr:`.Group.default_parameter` and other settings won't be inherited by commands **referencing the group by string**.

Once the lazy module is imported (e.g., by executing one of its commands), the :class:`~cyclopts.Group` object
becomes available and subsequent operations will use it correctly. However, in conjunction with lazy-loading, this is just unnecessary complexity and should be avoided.

.. _Help Text and Docstrings:

------------------------
Help Text and Docstrings
------------------------

For lazy commands, Cyclopts extracts docstrings directly from the source file using Python's
:mod:`ast` module, **without importing the module**. This preserves the startup time benefits
of lazy loading even when displaying help.

.. code-block:: python

   # myapp/commands/heavy.py
   import tensorflow  # Expensive import!

   def train_model(epochs: int = 10):
       """Train the machine learning model.

       This trains using the configured dataset and hyperparameters.
       """
       ...

.. code-block:: python

   # myapp/cli.py
   from cyclopts import App

   app = App()
   app.command("myapp.commands.heavy:train_model", name="train")

.. code-block:: console

   $ myapp --help
   Usage: myapp COMMAND

   Commands:
     train  Train the machine learning model.

   # tensorflow was NOT imported!

The docstring's short description (first paragraph) is extracted and displayed in help output.

Explicit Help Override
======================

If AST-based extraction isn't possible (e.g., dynamically created modules, compiled extensions,
or modules without source files), you can provide help text explicitly:

.. code-block:: python

   # For commands where AST extraction would fail
   app.command("compiled_module:func", name="process", help="Process data using compiled code.")

The ``help`` parameter takes precedence over docstring extraction when provided.
