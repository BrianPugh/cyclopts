.. _Coercion Rules:

==============
Coercion Rules
==============
This page intends to serve as a terse set of type coercion rules that Cyclopts follows.

Automatic coercion can always be overridden by the :attr:`.Parameter.converter` field.
Typically, the :attr:`~.Parameter.converter` function will receive a single token, but it may receive multiple tokens
if the annotated type is iterable (e.g. :class:`list`, :class:`set`).

*******
No Hint
*******
If no explicit type hint is provided:

* If the parameter has a **non-None** default value, interpret the type as ``type(default_value)``.

  .. code-block:: python

     from cyclopts import App

     app = App()

     @app.default
     def default(value=5):
         print(f"{value=} {type(value)=}")

     app()

  .. code-block:: console

     $ my-program 3
     value=3 type(value)=<class 'int'>

* Otherwise, :ref:`interpret the type as string <Coercion Rules - Str>`.

  .. code-block:: python

     from cyclopts import App

     app = App()

     @app.default
     def default(value):
         print(f"{value=} {type(value)=}")

     app()

  .. code-block:: console

     $ my-program foo
     value='foo' type(value)=<class 'str'>

***
Any
***
A standalone ``Any`` type hint is equivalent to `No Hint`_

.. _Coercion Rules - Str:

***
Str
***
No operation is performed, CLI tokens are natively strings.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def default(value: str):
       print(f"{value=} {type(value)=}")

   app()

.. code-block:: console

   $ my-program foo
   value='foo' type(value)=<class 'str'>

***
Int
***
For convenience, Cyclopts provides a richer feature-set of parsing integers than just naively calling ``int``.

* Accepts vanilla decimal values (e.g. `123`, `3.1415`). Floating-point values will be rounded prior to casting to an ``int``.
* Accepts binary values (strings starting with `0b`)
* Accepts octal values (strings starting with `0o`)
* Accepts hexadecimal values (strings starting with `0x`).

*****
Float
*****
Token gets cast as ``float(token)``. For example, ``float("3.14")``.

*******
Complex
*******
Token gets cast as ``complex(token)``. For example, ``complex("3+5j")``

****
Bool
****
1. If specified as a **keyword**, booleans are interpreted flags that take no parameter.
   The default **false-like** flag are ``--no-FLAG-NAME``.
   See :attr:`.Parameter.negative` for more about this feature.

   Example:

   .. code-block:: python

      from cyclopts import App

      app = App()

      @app.command
      def foo(my_flag: bool):
          print(my_flag)

      app()

   .. code-block:: console

       $ my-program foo --my-flag
       True

       $ my-program foo --no-my-flag
       False

2. If specified as a **positional** argument, a case-insensitive lookup is performed:

   * If the token is a **true-like value** ``{"yes", "y", "1", "true", "t"}``, then it is parsed as :obj:`True`.

   * If the token is a **false-like value** ``{"no", "n", "0", "false", "f"}``, then it is parsed as :obj:`False`.

   * Otherwise, a :exc:`CoercionError` will be raised.

   .. code-block:: console

      $ my-program foo 1
      True

      $ my-program foo 0
      False

      $ my-program foo not-a-true-or-false-value
      ╭─ Error ─────────────────────────────────────────────────╮
      │ Invalid value for "--my-flag": unable to convert        │
      │ "not-a-true-or-false-value" into bool.                  │
      ╰─────────────────────────────────────────────────────────╯


3. If specified as a keyword with a value attached with an ``=``, then the provided value will be parsed according to positional argument rules above (2).

  .. code-block:: python

     from cyclopts import App

     app = App()

     @app.command
     def foo(my_flag: bool):
         print(my_flag)

      app()

  .. code-block:: console

      $ my-program foo --my-flag=true
      True

      $ my-program foo --my-flag=false
      False

      $ my-program foo --no-my-flag=true
      False

      $ my-program foo --no-my-flag=false
      True


****
List
****
Unlike more simple types like :obj:`str` and :obj:`int`, lists use different parsing rules depending on whether the values are provided positionally or by keyword.

