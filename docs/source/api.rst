.. _API:

===
API
===

.. autoclass:: cyclopts.App
   :members: default, command, version_print, help_print, interactive_shell, parse_commands, parse_known_args, parse_args
   :special-members: __call__, __getitem__, __iter__

   Cyclopts Application.

   .. attribute:: name
      :type: Optional[Union[str, Iterable[str]]]
      :value: None

      Name of application, or subcommand if registering to another application. Name fallback resolution:

      1. User specified ``name``.
      2. If a ``default`` function has been registered, the name of that function.
      3. If the module name is ``__main__.py``, the name of the encompassing package.
      4. The value of ``sys.argv[0]``.

      Multiple names can be provided in the case of a subcommand, but this is relatively unusual.

   .. attribute:: help
      :type: Optional[str]
      :value: None

      Text to display on help screen.

   .. attribute:: help_flags
      :type: Union[str, Iterable[str]]
      :value: ("--help", "-h")

      Tokens that trigger :meth:`help_print`.
      Set to an empty list to disable help feature.
      Defaults to ``["--help", "-h"]``.
      Cannot be changed after instantiating the app.

   .. attribute:: help_format
      :type: Optional[Literal["plaintext", "markdown", "md", "restructuredtext", "rst"]]
      :value: None

      The markup language of docstring function descriptions.
      If :obj:`None`, fallback to parenting :attr:`~.App.help_format`.
      If no :attr:`~.App.help_format` is defined, falls back to ``"restructuredtext"``.

   .. attribute:: usage
      :type: Optional[str]
      :value: None

      Text to be displayed in lieue of the default ``Usage: app COMMAND ...`` at the beginning of the help-page.
      Set to an empty-string ``""`` to disable showing the default usage.

   .. attribute:: show
      :type: bool
      :value: True

      Show this command on the help screen.

   .. attribute:: version
      :type: Union[None, str, Callable]
      :value: None

      Version to be displayed when a token of ``version_flags`` is parsed.
      Defaults to attempting to using version of the package instantiating :class:`App`.
      If a ``Callable``, it will be invoked with no arguments when version is queried.

   .. attribute:: version_flags
      :type: Union[str, Iterable[str]]
      :value: ("--version",)

      Token(s) that trigger :meth:`version_print`.
      Set to an empty list to disable version feature.
      Defaults to ``["--version"]``.
      Cannot be changed after instantiating the app.

   .. attribute:: console
      :type: rich.console.Console
      :value: None

      Default :class:`rich.console.Console` to use when displaying runtime errors.
      Cyclopts console resolution is as follows:

      #. Any explicitly passed in console to methods like :meth:`App.__call__`, :meth:`App.parse_args`, etc.
      #. The relevant subcommand's :attr:`App.console` attribute, if not :obj:`None`.
      #. The parenting :attr:`App.console` (and so on), if not :obj:`None`.
      #. If all values are :obj:`None`, then the default :class:`~rich.console.Console` is used.


   .. attribute:: default_parameter
      :type: Parameter
      :value: None

      Default :class:`Parameter` configuration.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]
      :value: None

      The group(s) that ``default_command`` belongs to.

      * If :obj:`None`, defaults to the ``"Commands"`` group.

      * If ``str``, use an existing Group (from neighboring sub-commands) with name,
        **or** create a :class:`Group` with provided name if it does not exist.

      * If :class:`Group`, directly use it.

   .. attribute:: group_commands
      :type: Group
      :value: Group("Commands")

      The default group that sub-commands are assigned to.

   .. attribute:: group_arguments
      :type: Group
      :value: Group("Arguments")

      The default group that positional-only parameters are assigned to.

   .. attribute:: group_parameters
      :type: Group
      :value: Group("Parameters")

      The default group that non-positional-only parameters are assigned to.

   .. attribute:: converter
      :type: Optional[Callable]
      :value: None

      A function where all the converted CLI-provided variables will be keyword-unpacked,
      regardless of their positional/keyword-type in the command function signature.
      The python variable names will be used, which may differ from their CLI names.

      .. code-block:: python

          def converter(**kwargs) -> Dict[str, Any]:
              "Return an updated dictionary."

      The returned dictionary will be used passed along to the command invocation.
      This converter runs **after** :class:`Parameter` and :class:`Group` converters.

   .. attribute:: validator
      :type: Union[None, Callable, List[Callable]]
      :value: []

      A function where all the converted CLI-provided variables will be keyword-unpacked,
      regardless of their positional/keyword-type in the command function signature.
      The python variable names will be used, which may differ from their CLI names.

      Example usage:

      .. code-block:: python

         def validator(**kwargs):
             "Raise an exception if something is invalid."

      This validator runs **after** :class:`Parameter` and :class:`Group` validators.

      The raised error message will be presented to the user with python-variables prepended with "--" remapped to their CLI counterparts.

