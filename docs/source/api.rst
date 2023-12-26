.. _API:

===
API
===

.. autoclass:: cyclopts.App
   :members: name, default, default_parameter, command, version_print, help_print, interactive_shell, parse_known_args, parse_args
   :special-members: __call__, __getitem__

.. autoclass:: cyclopts.Parameter

   Cyclopts configuration for individual function parameters.

   .. attribute:: name
      :type: Union[None, str, Iterable[str]]

      Name(s) to expose to the CLI.
      Defaults to the python parameter's name, prepended with ``--``.
      Single-character options should start with ``-``.
      Full-name options should start with ``--``.

   .. attribute:: converter
      :type: Optional[Converter]

      A function that converts string token(s) into an object. The converter must have signature:

      .. code-block:: python

          def converter(type_, *args) -> Any:
              pass

      If not provided, defaults to Cyclopts's internal coercion engine.

   .. attribute:: validator
      :type: Union[None, Validator, Iterable[Validator]]

      A function (or list of functions) that validates data returned by the ``converter``.

      .. code-block:: python

          def validator(type_, value: Any) -> None:
              pass  # Raise a TypeError, ValueError, or AssertionError here if data is invalid.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]

      The group(s) that this parameter belongs to.
      This can be used to better organize the help-page, and/or to add additional conversion/validation logic (such as ensuring mutually-exclusive arguments).

      If ``None``, defaults to one of the following groups:

      1. ``"Arguments"`` if the parameter is ``POSITIONAL_ONLY``.

      2. ``"Parameters"`` otherwise.

   .. attribute:: negative
      :type: Union[None, str, Iterable[str]]

      Name(s) for empty iterables or false boolean flags.
      For booleans, defaults to ``--no-{name}``.
      For iterables, defaults to ``--empty-{name}``.
      Set to an empty list to disable this feature.

   .. attribute:: negative_bool
      :type: Optional[str]

      Prefix for negative boolean flags.
      Must start with ``"--"``.
      Defaults to ``"--no-"``.

   .. attribute:: negative_iterable
      :type: Optional[str]

      Prefix for empty iterables (like lists and sets) flags.
      Must start with ``"--"``.
      Defaults to ``"--empty-"``.

   .. attribute:: token_count
      :type: Optional[int]

      Number of CLI tokens this parameter consumes.
      If specified, a custom ``converter`` **must** also be specified.
      Defaults to autodetecting based on type annotation.

   .. attribute:: parse
      :type: Optional[bool]

      Attempt to use this parameter while parsing.
      Annotated parameter **must** be keyword-only.
      Defaults to ``True``.

   .. attribute:: show
      :type: Optional[bool]

      Show this parameter in the help screen.
      If ``False``, state of all other ``show_*`` flags are ignored.
      Defaults to ``parse`` value (``True``).

   .. attribute:: show_default
      :type: Optional[bool]

      If a variable has a default, display the default in the help page.
      Defaults to ``None``, similar to ``True``, but will not display the default if it's ``None``.

   .. attribute:: show_choices
      :type: Optional[bool]

      If a variable has a set of choices, display the choices in the help page.
      Defaults to ``True``.

   .. attribute:: help
      :type: Optional[str]

      Help string to be displayed in the help page.
      If not specified, defaults to the docstring.

   .. attribute:: show_env_var
      :type: Optional[bool]

      If a variable has ``env_var`` set, display the variable name in the help page.
      Defaults to ``True``.

   .. attribute:: env_var
      :type: Union[None, str, Iterable[str]]

      Fallback to environment variable(s) if CLI value not provided.
      If multiple environment variables are given, the left-most environment variable with a set value will be used.
      If no environment variable is set, Cyclopts will fallback to the function-signature default.

   .. automethod:: combine

   .. automethod:: default

.. autoclass:: cyclopts.Group

   A group of parameters and/or commands in a CLI application.

   .. attribute:: name
      :type: str

      Group name used for the help-panel and for group-referenced-by-string.
      Typically this is a title, so the first character should be capitalized.

   .. attribute:: help
      :type: str
      :value: ""

      Additional documentation shown on the help screen.

   .. attribute:: show
      :type: bool
      :value: True

      Show this group in the help-panel. This parameter is keyword-only.

   .. attribute:: converter
      :type: Optional[Callable]

      A function where the CLI-provided group variables will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature. The python variable names will be used, which may differ from their CLI names.

      .. code-block:: python

          def converter(**kwargs) -> Dict[str, Any]:
              """Return an updated dictionary."""

      The returned dictionary will be used passed along to the command invocation.
      The group converter runs **after** :class:`Parameter` converters and validators.
      This parameter is keyword-only.

   .. attribute:: validator
      :type: Optional[Callable]
      :value: None

      A function (or list of functions) where the CLI-provided group variables will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature. The python variable names will be used, which may differ from their CLI names.

      Example usage:

      .. code-block:: python

         def validator(**kwargs):
             "Raise an exception if something is invalid."

      Validators are **not** invoked on command groups.
      The group-validator runs **after** the group-converter.
      This parameter is keyword-only.

   .. attribute:: default_parameter
      :type: Optional[Parameter]
      :value: None

      Default Parameter in the parameter-resolution-stack that goes between ``app.default_parameter`` and the function signature's Annotated Parameter. This parameter is keyword-only.

   .. attribute:: default
      :type: Optional[Literal["Arguments", "Parameters", "Commands"]]
      :value: None

      Only one group registered to an app can have each non-``None`` option. This parameter is keyword-only.

.. autofunction:: cyclopts.coerce

.. autofunction:: cyclopts.create_bound_arguments

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
