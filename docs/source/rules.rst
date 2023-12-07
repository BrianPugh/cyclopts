.. _Coercion Rules:

==============
Coercion Rules
==============
This page intends to serve as a terse set of type coercion rules that Cyclopts follows.
If a specific type (including custom types) is not specified, the coercion defaults to ``type(token: str)``.
For example, Cyclopts does not have an explicit rule for ``pathlib.Path``, so if the value ``"foo.bin"`` is
provided, Cyclopts will default to coercing it as ``pathlib.Path("foo.bin")``.

Automatic coercion can always be overridden by the ``converter`` field of :class:`Parameter <cyclopts.Parameter>`.
Typically, the ``converter`` function will receive a single token, but it may receive multiple tokens
if the annotated type is iterable (e.g. ``list``, ``set``).

*******
No Hint
*******
If no explicit type hint is provided, the token will be parsed as a string. See `Str`_.

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
Data will be treated as a string. See `Str`_.

.. code-block:: python

   @app.default
   def default(value: Any):
       print(f"{value=} {type(value)=}")

.. code-block:: console

   $ my-program foo
   value='foo' type(value)=<class 'str'>

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

* If provided as a positional parameter, all remaining positional tokens will be consumed.

  + It is frequently more appropriate to use ``*args`` to consume all remaining posiitonal tokens.
    See :ref:`Args & Kwargs`.

* If provided as a keyword parameter, a single element will be added per use.

  Example:

  .. code-block:: python

      @app.default
      def main(favorite_numbers: List[int]):
          pass

  .. code-block:: console

     $ my-program --favorite-numbers 1 --favorite-numbers 2
     # favorite_numbers argument is a list containing 2 integers: ``[1, 2]``.

* To get an empty list pass in the flag ``--empty-MY-LIST-NAME``.
  Continuing the previous example:

  .. code-block:: console

     $ my-program --empty-favorite-numbers
     # favorite_numbers argument is an empty list: ``[]``.

  See the ``negative`` field of :class:`Parameter <cyclopts.Parameter>` for more about this feature.


********
Iterable
********
Follows the same rules as `List`_. The passed in data will be a list.

***
Set
***
Follows the same rules as `List`_, but the resulting datatype is a ``set``.

*****
Tuple
*****
A Tuple will parse the same number of tokens as the size of the annotated tuple.

.. code-block:: python

  @app.default
  def default(coordinates: Tuple[float, float, str]):
      pass

And invoke our script:

.. code-block:: console

   my-program --coordinates 3.14 2.718 my-coord-name
   # coordinates argument is a tuple containing two floats and a string: ``(3.14, 2.718, "my-coord-name")``

.. _Coercion Rules - Union:

*****
Union
*****

The unioned types will be iterated left-to-right until a successful coercion is performed.
``None`` type hints are ignored.

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

* Accepts vanilla decimal values (e.g. `123`, `3.1415`).
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
* If specified as a keyword, booleans get converted into flags that take no parameter.
  The false-like flag defaults to ``--no-FLAG-NAME``.
  See the ``negative`` field of :class:`Parameter <cyclopts.Parameter>` for more about this feature.

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

* If specified as a positional argument, a case-insensitive lookup is performed.
  If the token is in the set of false-like values ``{"no", "n", "0", "false", "f"}``, then it is parsed as ``False``.
  Otherwise, the value is interpreted as ``True``.

  .. code-block:: console

      $ my-program foo 1
      True

      $ my-program foo 0
      False

.. _Coercion Rules - Literal:

*******
Literal
*******
The ``Literal`` type is a good option for limiting the user input to a set of choices.
The ``Literal`` options will be iterated left-to-right until a successful coercion is performed.
Cyclopts attempts to coerce the input token into the **type** of each ``Literal`` option.


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
While `Literal`_ is the recommended way of providing the user options, another method is using ``Enum``.

For a user provided token, a **case-insensitive name** lookup is performed.
If an enum name contains an underscore, the CLI parameter may instead contain a hyphen, ``-``.
Leading/Trailing underscores will be stripped.

If coming from Typer_, **Cyclopts Enum handling is reversed compared to Typer**.
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


.. _Typer: https://typer.tiangolo.com
