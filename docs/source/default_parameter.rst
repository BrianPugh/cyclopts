.. _Default Parameter:

=================
Default Parameter
=================
The default values of :class:`.Parameter` for an app can be configured via :attr:`.App.default_parameter`.

For example, to disable the :attr:`~.Parameter.negative` flag feature across your entire app:

.. code-block:: python

   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(negative=()))

   @app.command
   def foo(*, flag: bool):
       pass

   app()

Consequently, ``--no-flag`` is no longer an allowed flag:

.. code-block:: console

   $ my-script foo --help
   Usage: my-script foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  --flag  [required]                                         │
   ╰───────────────────────────────────────────────────────────────╯

Explicitly annotating the parameter with  :attr:`~.Parameter.negative` overrides this configuration and works as expected:


.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App(default_parameter=Parameter(negative=()))

   @app.command
   def foo(*, flag: Annotated[bool, Parameter(negative="--anti-flag")]):
       pass

   app()

.. code-block:: console

   $ my-script foo --help
   Usage: my-script foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  --flag --anti-flag  [required]                             │
   ╰───────────────────────────────────────────────────────────────╯

.. _Parameter Resolution Order:

----------------
Resolution Order
----------------

When resolving what the :class:`.Parameter` values for an individual function parameter should be, explicitly set attributes of higher priority :class:`.Parameter` s override lower priority :class:`.Parameter` s. The resolution order is as follows:

1. **Highest Priority:** Parameter-annotated command function signature ``Annotated[..., Parameter()]``.

2. :attr:`.Group.default_parameter` that the **parameter** belongs to.

3. :attr:`.App.default_parameter` of the **app** that registered the command.

4. :attr:`.Group.default_parameter` of the **app** that the function belongs to.

5. **Lowest Priority:** (2-4) recursively of the parenting app call-chain.

Any of Parameter's fields can be set to `None` to revert back to the true-original Cyclopts default.

.. _Skipping Private Parameters:

---------------------------
Skipping Private Parameters
---------------------------

The :attr:`.Parameter.parse` attribute can accept a **regex pattern** to selectively skip parameters based on their name.
This is useful for defining "private" parameters that are externally injected (e.g. a :ref:`Meta App`, dependency-injection framework, etc) rather than parsed from the CLI.

For example, to skip all underscore-prefixed parameters:

.. code-block:: python

   from typing import Annotated
   from cyclopts import App, Parameter

   # The regex "^(?!_)" matches names that do NOT start with underscore.
   app = App(default_parameter=Parameter(parse="^(?!_)"))

   @app.command
   def greet(name: str, *, _db: Database):
       user = _db.get_user(name)
       print(f"Hello {user.full_name}!")

   @app.meta.default
   def launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       # Create shared resources
       db = Database("myapp.db")

       # Parse CLI and get ignored (non-parsed) parameters
       command, bound, ignored = app.parse_args(tokens)

       # Inject ignored parameters
       for name, type_ in ignored.items():
           if type_ is Database:
               bound.kwargs[name] = db

       return command(*bound.args, **bound.kwargs)

   if __name__ == "__main__":
       app.meta()

.. code-block:: console

   $ my-script --help
   Usage: my-script COMMAND

   ╭─ Commands ────────────────────────────────────────────────────╮
   │ greet                                                         │
   │ --help,-h  Display this message and exit.                     │
   │ --version  Display application version.                       │
   ╰───────────────────────────────────────────────────────────────╯

   $ my-script greet --help
   Usage: my-script greet [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  NAME,--name  [required]                                    │
   ╰───────────────────────────────────────────────────────────────╯

Notice that ``_db`` does not appear in the help screen.
Parameters that don't match the regex pattern are added to the ``ignored`` dictionary returned by :meth:`.App.parse_args`, making them available for meta-app injection.

Like all other :class:`Parameter` configurations, explicitly annotating with ``parse=True`` overrides the app-level regex:

.. code-block:: python

   from typing import Annotated
   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(parse="^(?!_)"))

   @app.default
   def main(name: str, *, _verbose: Annotated[bool, Parameter(parse=True)] = False):
       """_verbose IS parsed despite the underscore prefix"""

.. important::

   Parameters that are not parsed (either via ``parse=False`` or a non-matching regex pattern) **must** be either:

   * Keyword-only (defined after ``*`` in the function signature), or
   * Have a default value

   .. code-block:: python

      # Valid: keyword-only parameter
      def main(*, _context: dict): ...

      # Valid: has default value
      def main(_context: dict = None): ...

      # Invalid: positional without default - raises ValueError
      def main(_context: dict): ...
