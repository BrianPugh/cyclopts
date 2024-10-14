.. _Coercion Rules:

==============
Coercion Rules
==============
This page intends to serve as a terse set of type coercion rules that Cyclopts follows.

Automatic coercion can always be overridden by the :attr:`.Parameter.converter` field.
Typically, the ``converter`` function will receive a single token, but it may receive multiple tokens
if the annotated type is iterable (e.g. :class:`list`, :class:`set`).

*******
No Hint
*******
If no explicit type hint is provided:

* If the parameter has a **non-None** default value, interpret the type as ``type(default_value)``.

  .. code-block:: python

     @app.default
     def default(value=5):
         print(f"{value=} {type(value)=}")

  .. code-block:: console

     $ my-program 3
     value=3 type(value)=<class 'int'>

* Otherwise, :ref:`interpret the type as string <Coercion Rules - Str>`.

  .. code-block:: python

     @app.default
     def default(value):
         print(f"{value=} {type(value)=}")

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

   @app.default
   def default(value: str):
       print(f"{value=} {type(value)=}")

.. code-block:: console

   $ my-program foo
   value='foo' type(value)=<class 'str'>

****
List
****
* The inner annotation type will be applied independently to each element.

* If ``Parameter.allow_leading_hyphen=False`` (default behavior), all tokens will be consumed until a hyphenated-option is reached.

* If ``Parameter.allow_leading_hyphen=True``, all remaining tokens will be unconditionally consumed.

.. code-block:: python

    @app.default
    def main(*, favorite_numbers: List[int]):
        pass

.. code-block:: console

   $ my-program --favorite-numbers 1 2 3
   # favorite_numbers argument is a list containing 3 integers: ``[1, 2, 3]``.

* To get an empty list pass in the flag ``--empty-MY-LIST-NAME``.
  Continuing the previous example:

  .. code-block:: console

     $ my-program --empty-favorite-numbers
     # favorite_numbers argument is an empty list: ``[]``.

  See :attr:`.Parameter.negative` for more about this feature.


********
Iterable
********
Follows the same rules as `List`_. The passed in data will be a list.

********
Sequence
********
Follows the same rules as `List`_. The passed in data will be a list.

***
Set
***
Follows the same rules as `List`_, but the resulting datatype is a :class:`set`.

*********
Frozenset
*********
Follows the same rules as `List`_, but the resulting datatype is a :class:`set`.

*****
Tuple
*****
* Parses the same number of tokens as the size of the annotated tuple.

* The inner annotation type will be applied independently to each element.

* Nested fixed-length tuples are allowed: E.g. ``Tuple[Tuple[int, str], str]`` will consume 3 CLI tokens.

* Indeterminite-size tuples ``Tuple[type, ...]`` are only supported at the root-annotation level and behave similarly to `List`_.

.. code-block:: python

  @app.default
  def default(coordinates: Tuple[float, float, str]):
      pass

And invoke our script:

.. code-block:: console

   $ my-program --coordinates 3.14 2.718 my-coord-name
   # coordinates argument is a tuple containing two floats and a string: ``(3.14, 2.718, "my-coord-name")``

.. _Coercion Rules - Union:

*****
Union
*****

The unioned types will be iterated left-to-right until a successful coercion is performed.
:obj:`None` type hints are ignored.

.. code-block:: python

      @app.default
      def default(a: Union[None, int, str]):
          print(type(a))

.. code-block:: console

    $ my-program 10
    <class 'int'>

    $ my-program bar
    <class 'str'>


********
Optional
********
``Optional[...]`` is syntactic sugar for ``Union[..., None]``.  See Union_ rules.

***
Int
***
For convenience, Cyclopts provides a richer feature-set of parsing integers than just naively calling ``int``.

* Accepts vanilla decimal values (e.g. `123`, `3.1415`). Floating-point values will be rounded prior to casting to an ``int``.
* Accepts hexadecimal values (strings starting with `0x`).
* Accepts binary values (strings starting with `0b`)

*****
Float
*****
Not explicitly handled by Cyclopts, token gets cast as ``float(token)``. For example, ``float("3.14")``.

*******
Complex
*******
Not explicitly handled by Cyclopts, token gets cast as ``complex(token)``. For example, ``complex("3+5j")``

****
Bool
****
1. If specified as a keyword, booleans are interpreted flags that take no parameter.
   The false-like flag name defaults to ``--no-FLAG-NAME``.
   See :attr:`.Parameter.negative` for more about this feature.

   Example:

   .. code-block:: python

     @app.command
     def foo(my_flag: bool):
         print(my_flag)

   .. code-block:: console

       $ my-program foo --my-flag
       True

       $ my-program foo --no-my-flag
       False

