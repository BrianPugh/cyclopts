====================
Parameter Validators
====================
In a CLI application, users have the freedom to input a wide range of data.
This flexibility can lead to inputs the application does not expect.
By coercing the input into a data type (like an ``int``), we are already limiting the input to a certain degree.
To further restrict the user input, you can populate the ``validator`` field of :class:`.Parameter`.

A validator is any callable object (such as a function) that has the signature:

.. code-block:: python

   def validator(type_, value: Any) -> None:
       pass  # Raise any exception here if ``value`` is invalid.

Validation happens after the data converter runs.
Any of :exc:`AssertionError`, :exc:`TypeError` or :exc:`ValidationError` will be promoted to a :exc:`cyclopts.ValidationError`.
More than one validator can be supplied as a list to the ``validator`` field.

Cyclopts has some builtin common validators in the :ref:`cyclopts.validators <API Validators>` module.

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
   ╭─ Error ──────────────────────────────────────────────────────────╮
   │ Invalid value for --n. Must be < 16                              │
   ╰──────────────────────────────────────────────────────────────────╯

The following pre-defined annotated types are available in :mod:`cyclopts.types`:

.. code-block::

   PositiveFloat = Annotated[float, Parameter(validator=validators.Number(gt=0))]
   NonNegativeFloat = Annotated[float, Parameter(validator=validators.Number(gte=0))]
   NegativeFloat = Annotated[float, Parameter(validator=validators.Number(lt=0))]
   NonPositiveFloat = Annotated[float, Parameter(validator=validators.Number(lte=0))]

   PositiveInt = Annotated[int, Parameter(validator=validators.Number(gt=0))]
   NonNegativeInt = Annotated[int, Parameter(validator=validators.Number(gte=0))]
   NegativeInt = Annotated[int, Parameter(validator=validators.Number(lt=0))]
   NonPositiveInt = Annotated[int, Parameter(validator=validators.Number(lte=0))]

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
   ╭─ Error ─────────────────────────────────────────────────────────────────╮
   │ Invalid value for --path. this_file_does_not_exist.txt does not exist.  │
   ╰─────────────────────────────────────────────────────────────────────────╯

The following pre-defined annotated types are available in :mod:`cyclopts.types`:

.. code-block::

   Directory = Annotated[Path, Parameter(validator=validators.Path(file_okay=False))]
   File = Annotated[Path, Parameter(validator=validators.Path(dir_okay=False))]
   ExistingPath = Annotated[Path, Parameter(validator=validators.Path(exists=True))]
   ExistingDirectory = Annotated[Path, Parameter(validator=validators.Path(exists=True, file_okay=False))]
   ExistingFile = Annotated[Path, Parameter(validator=validators.Path(exists=True, dir_okay=False))]
