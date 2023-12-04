==========
Parameters
==========

Typically, Cyclopts gets all the information it needs from object names, type hints, or the function docstring:

.. code-block:: python

   import cyclopts

   app = cyclopts.App(help="This is help for the root application.")


   @app.command
   def foo(value: int):  # Cyclopts uses the ``value`` name and ``int`` type hint
       """Cyclopts uses this short description for help.

       Parameters
       ----------
       value: int
           Cyclopts uses this description for ``value``'s help.
       """


   app()

.. code-block:: console

   $ my-script --help
   Usage: my-script COMMAND

   This is help for the root application.

   ╭─ Commands ──────────────────────────────────────────────────────────────────────────╮
   │ foo  Cyclopts uses this short description for help.                                 │
   ╰─────────────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────────────────────────────────╮
   │ --version  Display application version.                                             │
   │ --help,-h  Display this message and exit.                                           │
   ╰─────────────────────────────────────────────────────────────────────────────────────╯

   $ my-script foo --help
   Usage: my-script [ARGS] [OPTIONS]

   Cyclopts uses this short description for help.

   ╭─ Parameters ────────────────────────────────────────────────────────────────────────╮
   │ *  VALUE,--value  Cyclopts uses this description for ``value``'s help. [required]   │
   ╰─────────────────────────────────────────────────────────────────────────────────────╯

This keeps the code as terse and clean as possible.
However, if more control is required, we can use :class:`Parameter <cyclopts.Parameter>` along with the builtin ``Annotated``.

.. code-block:: python

   from cyclopts import Parameter
   from typing_extensions import Annotated


   @app.command
   def foo(bar: Annotated[int, Parameter(...)]):
       pass

:class:`Parameter <cyclopts.Parameter>` gives complete control on how Cyclopts processes the annotated parameter.
See the API page for all configurable options.

----
Help
----
It's recommended to use docstrings for your parameter help, but if necessary, you can explicitly set a help string:

.. code-block:: python

   @app.command
   def foo(value: Annotated[int, Parameter(help="THIS IS USED.")]):
       """
       Parameters
       ----------
       value: int
           This description is not used; got overridden.
       """

.. code-block:: console

   $ my-script foo --help
   ╭─ Parameters ──────────────────────────────────────────────────╮
   │ *  VALUE,--value  THIS IS USED. [required]                    │
   ╰───────────────────────────────────────────────────────────────╯

----------
Converters
----------

Cyclopts has a powerful coercion engine that automatically converts CLI string tokens to the types hinted in a function signature.
However, sometimes a custom converter is required.

Lets consider a case where we want the user to specify a file size, and we want to allows suffixes like `"MB"`.

.. code-block:: python

   from cyclopts import App, Parameter
   from typing_extensions import Annotated
   from pathlib import Path

   app = App()

   mapping = {
       "kb": 1024,
       "mb": 1024 * 1024,
       "gb": 1024 * 1024 * 1024,
   }


   def byte_units(type_, *values):
       value = values[0].lower()
       try:
           return int(value)  # If this works, it didn't have a suffix.
       except ValueError:
           pass

       number, suffix = value[:-2], value[-2:]
       return int(number) * mapping[suffix]


   @app.command
   def zero(file: Path, size: Annotated[int, Parameter(converter=byte_units)]):
       """Creates a file of all-zeros."""
       print(f"Writing {size} zeros to {file}.")
       file.write_bytes(bytes(size))


   app()

.. code-block:: console

   $ my-script zero out.bin 100
   Writing 100 zeros to out.bin.

   $ my-script zero out.bin 1kb
   Writing 1024 zeros to out.bin.

   $ my-script zero out.bin 3mb
   Writing 3145728 zeros to out.bin.

The converter function gets the annotated type, and all the string tokens parsed for this argument.
The returned value gets used by the function.

----------------
Validating Input
----------------
Just because data is of the correct type, doesn't mean it's valid.
If we had a program that accepted an integer user age as an input, ``-1`` is an integer, but not a valid age.

.. code-block:: python

   def validate_age(type_, value):
       if value < 0:
           raise ValueError("Negative ages not allowed.")
       if value > 150:
           raise ValueError("You are too old to be using this application.")


   @app.default
   def allowed_to_buy_alcohol(age: int):
       if age < 21:
           print("Under 21: prohibited.")
       else:
           print("Good to go!")


   app()

.. code-block:: console

   $ my-script 30
   Good to go!

   $ my-script 10
   Under 21: prohibited.

   $ my-script -1
   ╭─ Error ──────────────────────────────────────────────────────────────────╮
   │ Invalid value for --age. Negative ages not allowed.                      │
   ╰──────────────────────────────────────────────────────────────────────────╯

   $ my-script 200
   ╭─ Error ──────────────────────────────────────────────────────────────────╮
   │ Invalid value for --age. You are too old to be using this application.   │
   ╰──────────────────────────────────────────────────────────────────────────╯
