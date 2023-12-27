==========
Validators
==========
In a CLI application, users have the freedom to input a wide range of data.
This flexibility can lead to inputs the application does not expect.
By coercing the input into a data type (like an ``int``), we are already limiting the input to a certain degree.
To further restrict the user input, you can populate the ``validator`` field in the :class:`Parameter <cyclopts.Parameter>`.

A validator is any callable object (such as a function) that has the signature:

.. code-block:: python

   def validator(type_, value: Any) -> None:
       pass  # Raise any exception here if ``value`` is invalid.

Validation happens after the data converter runs.
Any of ``AssertionError``, ``TypeError`` or ``ValidationError`` will be promoted into a :exc:`cyclopts.ValidationError`.
More than one validator can be supplied as a list to the ``validator`` field.

Cyclopts has some builtin common validators in the ``cyclopts.validators`` module.

------
Number
------
The :class:`Number <cyclopts.validators.Number>` validator can set minimum and maximum input values.

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

----
Path
----
The :class:`Path <cyclopts.validators.Path>` validator ensures certain properties
of the parsed ``pathlib.Path`` object, such as asserting the file must exist.

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