^^^^^^^^^^
Positional
^^^^^^^^^^
When arguments are provided positionally:

* If :attr:`Parameter.allow_leading_hyphen` is :obj:`False` (default behavior), reaching an option-like token will stop parsing for this parameter.
  If the number of consumed tokens is not a multiple of the required number of tokens to create an element of the list, a :exc:`MissingArgumentError` will be raised.

  .. code-block:: python

     from cyclopts import App

     app = App()

     @app.command
     def foo(values: list[int]):  # 1 CLI token per element
        print(values)

     @app.command
     def bar(values: list[tuple[int, str]]):  # 2 CLI tokens per element
        print(values)

     app()

  .. code-block:: console

     $ my-program foo 1 2 3
     [1, 2, 3]

     $ my-program bar 1 one 2 two
     [(1, 'one'), (2, 'two')]

     $ my-program bar 1 one 2
     ╭─ Error ─────────────────────────────────────────────────────╮
     │ Command "bar" parameter "--values" requires 2 arguments.    │
     │ Only got 1.                                                 │
     ╰─────────────────────────────────────────────────────────────╯

* If :attr:`Parameter.allow_leading_hyphen` is :obj:`True`, CLI tokens will be consumed unconditionally until exhausted.

  .. code-block:: python

     from cyclopts import App, Parameter
     from pathlib import Path
     from typing import Annotated

     app = App()

     @app.default
     def main(
        files: Annotated[list[Path], Parameter(allow_leading_hyphen=True)],
        some_flag: bool = False,
      ):
        print(f"{some_flag=}")
        print(f"Analyzing files {files}")

     app()

  .. code-block:: console

     $ my-program foo.bin bar.bin --fizz.bin buzz.bin --some-flag
     some_flag=True
     Analyzing files [PosixPath('foo.bin'), PosixPath('bar.bin'), PosixPath('--fizz.bin'), PosixPath('buzz.bin')]

  Known keyword arguments are parsed first (in this case, ``--some-flag``).
  To unambiguously pass in values positionally, provide them after a bare ``--``:

  .. code-block:: console

     $ my-program -- foo.bin bar.bin --fizz.bin buzz.bin --some-flag
     some_flag=False
     Analyzing files [PosixPath('foo.bin'), PosixPath('bar.bin'), PosixPath('--fizz.bin'), PosixPath('buzz.bin'), PosixPath('--some-flag')]


^^^^^^^
Keyword
^^^^^^^
When arguments are provided by keyword:

* Tokens will be consumed until enough data is collected to form the type-hinted object.

* The keyword can be specified multiple times.

* If :attr:`Parameter.allow_leading_hyphen` is :obj:`False` (default behavior), reaching an option-like token will raise :exc:`MissingArgumentError` if insufficient tokens have been parsed.

  .. code-block:: python

     from cyclopts import App

     app = App()

     @app.command
     def foo(values: list[int]):  # 1 CLI token per element
        print(values)

     @app.command
     def bar(values: list[tuple[int, str]]):  # 2 CLI tokens per element
        print(values)

     app()

  .. code-block:: console

     $ my-program foo --values 1 --values 2 --values 3
     [1, 2, 3]

     $ my-program bar --values 1 one --values 2 two
     [(1, 'one'), (2, 'two')]

     $ my-program bar --values 1 --values 2
     ╭─ Error ─────────────────────────────────────────────────────╮
     │ Command "bar" parameter "--values" requires 2 arguments.    │
     │ Only got 1.                                                 │
     ╰─────────────────────────────────────────────────────────────╯


* If :attr:`Parameter.consume_multiple` is :obj:`True`, all remaining tokens will be consumed (until an option-like token is reached if :attr:`Parameter.allow_leading_hyphen` is :obj:`False`)

  .. code-block:: python

     from cyclopts import App, Parameter
     from typing import Annotated

     app = App()

     @app.default
     def foo(values: Annotated[list[int], Parameter(consume_multiple=True)]):  # 1 CLI token per element
        print(values)

     app()

  .. code-block:: console

     $ my-program foo --values 1 2 3
     [1, 2, 3]

