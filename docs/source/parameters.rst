==========
Parameters
==========

Typically, Cyclopts gets all the information it needs from object names, type hints, and the function docstring:

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

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ foo        Cyclopts uses this short description for help.           │
   │ --help,-h  Display this message and exit.                           │
   │ --version  Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯

   $ my-script foo --help
   Usage: my-script [ARGS] [OPTIONS]

   Cyclopts uses this short description for help.

   ╭─ Parameters ────────────────────────────────────────────────────────────────────────╮
   │ *  VALUE,--value  Cyclopts uses this description for ``value``'s help. [required]   │
   ╰─────────────────────────────────────────────────────────────────────────────────────╯

This keeps the code as clean and terse as possible.
However, if more control is required, we can provide additional information by annotating type hints with :class:`.Parameter`.

.. code-block:: python

   from cyclopts import Parameter
   from typing import Annotated

   @app.command
   def foo(bar: Annotated[int, Parameter(...)]):
       pass

   app()

:class:`.Parameter` gives complete control on how Cyclopts processes the annotated parameter.
See the :ref:`API` page for all configurable options.
This page will investigate some of the more common use-cases.

------
Naming
------
Like :ref:`command names <Command Changing Name>`, CLI parameter names are derived from their python counterparts.
However, sometimes customization is needed.

.. _Parameters - Naming - Manual Naming:

^^^^^^^^^^^^^
Manual Naming
^^^^^^^^^^^^^
Parameter names (and their short forms) can be manually specified:

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   @app.default
   def main(
       *,
       foo: Annotated[str, Parameter(name=["--foo", "-f"])],  # Adding a short-form
       bar: Annotated[str, Parameter(name="--something-else")],
   ):
       pass

   app()

.. code-block:: console

   $ my-script --help

   Usage: main COMMAND [OPTIONS]
   ╭─ Commands ──────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.               │
   │ --version  Display application version.                 │
   ╰─────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────╮
   │ *  --foo             -f  [required]                     │
   │ *  --something-else      [required]                     │
   ╰─────────────────────────────────────────────────────────╯

Manually set names via :attr:`Parameter.name <cyclopts.Parameter.name>` are not subject to :attr:`Parameter.name_transform <cyclopts.Parameter.name_transform>`.


^^^^^^^^^^^^^^
Name Transform
^^^^^^^^^^^^^^
The name transform function that converts the python variable name to it's CLI counterpart can be configured by setting :attr:`Parameter.name_transform <cyclopts.Parameter.name_transform>` (defaults to :func:`.default_name_transform`).

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   def name_transform(s: str) -> str:
       return s.upper()

   @app.default
   def main(
       *,
       foo: Annotated[str, Parameter(name_transform=name_transform)],
       bar: Annotated[str, Parameter(name_transform=name_transform)],
   ):
       pass

   app()

.. code-block:: console

   $ my-script --help
   Usage: main COMMAND [OPTIONS]

   ╭─ Commands ──────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.               │
   │ --version  Display application version.                 │
   ╰─────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────╮
   │ *  --FOO  [required]                                    │
   │ *  --BAR  [required]                                    │
   ╰─────────────────────────────────────────────────────────╯

Notice how the parameter is now ``--FOO`` instead of the standard ``--foo``.

.. note:
   The returned string is **before** the standard ``--`` is prepended.

Generally, it is not very useful to set the name transform on **individual** parameters; it would be easier/clearer :ref:`to manually specify the name <Parameters - Naming - Manual Naming>`.
However, we can change the default name transform for the **entire app** by configuring the app's :ref:`default_parameter <Default Parameter>`.

To change the :attr:`~cyclopts.Parameter.name_transform` across your entire app, add the following to your :class:`~cyclopts.App` configuration:

.. code-block:: python

   app = App(
       default_parameter=Parameter(name_transform=my_custom_name_transform),
   )

