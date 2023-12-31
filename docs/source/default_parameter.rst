=================
Default Parameter
=================
The default values of :class:`Parameter` can be configured via :attr:`.App.default_parameter`.

For example, to disable the ``negative`` flag feature across your entire app:

.. code-block:: python

   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(negative=()))


   @app.command
   def foo(*, flag: bool):
       pass


   app()

Consequently, ``--no-flag`` is no longer provided:

.. code-block::

   $ my-script foo --help
   Usage: my-script foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  --flag  [required]                                         │
   ╰───────────────────────────────────────────────────────────────╯

Explicitly setting ``negative`` in the function signature works as expected:


.. code-block::

   @app.command
   def foo(*, flag: Annotated[bool, Parameter(negative="--anti-flag")]):
       pass

.. code-block::

   $ my-script foo --help
   Usage: my-script foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  --flag,--anti-flag  [required]                             │
   ╰───────────────────────────────────────────────────────────────╯

.. _Parameter Resolution Order:

----------------
Resolution Order
----------------

When resolving what the Parameter values for an individual function parameter should be, explicitly set attributes of higher priority Parameters override lower priority Parameters. The resolution order is as follows:

1. *Highest Priority:* Parameter-annotated command function signature ``Annotated[..., Parameter()]``.
2. :class:`App` ``default_parameter`` that registered the command.
3. *Lowest Priority:* :class:`App` parenting app(s)'s ``default_parameter`` (and their parents, and so on).

Any of Parameter's fields can be set to `None` to revert back to the true-original Cyclopts default.