.. autoclass:: cyclopts.Parameter

   Cyclopts configuration for individual function parameters.

   .. attribute:: name
      :type: Union[None, str, Iterable[str]]
      :value: None

      Name(s) to expose to the CLI.
      Defaults to the python parameter's name, prepended with ``--``.
      Single-character options should start with ``-``.
      Full-name options should start with ``--``.

   .. attribute:: converter
      :type: Optional[Callable]
      :value: None

      A function that converts string token(s) into an object. The converter must have signature:

      .. code-block:: python

          def converter(type_, *args) -> Any:
              pass

      If not provided, defaults to Cyclopts's internal coercion engine.

   .. attribute:: validator
      :type: Union[None, Callable, Iterable[Callable]]
      :value: None

      A function (or list of functions) that validates data returned by the ``converter``.

      .. code-block:: python

          def validator(type_, value: Any) -> None:
              pass  # Raise a TypeError, ValueError, or AssertionError here if data is invalid.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]
      :value: None

      The group(s) that this parameter belongs to.
      This can be used to better organize the help-page, and/or to add additional conversion/validation logic (such as ensuring mutually-exclusive arguments).

      If :obj:`None`, defaults to one of the following groups:

      1. Parenting :attr:`.App.group_arguments` if the parameter is ``POSITIONAL_ONLY``.
         By default, this is ``Group("Arguments")``.

      2. Parenting :attr:`.App.group_parameters` otherwise.
         By default, this is ``Group("Parameters")``.

   .. attribute:: negative
      :type: Union[None, str, Iterable[str]]
      :value: None

      Name(s) for empty iterables or false boolean flags.
      For booleans, defaults to ``--no-{name}``.
      For iterables, defaults to ``--empty-{name}``.
      Set to an empty list to disable this feature.

   .. attribute:: negative_bool
      :type: Optional[str]
      :value: None

      Prefix for negative boolean flags.
      Must start with ``"--"``.
      Defaults to ``"--no-"``.

   .. attribute:: negative_iterable
      :type: Optional[str]
      :value: None

      Prefix for empty iterables (like lists and sets) flags.
      Must start with ``"--"``.
      Defaults to ``"--empty-"``.

   .. attribute:: allow_leading_hyphen
      :type: bool
      :value: False

      Allow parsing non-numeric values that begin with a hyphen ``-``.
      This is disabled by default, allowing for more helpful error messages for unknown CLI options.

   .. attribute:: parse
      :type: Optional[bool]
      :value: True

      Attempt to use this parameter while parsing.
      Annotated parameter **must** be keyword-only.

   .. attribute:: required
      :type: Optional[bool]
      :value: None

      Parameter must be supplied.
      Defaults to required if parameter does not have a default from the function signature.

   .. attribute:: show
      :type: Optional[bool]
      :value: None

      Show this parameter on the help screen.
      If ``False``, state of all other ``show_*`` flags are ignored.
      Defaults to ``parse`` value (``True``).

   .. attribute:: show_default
      :type: Optional[bool]
      :value: None

      If a variable has a default, display the default on the help page.
      Defaults to :obj:`None`, similar to ``True``, but will not display the default if it's :obj:`None`.

   .. attribute:: show_choices
      :type: Optional[bool]
      :value: True

      If a variable has a set of choices, display the choices on the help page.
      Defaults to ``True``.

   .. attribute:: help
      :type: Optional[str]
      :value: None

      Help string to be displayed on the help page.
      If not specified, defaults to the docstring.

   .. attribute:: show_env_var
      :type: Optional[bool]
      :value: True

      If a variable has ``env_var`` set, display the variable name on the help page.
      Defaults to ``True``.

   .. attribute:: env_var
      :type: Union[None, str, Iterable[str]]
      :value: None

      Fallback to environment variable(s) if CLI value not provided.
      If multiple environment variables are given, the left-most environment variable with a set value will be used.
      If no environment variable is set, Cyclopts will fallback to the function-signature default.

   .. automethod:: combine

   .. automethod:: default

