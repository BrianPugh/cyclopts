.. _Default Parameter:

=================
Default Parameter
=================
The default values of :class:`Parameter` for an app can be configured via :attr:`.App.default_parameter`.

For example, to disable the :attr:`~.Parameter.negative` flag feature across your entire app:

.. code-block:: python

   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(negative=()))

   @app.command
   def foo(*, flag: bool):
       pass

   app()

Consequently, ``--no-flag`` is no longer an allowed flag:

.. code-block::

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