^^^^^^^^^^
Empty List
^^^^^^^^^^
Commonly, if we want a default list for a parameter in a function, we set the default value to ``None`` in the signature and then set it to the actual list in the function body:

.. code-block:: python

   def foo(extensions: Optional[list] = None):
      if extensions is None:
         extensions = [".png", ".jpg"]

We do this because mutable defaults is a `common unexpected source of bugs in python <https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments>`_.

However, sometimes we actually want to specify an empty list.
To get an empty list pass in the flag ``--empty-MY-LIST-NAME``.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(extensions: list | None = None):
      if extensions is None:
         extensions = [".png", ".jpg"]
      print(f"{extensions=}")

   app()

.. code-block:: console

   $ my-program
   extensions=['.png', '.jpg']

   $ my-program --empty-extensions
   extensions=[]

See :attr:`.Parameter.negative` for more about this feature.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Positional Only With Subsequent Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When a list is **positional-only**, it will consume tokens such that it leaves enough tokens for subsequent positional-only parameters.

.. code-block:: python

   from pathlib import Path
   from cyclopts import App

   app = App()

   @app.default
   def main(srcs: list[Path], dst: Path, /):  # "/" makes all prior parameters POSITIONAL_ONLY
       print(f"Processing files {srcs!r} to {dst!r}.")

   app()

.. code-block:: console

   $ my-program foo.bin bar.bin output.bin
   Processing files [PosixPath('foo.bin'), PosixPath('bar.bin')] to PosixPath('output.bin').


The console wildcard ``*`` is expanded by the console, so this example will naturally work with wildcards.

