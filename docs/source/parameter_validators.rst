.. _Parameter Validators:

====================
Parameter Validators
====================
In CLI applications, users have the freedom to input a wide range of data.
This flexibility can lead to inputs the application does not expect.
By coercing the input into a data type (like an :obj:`int`), we are already limiting the input to a certain degree (e.g. "foo" cannot be coerced into an integer).
To further restrict the user input, you can populate the :attr:`~.Parameter.validator` field of :class:`.Parameter`.

A validator is any callable object (such as a function) that has the signature:

.. code-block:: python

   def validator(type_, value: Any) -> None:
       pass  # Raise any exception here if ``value`` is invalid.

Validation happens **after** the data converter runs.
Any of :exc:`AssertionError`, :exc:`TypeError` or :exc:`ValidationError` will be promoted to a :exc:`cyclopts.ValidationError` so that the exception gets presented to the end-user in a nicer way.
More than one validator can be supplied as a list to the :attr:`~.Parameter.validator` field.

Cyclopts has some builtin common validators in the :ref:`cyclopts.validators <API Validators>` module.
See :ref:`Annotated Types` for common specific definitions provided as convenient pre-annotated types.

----
Path
----
The :class:`.Path` validator ensures certain properties
of the parsed :class:`pathlib.Path` object, such as asserting the file must exist.

.. code-block:: python

   from cyclopts import App, Parameter, validators
   from typing import Annotated
   from pathlib import Path

   app = App()

   @app.default()
   def foo(path: Annotated[Path, Parameter(validator=validators.Path(exists=True))]):
       print(f"File contents:\n{path.read_text()}")

   app()

.. code-block:: console

   $ echo Hello World > my_file.txt

   $ my-script my_file.txt
   File contents:
   Hello World

   $ my-script this_file_does_not_exist.txt
   ╭─ Error ────────────────────────────────────────────────────────────╮
   │ Invalid value "this_file_does_not_exist.txt" for "PATH".           │
   │ "this_file_does_not_exist.txt" does not exist.                     │
   ╰────────────────────────────────────────────────────────────────────╯

See :ref:`Annotated Path Types <Annotated Path Types>` for Annotated-Type equivalents of common Path converter/validators.

------
Number
------
The :class:`.Number` validator can set minimum and maximum input values.

.. code-block:: python

   from cyclopts import App, Parameter, validators
   from typing import Annotated

   app = App()

   @app.default()
   def foo(n: Annotated[int, Parameter(validator=validators.Number(gte=0, lt=16))]):
       print(f"Your number in hex is {str(hex(n))[2]}.")

   app()

.. code-block:: console

   $ my-script 0
   Your number in hex is 0.

   $ my-script 15
   Your number in hex is f.

   $ my-script 16
   ╭─ Error ────────────────────────────────────────────────────────────╮
   │ Invalid value "16" for "N". Must be < 16.                          │
   ╰────────────────────────────────────────────────────────────────────╯

See :ref:`Annotated Number Types <Annotated Number Types>` for Annotated-Type equivalents of common Number converter/validators.