2. If specified as a positional argument, a case-insensitive lookup is performed.
   If the token is in the set of **false-like values** ``{"no", "n", "0", "false", "f"}``, then it is parsed as ``False``.
   If the token is in the set of **true-like values** ``{"yes", "y", "1", "true", "t"}``, then it is parsed as ``True``.
   Otherwise, a :exc:`CoercionError` will be raised.

   .. code-block:: console

       $ my-program foo 1
       True

       $ my-program foo 0
       False

3. If specified as a keyword with a value attached with an ``=``, then the provided value will be parsed according to positional argument rules above (2).
   Only the positive flag can be specified this way, attempting to assign a value to the negative value will result in a :exc:`ValidationError`.

  .. code-block:: python

    @app.command
    def foo(my_flag: bool):
        print(my_flag)

  .. code-block:: console

      $ my-program foo --my-flag=true
      True

      $ my-program foo --my-flag=false
      False

      $ my-program foo --no-my-flag=true
      ╭─ Error ───────────────────────────────────────────────────────────╮
      │ Cannot assign value to negative flag "--no-my-flag".              │
      ╰───────────────────────────────────────────────────────────────────╯

.. _Coercion Rules - Literal:

*******
Literal
*******
The :obj:`~typing.Literal` type is a good option for limiting the user input to a set of choices.
The :obj:`~typing.Literal` options will be iterated left-to-right until a successful coercion is performed.
Cyclopts attempts to coerce the input token into the **type** of each :obj:`~typing.Literal` option.


.. code-block:: python

   @app.default
   def default(value: Literal["foo", "bar", 3]):
       print(f"{value=} {type(value)=}")

.. code-block:: console

   $ my-program foo
   value='foo' type(value)=<class 'str'>

   $ my-program bar
   value='bar' type(value)=<class 'str'>

   $ my-program 3
   value=3 type(value)=<class 'int'>

   $ my-program fizz
   ╭─ Error ─────────────────────────────────────────────────────────────────────────╮
   │ Error converting value "fizz" to typing.Literal['foo', 'bar', 3] for "--value". │
   ╰─────────────────────────────────────────────────────────────────────────────────╯


****
Enum
****
While `Literal`_ is the recommended way of providing the user options, another method is using :class:`~enum.Enum`.

:attr:`Parameter.name_transform <cyclopts.Parameter.name_transform>` gets applied to all :class:`~enum.Enum` names, as well as the CLI provided token.
By default,this means that a **case-insensitive name** lookup is performed.
If an enum name contains an underscore, the CLI parameter **may** instead contain a hyphen, ``-``.
Leading/Trailing underscores will be stripped.

If coming from Typer_, **Cyclopts Enum handling is the reverse of Typer**.
Typer attempts to match the token to an Enum **value**; Cyclopts attempts to match the token to an Enum **name**.


.. code-block:: python

   class Language(str, Enum):
       ENGLISH = "en"
       SPANISH = "es"
       GERMAN = "de"


   @app.default
   def default(language: Language = Language.ENGLISH):
       print(f"Using: {language}")

.. code-block:: console

   $ my-program english
   Using: Language.ENGLISH

   $ my-program german
   Using: Language.GERMAN

   $ my-program french
   ╭─ Error ────────────────────────────────────────────────────────────────╮
   │ Error converting value "french" to <enum 'Language'> for "--language". │
   ╰────────────────────────────────────────────────────────────────────────╯

.. _Coercion Rules - Dataclasses:

********************
User-Defined Classes
********************
Cyclopts supports classically defined user classes, as well as classes defined by the following dataclass-like libraries:

* `attrs <https://www.attrs.org/en/stable/>`_
* `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
* `NamedTuple <https://docs.python.org/3/library/typing.html#typing.NamedTuple>`_
* `pydantic <https://docs.pydantic.dev/latest/>`_
* `TypedDict <https://docs.python.org/3/library/typing.html#typing.TypedDict>`_

.. note:
   For ``pydantic`` classes, Cyclopts will *not* internally perform type conversions and instead relies on pydantic's coercion engine.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
``Parameter(accepts_keys=None)`` (default)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Same behavior as ``Parameter(accepts_keys=True)``.

================================
``Parameter(accepts_keys=True)``
================================
Subkey parsing allows for assigning values positionally and by keyword with a dot-separator. Subkey parsing will respect positional-only as well as keyword-only inference from the function signature.

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


Cyclopts will recursively search for :class:`Parameter` annotations and respect them:

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

The special name ``"*"`` will remove the immediate parameter's name from the dotted-hierarchal name:

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

Docstrings from the class are used for the help page. Docstrings from the decorated command have priority, if supplied:

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


=================================
``Parameter(accepts_keys=False)``
=================================
If the class is annotated with ``Parameter(accepts_keys=False)``, then no dot-notation parameters are exported.
The class parameter will consume enough tokens to populate the required positional arguments.

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
