===
API
===

.. autoclass:: cyclopts.App
   :members: default, command, version_print, help_print, interactive_shell
   :special-members: __call__

.. autoclass:: cyclopts.Parameter

.. autofunction:: cyclopts.coerce

----------
Exceptions
----------

.. autoexception:: cyclopts.CycloptsError
   :show-inheritance:

.. autoexception:: cyclopts.ValidationError
   :show-inheritance:

.. autoexception:: cyclopts.CoercionError
   :show-inheritance:

.. autoexception:: cyclopts.InvalidCommandError
   :show-inheritance:

.. autoexception:: cyclopts.UnusedCliTokensError
   :show-inheritance:

.. autoexception:: cyclopts.MissingArgumentError
   :show-inheritance:

.. autoexception:: cyclopts.CommandCollisionError

.. autoexception:: cyclopts.MultipleParameterAnnotationError