.. autoclass:: cyclopts.Group
   :members: create_ordered

   A group of parameters and/or commands in a CLI application.

   .. attribute:: name
      :type: str
      :value: ""

      Group name used for the help-page and for group-referenced-by-string.
      This is a title, so the first character should be capitalized.
      If a name is not specified, it will not be shown on the help-page.

   .. attribute:: help
      :type: str
      :value: ""

      Additional documentation shown on the help-page.
      This will be displayed inside the group's panel, above the parameters/commands.

   .. attribute:: show
      :type: Optional[bool]
      :value: None

      Show this group on the help-page.
      Defaults to :obj:`None`, which will only show the group if a ``name`` is provided.

   .. attribute:: sort_key
      :type: Any
      :value: None

      Modifies group-panel display order on the help-page.

      1. If :attr:`sort_key`, or any of it's contents, are ``Callable``, then invoke it ``sort_key(group)`` and apply the returned value to (2) if :obj:`None`, (3) otherwise.

      2. For all groups with ``sort_key==None`` (default value), sort them alphabetically.
         These sorted groups will be displayed **after** ``sort_key != None`` list (see 3).

      3. For all groups with ``sort_key!=None``, sort them by ``(sort_key, group.name)``.
         It is the user's responsibility that ``sort_key`` s are comparable.

      Example usage:

      .. code-block:: python

         @app.command(group=Group("4", sort_key=5))
         def cmd1():
             pass


         @app.command(group=Group("3", sort_key=lambda x: 10))
         def cmd2():
             pass


         @app.command(group=Group("2", sort_key=lambda x: None))
         def cmd3():
             pass


         @app.command(group=Group("1"))
         def cmd4():
             pass

      Resulting help-page:

      .. code-block:: bash

        Usage: app COMMAND

        App Help String Line 1.

        ╭─ 4 ────────────────────────────────────────────────────────────────╮
        │ cmd1                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 3 ────────────────────────────────────────────────────────────────╮
        │ cmd2                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 1 ────────────────────────────────────────────────────────────────╮
        │ cmd4                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 2 ────────────────────────────────────────────────────────────────╮
        │ cmd3                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯

   .. attribute:: default_parameter
      :type: Optional[Parameter]
      :value: None

      Default :class:`Parameter` in the parameter-resolution-stack that goes between :attr:`.App.default_parameter` and the function signature's :obj:`Annotated` :class:`.Parameter`.
      The provided :class:`Parameter` is not allowed to have a :attr:`~Parameter.group` value.

   .. attribute:: converter
      :type: Optional[Callable]

      A function where the CLI-provided group variables will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature. The python variable names will be used, which may differ from their CLI names.

      .. code-block:: python

          def converter(**kwargs) -> Dict[str, Any]:
              """Return an updated dictionary."""

      The **python variable names will be used**, which may differ from their CLI names.
      If a variable isn't populated from the CLI or environment variable, it will not be provided to the converter.
      I.e. defaults from the function signature are **not** applied prior.

      The returned dictionary will be used for subsequent execution.
      Removing variables from the returned dictionary will unbind them.
      When used with :meth:`@app.command <cyclopts.App.command>`, all function arguments are provided.

   .. attribute:: validator
      :type: Optional[Callable]
      :value: None

      A function (or list of functions) where the CLI-provided group variables will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature.
      The **python variable names will be used**, which may differ from their CLI names.

      Example usage:

      .. code-block:: python

         def validator(**kwargs):
             "Raise an exception if something is invalid."

      Validators are **not** invoked on command groups.
      The group-validator runs **after** the group-converter.

      The raised error message will be presented to the user with python-variables prepended with ``"--"`` remapped to their CLI counterparts.

      In the following example, the python variable name ``"--bar"`` in the error message is remapped to ``"--buzz"``.

      .. code-block:: python

         from cyclopts import Parameter, App, Group
         from typing import Annotated

         app = App()


         def upper_case_only(**kwargs):
             for k, v in kwargs.items():
                 if not v.isupper():
                     raise ValueError(f'--{k} value "{v}" needs to be uppercase.')


         group = Group("", validator=upper_case_only)


         @app.default
         def foo(
             bar: Annotated[str, Parameter(name="--fizz", group=group)],
             baz: Annotated[str, Parameter(name="--buzz", group=group)],
         ):
             pass


         app()

      .. code-block:: console

         $ python meow.py ALICE bob
         ╭─ Error ─────────────────────────────────────────────────╮
         │ --buzz value "bob" needs to be uppercase.               │
         ╰─────────────────────────────────────────────────────────╯