.. code-block:: console

   $ ls foo
   buzz.bin fizz.bin

   $ my-program foo/*.bin output.bin
   Processing files [PosixPath('foo/buzz.bin'), PosixPath('foo/fizz.bin')] to PosixPath('output.bin').


********
Iterable
********
Follows the same rules as `List`_. The passed in data will be a :class:`list`.

********
Sequence
********
Follows the same rules as `List`_. The passed in data will be a :class:`list`.

***
Set
***
Follows the same rules as `List`_, but the resulting datatype is a :class:`set`.

*********
Frozenset
*********
Follows the same rules as `Set`_, but the resulting datatype is a :class:`frozenset`.

*****
Tuple
*****
* The inner type hint(s) will be applied independently to each element. Enough CLI tokens will be consumed to populate the inner types.

* Nested fixed-length tuples are allowed: E.g. ``tuple[tuple[int, str], str]`` will consume 3 CLI tokens.

* Indeterminite-size tuples ``tuple[type, ...]`` are only supported at the root-annotation level and behave similarly to `List`_.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def default(coordinates: tuple[float, float, str]):
      print(f"{coordinates=}")

   app()

And invoke our script:

.. code-block:: console

   $ my-program --coordinates 3.14 2.718 my-coord-name
   coordinates=(3.14, 2.718, 'my-coord-name')

.. _Coercion Rules - Union:

****
Dict
****
Cyclopts can populate dictionaries using keyword dot-notation:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def default(message: str, *, mapping: dict[str, str] | None = None):
       if mapping:
           for find, replace in mapping.items():
               message = message.replace(find, replace)
       print(message)

   app()

.. code-block:: console

   $ my_program 'Hello Cyclopts users!'
   Hello Cyclopts users!

   $ my_program 'Hello Cyclopts users!' --mapping.Hello Hey
   Hey Cyclopts users!

   $ my_program 'Hello Cyclopts users!' --mapping.Hello Hey --mapping.users developers
   Hey Cyclopts developers!

Due to the way of specifying keys, it is recommended to make dict parameters keyword-only; dicts **cannot** be populated positionally.
If you do not wish for the user to be able to specify arbitrary keys, see `User-Defined Classes`_.
For specifying arbitrary keywords at the root level, see :ref:`kwargs <Args & Kwargs - Kwargs>`.

*****
Union
*****

The unioned types will be iterated **left-to-right** until a successful coercion is performed.
:obj:`None` type hints are ignored.

.. code-block:: python

   from cyclopts import App
   from typing import Union

   app = App()

   @app.default
   def default(a: Union[None, int, str]):
       print(type(a))

   app()

.. code-block:: console

    $ my-program 10
    <class 'int'>

    $ my-program bar
    <class 'str'>


********
Optional
********
``Optional[...]`` is syntactic sugar for ``Union[..., None]``.  See Union_ rules.

.. _Coercion Rules - Literal:

*******
Literal
*******
The :obj:`~typing.Literal` type is a good option for limiting user input to a set of choices.
Like Union_, the :obj:`~typing.Literal` options will be iterated **left-to-right** until a successful coercion is performed.
Cyclopts attempts to coerce the input token into the **type** of each :obj:`~typing.Literal` option.


.. code-block:: python

   from cyclopts import App
   from typing import Literal

   app = App()

   @app.default
   def default(value: Literal["foo", "bar", 3]):
       print(f"{value=} {type(value)=}")

   app()

.. code-block:: console

   $ my-program foo
   value='foo' type(value)=<class 'str'>

   $ my-program bar
   value='bar' type(value)=<class 'str'>

   $ my-program 3
   value=3 type(value)=<class 'int'>

   $ my-program fizz
   ╭─ Error ─────────────────────────────────────────────────╮
   │ Invalid value for "VALUE": unable to convert "fizz"     │
   │ into one of {'foo', 'bar', 3}.                          │
   ╰─────────────────────────────────────────────────────────╯


****
Enum
****
While `Literal`_ is the recommended way of providing the user a set of choices, another method is using :class:`~enum.Enum`.

The :attr:`Parameter.name_transform <cyclopts.Parameter.name_transform>` gets applied to all :class:`~enum.Enum` names, as well as the CLI provided token.
By default,this means that a **case-insensitive name** lookup is performed.
If an enum name contains an underscore, the CLI parameter **may** instead contain a hyphen, ``-``.
Leading/Trailing underscores will be stripped.

If coming from Typer_, **Cyclopts Enum handling is the reverse of Typer**.
Typer attempts to match the token to an Enum **value**; Cyclopts attempts to match the token to an Enum **name**.
This is done because generally the **name** of the enum is meant to be human readable, while the **value** has some program/machine significance.

As a real-world example, the PNG image format supports `5 different color-types <https://www.w3.org/TR/2003/REC-PNG-20031110/#6Colour-values>`_, which gets encoded into a `1-byte int in the image header <https://www.w3.org/TR/2003/REC-PNG-20031110/#11IHDR>`_.

.. code-block:: python

   from cyclopts import App
   from enum import IntEnum

   app = App()

   class ColorType(IntEnum):
       GRAYSCALE = 0
       RGB = 2
       PALETTE = 3
       GRAYSCALE_ALPHA = 4
       RGBA = 6

   @app.default
   def default(color_type: ColorType = ColorType.RGB):
       print(f"Writing color-type value: {color_type} to the image header.")

   app()

.. code-block:: console

   $ my-program
   Writing color-type value: 2 to the image header.

   $ my-program grayscale-alpha
   Writing color-type value: 4 to the image header.

****
Flag
****
:class:`~enum.Flag` enums (and by extension, :class:`~enum.IntFlag`) are treated as a collection of boolean flags.

The :attr:`Parameter.name_transform <cyclopts.Parameter.name_transform>` gets applied to all :class:`~enum.Flag` names, as well as the CLI provided token.
By default, this means that a **case-insensitive name** lookup is performed.
If an enum name contains an underscore, the CLI parameter **may** instead contain a hyphen, ``-``.
Leading/Trailing underscores will be stripped.

.. code-block:: python

   from cyclopts import App
   from enum import Flag, auto

   app = App()

   class Permission(Flag):
       READ = auto()
       WRITE = auto()
       EXECUTE = auto()

   @app.default
   def default(permissions: Permission = Permission.READ):
       print(f"Permissions: {permissions}")

   app()

.. code-block:: console

   $ my-program
   Permissions: Permission.READ

   $ my-program write
   Permissions: Permission.WRITE

   $ my-program read write
   Permissions: Permission.READ|WRITE

   $ my-program --permissions.write
   Permissions: Permission.WRITE

   $ my-program --permissions.write --permissions.read
   Permissions: Permission.READ|WRITE

.. note::
    If you want to directly expose the flags as booleans (e.g. ``--read``), then see :ref:`Namespace Flattening <Namespace Flattening>`.


.. _Coercion Rules - Dataclasses:

********
datetime
********

Cyclopts supports parsing timestamps into a :class:`~datetime.datetime` object. The supplied time must be in one of the following formats:

- ``%Y-%m-%d`` (e.g. 1956-01-31)
- ``%Y-%m-%dT%H:%M:%S`` (e.g. 1956-01-31T10:00:00)
- ``%Y-%m-%d %H:%M:%S``  (e.g. 1956-01-31 10:00:00)
- ``%Y-%m-%dT%H:%M:%S%z``  (e.g. 1956-01-31T10:00:00+0000)
- ``%Y-%m-%dT%H:%M:%S.%f``  (e.g. 1956-01-31T10:00:00.123456)
- ``%Y-%m-%dT%H:%M:%S.%f%z``  (e.g. 1956-01-31T10:00:00.123456+0000)


*********
timedelta
*********
Cyclopts supports parsing time durations into a :class:`~datetime.timedelta` object. The supplied time must be in one of the following formats:

- ``30s`` - 30 seconds
- ``5m`` - 5 minutes
- ``2h`` - 2 hours
- ``1d`` - 1 day
- ``3w`` - 3 weeks
- ``6M`` - 6 months (approximate)
- ``1y`` - 1 year (approximate)

Combining durations is also supported:

- "1h30m" - 1 hour and 30 minutes
- "1d12h" - 1 day and 12 hours

********************
User-Defined Classes
********************
Cyclopts supports classically defined user classes, as well as classes defined by the following dataclass-like libraries:

* `attrs <https://www.attrs.org/en/stable/>`_
* `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
* `NamedTuple <https://docs.python.org/3/library/typing.html#typing.NamedTuple>`_
* `pydantic <https://docs.pydantic.dev/latest/>`_
* `TypedDict <https://docs.python.org/3/library/typing.html#typing.TypedDict>`_

.. note::
   For ``pydantic`` classes, Cyclopts will *not* internally perform type conversions and instead relies on pydantic's coercion engine.

Subkey parsing allows for assigning values positionally and by keyword with a dot-separator.

.. code-block:: python

   from cyclopts import App
   from dataclasses import dataclass
   from typing import Literal

   app = App()

   @dataclass
   class User:
      name: str
      age: int
      region: Literal["us", "ca"] = "us"

   @app.default
   def main(user: User):
      print(user)

   app()

.. code-block:: console

   $ my-program --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   ╭─ Commands ──────────────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                                       │
   │ --version  Display application version.                                         │
   ╰─────────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────────────────────────────╮
   │ *  USER.NAME --user.name      [required]                                        │
   │ *  USER.AGE --user.age        [required]                                        │
   │    USER.REGION --user.region  [choices: us, ca] [default: us]                   │
   ╰─────────────────────────────────────────────────────────────────────────────────╯

   $ my-program 'Bob Smith' 30
   User(name='Bob Smith', age=30, region='us')

   $ my-program --user.name 'Bob Smith' --user.age 30
   User(name='Bob Smith', age=30, region='us')

   $ my-program --user.name 'Bob Smith' 30 --user.region=ca
   User(name='Bob Smith', age=30, region='ca')


Cyclopts will recursively search for :class:`~.Parameter` annotations and respect them:

.. code-block:: python

   from cyclopts import App, Parameter
   from dataclasses import dataclass
   from typing import Annotated

   app = App()

   @dataclass
   class User:
      # Beginning with "--" will completely override the parenting parameter name.
      name: Annotated[str, Parameter(name="--nickname")]
      # Not beginning with "--" will tack it on to the parenting parameter name.
      age: Annotated[int, Parameter(name="years-young")]

   @app.default
   def main(user: Annotated[User, Parameter(name="player")]):
      print(user)

   app()

.. code-block:: console

   $ my-program --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   ╭─ Commands ────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                 │
   │ --version  Display application version.                   │
   ╰───────────────────────────────────────────────────────────╯
   ╭─ Parameters ──────────────────────────────────────────────╮
   │ *  NICKNAME --nickname     [required]                     │
   │ *  PLAYER.YEARS-YOUNG      [required]                     │
   │      --player.years-young                                 │
   ╰───────────────────────────────────────────────────────────╯

^^^^^^^^^^^^^^^^^^^^
Namespace Flattening
^^^^^^^^^^^^^^^^^^^^
The special parameter name ``"*"`` will remove the immediate parameter's name from the dotted-hierarchal name:

.. code-block:: python

   from cyclopts import App, Parameter
   from dataclasses import dataclass
   from typing import Annotated

   app = App()

   @dataclass
   class User:
      name: str
      age: int

   @app.default
   def main(user: Annotated[User, Parameter(name="*")]):
      print(user)

   app()

.. code-block:: console

   $ my-program --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   ╭─ Commands ─────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.              │
   │ --version  Display application version.                │
   ╰────────────────────────────────────────────────────────╯
   ╭─ Parameters ───────────────────────────────────────────╮
   │ *  NAME --name  [required]                             │
   │ *  AGE --age    [required]                             │
   ╰────────────────────────────────────────────────────────╯

This can be used to conveniently share parameters between commands, and to create a global config object. See :ref:`Sharing Parameters`.

^^^^^^^^^^
Docstrings
^^^^^^^^^^
Docstrings from the class are used for the help page. Docstrings from the command have priority over class docstrings, if supplied:

.. code-block:: python

   from cyclopts import App
   from dataclasses import dataclass

   app = App()

   @dataclass
   class User:
      name: str
      "First and last name of the user."

      age: int
      "Age in years of the user."

   @app.default
   def main(user: User):
      """A short summary of what this program does.

      Parameters
      ----------
      user.age: int
         User's age docstring from the command docstring.
      """
      print(user)

   app()

.. code-block:: console

   $ my-program --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   A short summary of what this program does.

   ╭─ Commands ──────────────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                                       │
   │ --version  Display application version.                                         │
   ╰─────────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────────────────────────────╮
   │ *  USER.NAME --user.name  First and last name of the user. [required]           │
   │ *  USER.AGE --user.age    User's age docstring from the command docstring.      │
   │                           [required]                                            │
   ╰─────────────────────────────────────────────────────────────────────────────────╯


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Parameter(accepts_keys=False)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the class is annotated with ``Parameter(accepts_keys=False)``, then no dot-notation subkeys are exported.
The class parameter will consume enough tokens to populate the **required positional** arguments.

.. code-block:: python

   from cyclopts import App, Parameter
   from dataclasses import dataclass
   from typing import Annotated, Literal

   app = App()

   @dataclass
   class User:
      name: str
      age: int
      region: Literal["us", "ca"] = "us"

   @app.default
   def main(user: Annotated[User, Parameter(accepts_keys=False)]):
      print(user)

   app()

.. code-block:: console

   $ my-program --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   ╭─ Commands ─────────────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                                      │
   │ --version  Display application version.                                        │
   ╰────────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ───────────────────────────────────────────────────────────────────╮
   │ *  USER --user  [required]                                                     │
   ╰────────────────────────────────────────────────────────────────────────────────╯

   $ my-program 'Bob Smith' 27
   User(name='Bob Smith', age=27, region='us')

   $ my-program 'Bob Smith'
   ╭─ Error ────────────────────────────────────────────────────────────────────────╮
   │ Parameter "--user" requires 2 arguments. Only got 1.                           │
   ╰────────────────────────────────────────────────────────────────────────────────╯

In this example, we are unable to change the ``region`` parameter of ``User`` from the CLI.


.. _Typer: https://typer.tiangolo.com
