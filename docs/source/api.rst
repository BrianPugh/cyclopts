.. _API:

===
API
===

.. autoclass:: cyclopts.App
   :members: default, command, version_print, help_print, interactive_shell, parse_commands, parse_known_args, parse_args, assemble_argument_collection
   :special-members: __call__, __getitem__, __iter__

   Cyclopts Application.

   .. attribute:: name
      :type: Optional[Union[str, Iterable[str]]]
      :value: None

      Name of application, or subcommand if registering to another application. Name fallback resolution:

      1. User specified :attr:`~.App.name` parameter.
      2. If a :attr:`~.App.default` function has been registered, the name of that function.
      3. If the module name is ``__main__.py``, the name of the encompassing package.
      4. The value of ``sys.argv[0]``; i.e. the name of the python script.

      Multiple names can be provided in the case of a subcommand, but this is relatively unusual.

      Example:

      .. code-block:: python

         from cyclopts import App

         app = App()
         app.command(App(name="foo"))

         @app["foo"].command
         def bar():
             print("Running bar.")

         app()

      .. code-block:: console

         $ my-script foo bar
         Running bar.

   .. attribute:: help
      :type: Optional[str]
      :value: None

      Text to display on help screen.
      If not supplied, fallbacks to parsing the docstring of function registered with :meth:`.App.default`.

      .. code-block:: python

         from cyclopts import App

         app = App(help="This is my help string.")
         app()

      .. code-block::

         $ my-script --help
         Usage: scratch.py COMMAND

         This is my help string.

         ╭─ Commands ────────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                             │
         │ --version  Display application version.                               │
         ╰───────────────────────────────────────────────────────────────────────╯

   .. attribute:: help_flags
      :type: Union[str, Iterable[str]]
      :value: ("--help", "-h")

      CLI flags that trigger :meth:`help_print`.
      Set to an empty list to disable this feature.
      Defaults to ``["--help", "-h"]``.

   .. attribute:: help_format
      :type: Optional[Literal["plaintext", "markdown", "md", "restructuredtext", "rst"]]
      :value: None

      The markup language used in function docstring.
      If :obj:`None`, fallback to parenting :attr:`~.App.help_format`.
      If no :attr:`~.App.help_format` is defined, falls back to ``"restructuredtext"``.

   .. attribute:: version_format
      :type: Optional[Literal["plaintext", "markdown", "md", "restructuredtext", "rst"]]
      :value: None

      The markup language used in the version string.
      If :obj:`None`, fallback to parenting :attr:`~.App.version_format`.
      If no :attr:`~.App.version_format` is defined, falls back to resolved :attr:`~.App.help_format`.

   .. attribute:: usage
      :type: Optional[str]
      :value: None

      Text to be displayed in lieue of the default ``Usage: app COMMAND ...`` at the beginning of the help-page.
      Set to an empty-string ``""`` to disable showing the default usage.

   .. attribute:: show
      :type: bool
      :value: True

      Show this **command** on the help screen.
      Hidden commands (``show=False``) are still executable.

      .. code-block:: python

         from cyclopts import App
         app = App()

         @app.command
         def foo():
            print("Running foo.")

         @app.command(show=False)
         def bar():
            print("Running bar.")

         app()

      .. code-block:: console

         $ my-script foo
         Running foo.

         $ my-script bar
         Running bar.

         $ my-script --help
         Usage: scratch.py COMMAND

         ╭─ Commands ─────────────────────────────────────────────────╮
         │ foo                                                        │
         │ --help -h  Display this message and exit.                  │
         │ --version  Display application version.                    │
         ╰────────────────────────────────────────────────────────────╯

   .. attribute:: version
      :type: Union[None, str, Callable]
      :value: None

      Version to be displayed when a :attr:`version_flags` is parsed.
      Defaults to the version of the package instantiating :class:`App`.
      If a :obj:`~typing.Callable`, it will be invoked with no arguments when version is queried.

   .. attribute:: version_flags
      :type: Union[str, Iterable[str]]
      :value: ("--version",)

      Token(s) that trigger :meth:`version_print`.
      Set to an empty list to disable version feature.
      Defaults to ``["--version"]``.

   .. attribute:: console
      :type: rich.console.Console
      :value: None

      Default :class:`rich.console.Console` to use when displaying runtime messages.
      Cyclopts console resolution is as follows:

      #. Any explicitly passed in console to methods like :meth:`App.__call__`, :meth:`App.parse_args`, etc.
      #. The relevant subcommand's :attr:`App.console` attribute, if not :obj:`None`.
      #. The parenting :attr:`App.console` (and so on), if not :obj:`None`.
      #. If all values are :obj:`None`, then the default :class:`~rich.console.Console` is used.


   .. attribute:: default_parameter
      :type: Parameter
      :value: None

      Default :class:`Parameter` configuration. Unspecified values of command-annotated :class:`Parameter` will inherit these values.
      See :ref:`Default Parameter` for more details.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]
      :value: None

      The group(s) that ``default_command`` belongs to.

      * If :obj:`None`, defaults to the ``"Commands"`` group.

      * If :obj:`str`, use an existing :class:`Group` (from neighboring sub-commands) with name,
        **or** create a :class:`Group` with provided name if it does not exist.

      * If :class:`Group`, directly use it.

   .. attribute:: group_commands
      :type: Group
      :value: Group("Commands")

      The default :class:`Group` that sub-commands are assigned to.

   .. attribute:: group_arguments
      :type: Group
      :value: Group("Arguments")

      The default :class:`Group` that positional-only parameters are assigned to.

   .. attribute:: group_parameters
      :type: Group
      :value: Group("Parameters")

      The default :class:`Group` that non-positional-only parameters are assigned to.

   .. attribute:: validator
      :type: Union[None, Callable, list[Callable]]
      :value: []

      A function where all the converted CLI-provided variables will be **keyword-unpacked**,
      regardless of their positional/keyword-type in the command function signature.
      The python variable names will be used, which may differ from their CLI names.

      Example usage:

      .. code-block:: python

         def validator(**kwargs):
             "Raise an exception if something is invalid."

      This validator runs **after** :class:`Parameter` and :class:`Group` validators.

   .. attribute:: name_transform
      :type: Optional[Callable[[str], str]]
      :value: None

      A function that converts function names to their CLI command counterparts.

      The function must have signature:

      .. code-block:: python

         def name_transform(s: str) -> str:
             ...

      The returned string should be **without** a leading ``--``.
      If :obj:`None` (default value), uses :func:`cyclopts.default_name_transform`.
      Subapps inherit from the first non-:obj:`None` parent ``name_transform``.

   .. attribute:: config
      :type: Union[None, Callable, Iterable[Callable]]
      :value: None

      A function or list of functions that are consecutively executed after parsing CLI tokens and environment variables.
      These function(s) are called **before** any conversion and validation.
      Each config function must have signature:

      .. code-block:: python

         def config(apps: list["App"], commands: Tuple[str, ...], arguments: ArgumentCollection):
             """Modifies given mapping inplace with some injected values.

             Parameters
             ----------
             apps: Tuple[App, ...]
                The application hierarchy that led to the current command function.
                The current command app is the last element of this tuple.
             commands: Tuple[str, ...]
                The CLI strings that led to the current command function.
             arguments: ArgumentCollection
                Complete ArgumentCollection for the app.
                Modify this collection inplace to influence values provided to the function.
             """

      The intended use-case of this feature is to allow users to specify functions that can load defaults from some external configuration.
      See :ref:`cyclopts.config <API Config>` for useful builtins and :ref:`Config Files` for examples.


