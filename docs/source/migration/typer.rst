====================
Migrating From Typer
====================
Much of Cyclopts's syntax is `Typer`_-inspired. Migrating from Typer should be pretty straightforward; it is recommended to first read the :ref:`Getting Started` and :ref:`Commands` sections. The below table offers a jumping off point for translating the various portions of the APIs. The :ref:`Typer Comparison` page also provides many examples comparing the APIs.

.. list-table:: Typer-to-Cyclopts API Reference
   :widths: 30 30 40
   :header-rows: 1

   * - Typer
     - Cyclopts
     - Notes

   * - :class:`typer.Typer()`
     - :class:`cyclopts.App()`
     - Same/similar fields:
         + :attr:`.App.name` - Optional name of application or sub-command.
       Cyclopts has more user-friendly default features:
         + Equivalent ``no_args_is_help=True``.
         + Equivalent ``pretty_exceptions_enable=False``.

   * - :meth:`@app.command()`
     - :meth:`@app.command() <.App.command>`
     - In Cyclopts, ``@app.command`` :ref:`always results in a command. <Typer Default Command>` To define an action when no command is provided, see :meth:`@app.default <.App.default>`.

   * - :meth:`@app.add_typer`
     - :meth:`@app.command`
     - Sub applications and commands are registered the same way in Cyclopts.

   * - :meth:`@app.callback()`
     - :meth:`@app.default() <.App.default>`

       :meth:`@app.meta.default() <.App.default>`
     - Typer's callback always executes before executing an app.
       If used to provide functionality when no command was specified from the CLI, then use :meth:`@app.default() <.App.default>`.
       Otherwise, checkout Cyclopt's :ref:`Meta App`.

   * - :class:`Annotated[..., typer.Argument(...)]`

       :class:`Annotated[..., typer.Option(...)]`
     - :class:`Annotated[..., cyclopts.Parameter(...)] <.Parameter>`
     - In Cyclopts, Positional/Keyword arguments :ref:`are determined from the function signature. <Typer Argument vs Option>`
       Some of Typer's validation fields, like ``exists`` for :class:`~pathlib.Path` types are handled in Cyclopts :ref:`by explicit validators. <Parameter Validators>`

Cyclopts and Typer mostly handle type-hints the same way, but there are a few notable exceptions:

.. list-table:: Typer-to-Cyclopts Type-Hints
   :widths: 30 70
   :header-rows: 1

   * - Type Annotation
     - Notes

   * - :class:`~enum.Enum`
     - Compared to Typer, Cyclopts handles :class:`~enum.Enum` lookups :ref:`in the reverse direction. <Typer Choices>`
       Frequently, :obj:`~typing.Literal` :ref:`offers a more terse, intuitive choice option. <Coercion Rules - Literal>`

   * - :obj:`~typing.Union`
     - Typer does **not** support type unions. :ref:`Cyclopts does. <Coercion Rules - Union>`

   * - ``Optional[List] = None``
     - When no CLI argument is specified, Typer passes in an empty list ``[]``.
       :ref:`Cyclopts will not bind an argument, <Typer Optional Lists>` resulting in the default :obj:`None`.

-------------
General Steps
-------------
#. Add the following import: ``from cyclopts import App, Parameter``.
#. Change ``app = Typer(...)`` to just ``app = App()``. Revisit more advanced configuration later.
#. Remove all ``@app.callback`` stuff. Cyclopts already provides a good ``--version`` handler for you.
#. Replace all ``Annotated[..., Argument/Option]`` type-hints with :class:`Annotated[..., Parameter()] <.Parameter>`.
   If only supplying a :attr:`~.Parameter.help` string, :ref:`it's better to supply it via docstring. <Typer Docstring Parsing>`
#. Cyclopts has similar boolean-flag handling as Typer, :ref:`but has different configuration parameters. <Typer Flag Negation>`

   .. code-block:: python

      #########
      # Typer #
      #########
      # Overriding the name results in no "False" flag generation.
      my_flag: Annotated[bool, Option("--my-custom-flag")]
      # However, it can be custom specified:
      my_flag: Annotated[bool, Option("--my-custom-flag/--disable-my-custom-flag")]

      ############
      # Cyclopts #
      ############
      # Overriding the name still results in "False" flag generation:
      #    --my-custom-flag --no-my-custom-flag
      my_flag: Annotated[bool, Parameter("--my-custom-flag")]
      # Negative flag generation can be disabled:
      #    --my-custom-flag
      my_flag: Annotated[bool, Parameter("--my-custom-flag", negative="")]
      # Or the prefix can be changed:
      #    --my-custom-flag --disable-my-custom-flag
      my_flag: Annotated[bool, Parameter("--my-custom-flag", negative_bool="--disable-")]

After the basic migration is done, it is recommended to read through the rest of Cyclopts's documentation to learn about some of the better functionality it has, which could result in cleaner, terser code.

.. _Typer: https://typer.tiangolo.com
.. _always results in a command.: https://github.com/tiangolo/typer/issues/315
