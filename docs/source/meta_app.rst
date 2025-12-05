.. _Meta App:

========
Meta App
========
What if you want more control over the application launch process?
Cyclopts provides the option of launching an app from an app; a meta app!

------------
Meta Sub App
------------
Typically, a Cyclopts application is launched by calling the :class:`.App` object:

.. code-block:: python

   from cyclopts import App

   app = App()
   # Register some commands here (not shown)
   app()  # Run the app

To change how the primary app is run, you can use the meta-app feature of Cyclopts.
The meta app is a special :class:`.App` that inherits configuration from its parent
and has its help-page merged with the parent app's help.

.. code-block:: python

   from cyclopts import App, Group, Parameter
   from typing import Annotated

   app = App()
   # Rename the meta's "Parameter" -> "Session Parameters".
   # Set sort_key so it will be drawn higher up the help-page.
   app.meta.group_parameters = Group("Session Parameters", sort_key=0)

   @app.command
   def foo(loops: int):
       for i in range(loops):
           print(f"Looping! {i}")

   @app.meta.default
   def my_app_launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], user: str):
       print(f"Hello {user}")
       app(tokens)

   app.meta()

.. code-block:: console

   $ my-script --user=Bob foo 3
   Hello Bob
   Looping! 0
   Looping! 1
   Looping! 2

The variable positional ``*tokens`` will aggregate all remaining tokens, including those starting with a hyphen (typically options).
We can then pass them along to the primary ``app``.

The ``meta`` app inherits many configuration values from its parent app and is
additionally scanned when generating help screens.
``*tokens`` is annotated with ``show=False`` since we do not want this variable to show up in the help screen.

.. code-block:: console

   $ my-script --help
   Usage: my-script COMMAND

   ╭─ Session Parameters ────────────────────────────────────────────────────╮
   │ *  --user  [required]                                                   │
   ╰─────────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ──────────────────────────────────────────────────────────────╮
   │ foo                                                                     │
   │ --help,-h  Display this message and exit.                               │
   │ --version  Display application version.                                 │
   ╰─────────────────────────────────────────────────────────────────────────╯

-------------
Meta Commands
-------------
If you want a command to circumvent ``my_app_launcher``, add it as you would any other command to the meta app.

.. code-block:: python

   @app.meta.command
   def info():
       print("CLI didn't have to provide --user to call this.")

.. code-block:: console

   $ my-script info
   CLI didn't have to provide --user to call this.

   $ my-script --help
   Usage: my-script COMMAND

   ╭─ Session Parameters ────────────────────────────────────────────────────╮
   │ *  --user  [required]                                                   │
   ╰─────────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ──────────────────────────────────────────────────────────────╮
   │ foo                                                                     │
   │ info                                                                    │
   │ --help,-h  Display this message and exit.                               │
   │ --version  Display application version.                                 │
   ╰─────────────────────────────────────────────────────────────────────────╯

Just like a standard application, the parsed ``command`` executes instead of ``default``.

-------------------------
Custom Command Invocation
-------------------------
The core logic of :meth:`.App.__call__` method is the following:

.. code-block:: python

    def __call__(self, tokens=None, **kwargs):
        command, bound, ignored = self.parse_args(tokens, **kwargs)
        return command(*bound.args, **bound.kwargs)

Knowing this, we can easily customize how we actually invoke actions with Cyclopts.
Let's imagine that we want to instantiate an object, ``User`` in our meta app, and pass it to subsequent commands that need it.
This might be useful to share an expensive-to-create object amongst commands in a single session; see :ref:`Command Chaining`.

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   class User:
       def __init__(self, name):
           self.name = name

   @app.command
   def create(
       age: int,
       *,
       user_obj: Annotated[User, Parameter(parse=False)],
   ):
       print(f"Creating user {user_obj.name} with age {age}.")

   @app.meta.default
   def launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], user: str):
       additional_kwargs = {}
       command, bound, ignored = app.parse_args(tokens)
       # "ignored" is a dict mapping python-variable-name to it's type annotation for parameters with "parse=False".
       if "user_obj" in ignored:
           # 'ignored["user_obj"]' is the class "User"
           additional_kwargs["user_obj"] = ignored["user_obj"](user)
       return command(*bound.args, **bound.kwargs, **additional_kwargs)

   if __name__ == "__main__":
       app.meta()

.. code-block:: console

   $ my-script create --user Alice 30
   Creating user Alice with age 30.

The ``parse=False`` configuration tells Cyclopts to not try and bind arguments to this parameter.
Cyclopts will pass it along to ``ignored`` to make custom meta-app logic easier.
The annotated parameter **must** be a keyword-only parameter.

.. tip::

   For app-wide control over which parameters are parsed, :attr:`~.Parameter.parse` can also accept a **regex pattern**.
   This can be useful for automatically skipping all "private" parameters (e.g., those prefixed with ``_``) with the regex pattern ``"^(?!_)"``.
   See :ref:`Skipping Private Parameters` for details.