.. autoclass:: cyclopts.Parameter

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

      A function that converts tokens into an object. The converter should have signature:

      .. code-block:: python

          def converter(type_, tokens) -> Any:
              pass

      Where ``type_`` is the parameter's type hint, and ``tokens`` is either:

      * A ``list[cyclopts.Token]`` of CLI tokens (most commonly).

        .. code-block:: python

           from cyclopts import App, Parameter
           from typing import Annotated

           app = App()

           def converter(type_, tokens):
              assert type_ == tuple[int, int]
              return tuple(2 * int(x.value) for x in tokens)

           @app.default
           def main(coordinates: Annotated[tuple[int, int], Parameter(converter=converter)]):
              print(f"{coordinates=}")

           app()

        .. code-block:: console

           $ python my-script.py 7 12
           coordinates=(14, 24)

      * A ``dict`` of :class:`Token` if keys are specified in the CLI. E.g.

        .. code-block:: console

           $ python my-script.py --foo.key1=val1

        would be parsed into:

        .. code-block:: python

           tokens = {
              "key1": ["val1"],
           }

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

      * For booleans, defaults to ``no-{name}`` (see :attr:`negative_bool`).

      * For iterables, defaults to ``empty-{name}`` (see :attr:`negative_iterable`).

      Set to an empty list or string to disable the creation of negative flags.

   .. attribute:: negative_bool
      :type: Optional[str]
      :value: None

      Prefix for negative boolean flags. Defaults to ``"no-"``.

   .. attribute:: negative_iterable
      :type: Optional[str]
      :value: None

      Prefix for empty iterables (like lists and sets) flags. Defaults to ``"empty-"``.

   .. attribute:: allow_leading_hyphen
      :type: bool
      :value: False

      Allow parsing non-numeric values that begin with a hyphen ``-``.
      This is disabled (:obj:`False`) by default, allowing for more helpful error messages for unknown CLI options.

   .. attribute:: parse
      :type: Optional[bool]
      :value: True

      Attempt to use this parameter while parsing.
      Annotated parameter **must** be keyword-only.

   .. attribute:: required
      :type: Optional[bool]
      :value: None

      Indicates that the parameter must be supplied.
      Defaults to inferring from the function signature; i.e. ``False`` if the parameter has a default, ``True`` otherwise.

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

   .. attribute:: env_var_split
      :type: Callable
      :value: cyclopts.env_var_split

      Function that splits up the read-in :attr:`~cyclopts.Parameter.env_var` value.
      The function must have signature:

      .. code-block:: python

         def env_var_split(type_: type, val: str) -> list[str]:
             ...

      where ``type_`` is the associated parameter type-hint, and ``val`` is the environment value.

   .. attribute:: name_transform
      :type: Optional[Callable[[str], str]]
      :value: None

      A function that converts python parameter names to their CLI command counterparts.

      The function must have signature:

      .. code-block:: python

         def name_transform(s: str) -> str:
             ...

      If :obj:`None` (default value), uses :func:`cyclopts.default_name_transform`.

   .. attribute:: accepts_keys
      :type: Optional[bool]
      :value: None

      If ``False``, treat the user-defined class annotation similar to a tuple.
      Individual class sub-parameters will not be addressable by CLI keywords.
      The class will consume enough tokens to populate all required positional parameters.

      Default behavior (``accepts_keys=True``):

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         class Image:
            def __init__(self, path, label):
               self.path = path
               self.label = label

            def __repr__(self):
               return f"Image(path={self.path!r}, label={self.label!r})"

         @app.default
         def main(image: Image):
            print(f"{image=}")

         app()

      .. code-block:: console

         $ my-program --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ──────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                           │
         │ --version  Display application version.                             │
         ╰─────────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ────────────────────────────────────────────────────────╮
         │ *  IMAGE.PATH --image.path    [required]                            │
         │ *  IMAGE.LABEL --image.label  [required]                            │
         ╰─────────────────────────────────────────────────────────────────────╯

         $ my-program foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

         $ my-program --image.path foo.jpg --image.label nature
         image=Image(path='foo.jpg', label='nature')

      Behavior when ``accepts_keys=False``:

      .. code-block:: python

         # Modify the default command function's signature.
         @app.default
         def main(image: Annotated[Image, Parameter(accepts_keys=False)]):
            print(f"{image=}")

      .. code-block:: console

         $ my-program --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ──────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                           │
         │ --version  Display application version.                             │
         ╰─────────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ────────────────────────────────────────────────────────╮
         │ *  IMAGE --image  [required]                                        │
         ╰─────────────────────────────────────────────────────────────────────╯

         $ my-program foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

         $ my-program --image foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

   .. attribute:: consume_multiple
      :type: Optional[bool]
      :value: None

      When a parameter is **specified by keyword**, consume multiple elements worth of CLI tokens.
      Will consume tokens until the stream is exhausted, or an and :attr:`.allow_leading_hyphen` is False
      If ``False`` (default behavior), then only a single element worth of CLI tokens will be consumed.

      .. code-block:: python

         from cyclopts import App
         from pathlib import Path

         app = App()

         @app.default
         def rules(files: list[Path], ext: list[str] = []):
            pass

         app()

      .. code-block:: console

         $ cmd --ext .pdf --ext .html foo.md bar.md

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

   .. attribute:: validator
      :type: Optional[Callable]
      :value: None

      A function (or list of functions) that validates an :class:`.ArgumentCollection`.

      Example usage:

      .. code-block:: python

         def validator(argument_collection: ArgumentCollection):
             "Raise an exception if something is invalid."

      Validators are **not** invoked for command groups.