----
Help
----
It is recommended to use docstrings for your parameter help, but if necessary, you can explicitly set a help string:

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

.. _Converters:

----------
Converters
----------

Cyclopts has a powerful coercion engine that automatically converts CLI string tokens to the types hinted in a function signature.
However, sometimes a custom :attr:`~.Parameter.converter` is required.

Lets consider a case where we want the user to specify a file size, and we want to allows suffixes like `"MB"`.

.. code-block:: python

   from cyclopts import App, Parameter, Token
   from typing import Annotated
   from pathlib import Path

   app = App()

   mapping = {
       "kb": 1024,
       "mb": 1024 * 1024,
       "gb": 1024 * 1024 * 1024,
   }

   def byte_units(type_, tokens: list[Token]) -> int:
       # type_ is ``int``,
       value = tokens[0].value.lower()
       try:
           return type_(value)  # If this works, it didn't have a suffix.
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

The converter function gets the annotated type, and the :class:`.Token` s parsed for this argument.
The returned value is supplied to the parameter for the function.

----------------
Validating Input
----------------
Just because data is of the correct type, doesn't mean it's valid.
If we had a program that accepts integer user age as an input, ``-1`` is an integer, but not a valid age.

.. code-block:: python

   from cyclopts import App, Parameter
   from typing import Annotated

   app = App()

   def validate_age(type_, value):
       if value < 0:
           raise ValueError("Negative ages not allowed.")
       if value > 150:
           raise ValueError("You are too old to be using this application.")

   @app.default
   def allowed_to_buy_alcohol(age: Annotated[int, Parameter(validator=validate_age)]):
       print("Under 21: prohibited." if age < 21 else "Good to go!")

   app()

.. code-block:: console

   $ my-script 30
   Good to go!

   $ my-script 10
   Under 21: prohibited.

   $ my-script -1
   ╭─ Error ──────────────────────────────────────────────────────────────────────╮
   │ Invalid value "-1" for "AGE". Negative ages not allowed.                     │
   ╰──────────────────────────────────────────────────────────────────────────────╯

   $ my-script 200
   ╭─ Error ──────────────────────────────────────────────────────────────────────╮
   │ Invalid value "200" for "AGE". You are too old to be using this application. │
   ╰──────────────────────────────────────────────────────────────────────────────╯

Certain builtin error types (:exc:`ValueError`, :exc:`TypeError`, :exc:`AssertionError`) will be re-interpreted by Cyclopts and formatted into a prettier message for the application user.

--------------------
Parameter Resolution
--------------------
Cyclopts can combine multiple :class:`.Parameter` annotations together.
Say you want to define a new :obj:`int` type that uses the :ref:`byte-centric converter from above<Converters>`.

We can define the type:

.. code-block:: python

   ByteSize = Annotated[int, Parameter(converter=byte_units)]

We can then either directly annotate a function parameter with this:

.. code-block:: python

   @app.command
   def zero(size: ByteSize):
       pass

or even stack annotations to add additional features, like a validator:

.. code-block:: python

   def must_be_multiple_of_4096(type_, value):
       assert value % 4096 == 0, "Size must be a multiple of 4096"


   @app.command
   def zero(size: Annotated[ByteSize, Parameter(validator=must_be_multiple_of_4096)]):
       pass

Python interprets this type annotation as:

.. code-block:: python

   Annotated[ByteSize, Parameter(converter=byte_units), Parameter(validator=must_be_multiple_of_4096)]

Cyclopts will search **right-to-left** for **set** parameter attributes until one is found. I.e. right-most parameter attributes have the highest priority.

.. code-block:: console

   $ my-script 1234
   ╭─ Error ──────────────────────────────────────────────────────────────────────╮
   │ Invalid value "1234" for "SIZE". Size must be a multiple of 4096             │
   ╰──────────────────────────────────────────────────────────────────────────────╯

See :ref:`Parameter Resolution Order<Parameter Resolution Order>` for more details.
