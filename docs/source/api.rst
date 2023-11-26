.. _API:

===
API
===

.. autoclass:: cyclopts.App
   :members: name, default, command, version_print, help_print, interactive_shell, parse_known_args, parse_args
   :special-members: __call__, __getitem__

.. autoclass:: cyclopts.Parameter
   :members:
   :exclude-members: get_negatives, show_

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

.. autoexception:: cyclopts.MultipleParameterAnnotationError