.. autoclass:: cyclopts.Token

   .. attribute:: keyword
      :type: Optional[str]
      :value: None

      **Unadulterated** user-supplied keyword like ``--foo`` or ``--foo.bar.baz``; ``None`` when token was pared positionally.
      Could also be something like ``tool.project.foo`` if from non-cli sources.

   .. attribute:: value
      :type: str
      :value: ""

      The parsed token value (unadulterated).

   .. attribute:: source
      :type: str
      :value: ""

      Where the token came from; used for error message purposes.
      Cyclopts uses the string ``cli`` for cli-parsed tokens.

   .. attribute:: index
      :type: int
      :value: 0

      The relative positional index in which the value was provided.

   .. attribute:: keys
      :type: tuple[str, ...]
      :value: ()

      The additional parsed **python** variable keys from :attr:`keyword`.

      Only used for Arguments that take arbitrary keys.

   .. attribute:: implicit_value
      :type: Any
      :value: cyclopts.UNSET

      Final value that should be used instead of converting from :attr:`value`.

      Commonly used for boolean flags.

      Ignored if :obj:`~.UNSET`.

.. autoclass:: cyclopts.field_info.FieldInfo

.. autoclass:: cyclopts.Argument
   :members:

.. autoclass:: cyclopts.ArgumentCollection
   :members:

