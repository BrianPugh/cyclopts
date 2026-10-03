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

   * - :meth:`app.add_typer(...)`
     - :meth:`app.command(...)`
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

Most ``typer.Option``/``typer.Argument`` keyword arguments have a shorter Cyclopts spelling, or are unnecessary entirely.
The left column is the Typer habit; the right column is the idiomatic Cyclopts replacement.

.. list-table:: Typer-to-Cyclopts Parameter Habits
   :widths: 40 60
   :header-rows: 1

   * - Typer
     - Cyclopts

   * - ``Option(help="Number of workers.")``
     - No :class:`.Parameter` needed. Document ``workers`` in the function's :ref:`docstring <Typer Docstring Parsing>`.
       :attr:`.Parameter.help` exists as an override for when no docstring is available.

   * - ``Option("--workers", "-w")``
     - ``Parameter(alias="-w")``. :attr:`~.Parameter.alias` **adds** a name; the derived ``--workers`` is kept.
       Use :attr:`~.Parameter.name` only to **replace** the derived name.

   * - ``Option(envvar="WORKERS")``
     - ``Parameter(env_var="WORKERS")``

   * - ``Option(hidden=True)``
     - ``Parameter(show=False)``

   * - ``Option(rich_help_panel="Tuning")``
     - ``Parameter(group="Tuning")``

   * - ``Option(min=1, max=64)``
     - ``Parameter(validator=validators.Number(gte=1, lte=64))``

   * - ``Option(exists=True, dir_okay=False)`` on a :class:`~pathlib.Path`
     - ``Parameter(validator=validators.Path(exists=True, dir_okay=False))``

   * - ``Option(callback=check)``
     - ``Parameter(validator=check)`` for validation; ``Parameter(converter=parse)`` for parsing. See :ref:`Parameter Validators`.

   * - ``Option(parser=parse)``
     - ``Parameter(converter=parse)``

   * - ``Option(count=True)``
     - ``Parameter(count=True)``

   * - ``Option("--flag/--no-flag")``
     - Nothing; ``--no-flag`` is generated for every :class:`bool`. Customize with :attr:`~.Parameter.negative`.

   * - ``Option(is_flag=False)`` / ``Argument(...)`` to control positional vs keyword
     - The function signature decides: parameters before ``/`` are positional-only, after ``*`` are keyword-only, otherwise both.
       See :ref:`Typer Argument vs Option`.

   * - :class:`~enum.Enum` for choices
     - :obj:`~typing.Literal` is terser; :class:`~enum.Enum` also works.

   * - ``typer.echo(...)``
     - :func:`print`.

   * - ``raise typer.Exit(code=1)``
     - ``return 1`` (an :class:`int` return value becomes the exit code) or ``raise SystemExit(1)``.

   * - ``Typer(rich_markup_mode="rich")``
     - ``App(help_format="rich")``; the default is ``"restructuredtext"``. Markdown is also supported.

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
