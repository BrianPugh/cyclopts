=================
Default Parameter
=================
The default values of :class:`Parameter` can be configured via the ``default_parameter`` field of :class:`App`.

For example, to disable the ``negative`` flag feature across your entire app:

.. code-block:: python

   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(negative=()))


   @app.command
   def foo(*, flag: bool):
       pass


   app()

We can see that ``--no-flag`` is no longer provided:

.. code-block::

   $ my-script foo --help
   Usage: my-script foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  --flag  [required]                                         │
   ╰───────────────────────────────────────────────────────────────╯

However, if we explicitly set ``negative`` in the function signature, it works as expected:


.. code-block::

   @app.command
   def foo(*, flag: Annotated[bool, Parameter(negative="--no-flag")]):
       pass


When resolving what the ``default_parameter`` values should be, explicitly set values from higher priority sources override lower-priority sources:

1. *Highest Priority:* Parameter-annotated command function signature ``Annotated[..., Parameter()]``.
2. :class:`App` ``default_parameter`` that registered the command.
3. *Lowest Priority:* :class:`App` parenting app(s)'s ``default_parameter``.