.. autoclass:: cyclopts.UNSET

.. autofunction:: cyclopts.default_name_transform

.. autofunction:: cyclopts.env_var_split

.. _API Validators:

----------
Validators
----------
Cyclopts has several builtin validators for common CLI inputs.

.. autoclass:: cyclopts.validators.LimitedChoice
   :members:

.. autoclass:: cyclopts.validators.MutuallyExclusive
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
All of these types will also work on sequence of paths (e.g. ``tuple[Path, Path]`` or ``list[Path]``).

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
All of these types will also work on sequence of numbers (e.g. ``tuple[int, int]`` or ``list[float]``).

.. autodata:: cyclopts.types.PositiveFloat

.. autodata:: cyclopts.types.NonNegativeFloat

.. autodata:: cyclopts.types.NegativeFloat

.. autodata:: cyclopts.types.NonPositiveFloat

.. autodata:: cyclopts.types.PositiveInt

.. autodata:: cyclopts.types.NonNegativeInt

.. autodata:: cyclopts.types.NegativeInt

.. autodata:: cyclopts.types.NonPositiveInt

.. autodata:: cyclopts.types.UInt8

.. autodata:: cyclopts.types.Int8

.. autodata:: cyclopts.types.UInt16

.. autodata:: cyclopts.types.Int16

.. autodata:: cyclopts.types.UInt32

.. autodata:: cyclopts.types.Int32


.. _API Config:

------
Config
------
Cyclopts has builtin configuration classes to be used with :attr:`App.config <cyclopts.App.config>` for loading user-defined defaults in many common scenarios.
All Cyclopts builtins index into the configuration file with the following rules:

1. Apply ``root_keys`` (if provided) to enter the project's configuration namespace.

2. Apply the command name(s) to enter the current command's configuration namespace.

3. Apply each key/value pair if CLI arguments have **not** been provided for that parameter.

.. autoclass:: cyclopts.config.Toml
   :members:

   Automatically read configuration from Toml file.

   .. attribute:: root_keys
      :type: Iterable[str]
      :value: None
      :noindex:

      The key or sequence of keys that lead to the root configuration structure for this app.
      For example, if referencing a ``pyproject.toml``, it is common to store all of your projects configuration under:

      .. code-block:: toml

         [tool.myproject]

      So, your Cyclopts :class:`~cyclopts.App` should be configured as:

      .. code-block:: python

         app = cyclopts.App(config=cyclopts.config.Toml("pyproject.toml", root_keys=("tool", "myproject")))

.. autoclass:: cyclopts.config.Yaml
   :members:

   Automatically read configuration from Yaml file.


.. autoclass:: cyclopts.config.Json
   :members:

   Automatically read configuration from Json file.


.. autoclass:: cyclopts.config.Env

   Automatically derive environment variable names to read configurations from.

   For example, consider the following app:

   .. code-block:: python

      import cyclopts

      app = cyclopts.App(config=cyclopts.config.Env("MY_SCRIPT_"))


      @app.command
      def my_command(foo, bar):
          print(f"{foo=} {bar=}")


      app()

   If values for ``foo`` and ``bar`` are not supplied by the command line, the app will check
   the environment variables ``MY_SCRIPT_MY_COMMAND_FOO`` and ``MY_SCRIPT_MY_COMMAND_BAR``, respectively:

   .. code-block:: console

      $ python my_script.py my-command 1 2
      foo=1 bar=2

      $ export MY_SCRIPT_MY_COMMAND_FOO=100
      $ python my_script.py my-command --bar=2
      foo=100 bar=2
      $ python my_script.py my-command 1 2
      foo=1 bar=2


   .. attribute:: prefix
      :type: str
      :value: ""

      String to prepend to all autogenerated environment variable names.
      Typically ends in ``_``, and is something like ``MY_APP_``.

   .. attribute:: command
      :type: bool
      :value: True

   .. attribute:: split
      :type: Callable
      :value: cyclopts.env_var_split

      Function that splits up the read-in :attr:`~cyclopts.Parameter.env_var` value.

----------
Exceptions
----------

.. autoexception:: cyclopts.CycloptsError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.ValidationError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.UnknownOptionError
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