.. autofunction:: cyclopts.convert


.. _API Validators:

----------
Validators
----------
Cyclopts has several builtin validators for common CLI inputs.

.. autoclass:: cyclopts.validators.LimitedChoice
   :members:

.. autoclass:: cyclopts.validators.Number
   :members:

.. autoclass:: cyclopts.validators.Path
   :members:


.. _Annotated Types:

-----
Types
-----
Cyclopts has builtin pre-defined annotated-types for common validation configurations.
All definitions in this section are just predefined annotations for convenience:

.. code-block:: python

   Annotated[..., Parameter(...)]

Due to Cyclopts's advanced :class:`.Parameter` resolution engine, these annotations can themselves be annotated. E.g:

.. code-block::

   Annotated[PositiveInt, Parameter(...)]

.. _Annotated Path Types:

^^^^
Path
^^^^
:class:`~pathlib.Path` annotated types for checking existence, type, and performing path-resolution.

.. autodata:: cyclopts.types.ExistingPath

.. autodata:: cyclopts.types.ResolvedPath

.. autodata:: cyclopts.types.ResolvedExistingPath

.. autodata:: cyclopts.types.Directory

.. autodata:: cyclopts.types.ExistingDirectory

.. autodata:: cyclopts.types.ResolvedDirectory

.. autodata:: cyclopts.types.ResolvedExistingDirectory

.. autodata:: cyclopts.types.File

.. autodata:: cyclopts.types.ExistingFile

.. autodata:: cyclopts.types.ResolvedFile

.. autodata:: cyclopts.types.ResolvedExistingFile

.. _Annotated Number Types:

^^^^^^
Number
^^^^^^
Annotated types for checking common int/float value constraints.

.. autodata:: cyclopts.types.PositiveFloat

.. autodata:: cyclopts.types.NonNegativeFloat

.. autodata:: cyclopts.types.NegativeFloat

.. autodata:: cyclopts.types.NonPositiveFloat

.. autodata:: cyclopts.types.PositiveInt

.. autodata:: cyclopts.types.NonNegativeInt

.. autodata:: cyclopts.types.NegativeInt

.. autodata:: cyclopts.types.NonPositiveInt

----------
Exceptions
----------

.. autoexception:: cyclopts.CycloptsError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.ValidationError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.CoercionError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.InvalidCommandError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.UnusedCliTokensError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.MissingArgumentError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.CommandCollisionError
