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

.. autofunction:: cyclopts.coerce

.. autofunction:: cyclopts.create_bound_arguments

----------
Validators
----------
Cyclopts has several builtin validators for common CLI inputs.

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
