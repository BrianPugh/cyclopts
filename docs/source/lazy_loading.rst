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

Lazy commands are resolved/imported in these situations:

- **Command Execution** - When the user runs that specific command
- **Help Generation** - When displaying help that includes the command
- **Direct Access** - When accessing via ``app["command_name"]``

In order to benefit from lazy loading, you have to make sure that the files are not imported by other means when your CLI starts up.

------------------
Import Path Format
------------------

The import path string has two parts separated by a colon (``:``):

**Module Path** (before the ``:``)
  The Python **module** to import, using dot notation (e.g., ``myapp.commands.users``).

**Attribute Name** (after the ``:``)
  The function or App to get from the module using :func:`getattr`.

Examples:

.. code-block:: python

   # Simple function in a module
   app.command("myapp.commands:create_user")

   # Nested module path
   app.command("myapp.admin.database.operations:migrate")

   # Import an App instance, exposed to the CLI as "admin"
   app.command("myapp.admin:admin_app", name="admin")

.. note::
   The attribute name (after ``:``) is the **actual Python name**, not the CLI command name.
   Use the ``name`` parameter to specify the CLI command name.

----------------------
Name vs Function Name
----------------------

The ``name`` parameter specifies **how the command appears in the CLI**, while the import path
specifies **what code to execute**. They can be completely different:

.. code-block:: python

   from cyclopts import App

   user_app = App(name="user")

   # Function name: "list_users"
   # CLI command name: "list"
   user_app.command("myapp.commands.users:list_users", name="list")

   # Function name: "delete"
   # CLI command name: "remove"
   user_app.command("myapp.commands.users:delete", name="remove")

.. code-block:: console

   $ myapp user list --limit 10
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

To catch import errors early, you can access the command during testing:

.. code-block:: python

   import pytest
   from cyclopts import App

   def test_lazy_commands_are_importable():
       app = App()
       app.command("myapp.commands:create")

       # This will trigger the import and fail if path is wrong
       resolved = app["create"]
       assert resolved is not None
