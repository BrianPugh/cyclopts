======
Groups
======
Groups offer a way to organize parameters and command on the help-page.
Additionally, they also offer an additional layer of logic that converters and validators can operate on.

Groups can be specified in 2 ways:
1. Creating an instance of the :class:`cyclopts.Group` object.
2. Implicitly with just a string identifier.

----------
Converters
----------
A converter is any callable object (such as a function) that has signature:

.. code-block:: python

   def converter(**kwargs: Any) -> Dict[str, Any]:
       # This is a no-op converter
       return kwargs

Parsed and converted arguments belonging to the group will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature.
The python variable names will be used, which may differ from their CLI names.

The returned dictionary will be used for subsequent execution.

----------
Validators
----------
A validator is any callable object (such as a function) that has signature:

.. code-block:: python

   def validator(**kwargs: Any):
       pass  # Raise any exception here if ``kwargs`` is invalid.

Parsed and converted arguments belonging to the group will be keyword-unpacked, regardless of their positional/keyword-type in the command function signature.
The python variable names will be used, which may differ from their CLI names.
