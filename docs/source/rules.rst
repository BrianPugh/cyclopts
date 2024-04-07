.. _Coercion Rules:

==============
Coercion Rules
==============
This page intends to serve as a terse set of type coercion rules that Cyclopts follows.
If a specific type (including custom types) is not specified, the coercion defaults to ``type(token: str)``.
For example, Cyclopts does not have an explicit rule for :class:`pathlib.Path`, so if the value ``"foo.bin"`` is
provided, Cyclopts will default to coercing it as ``pathlib.Path("foo.bin")``.

Automatic coercion can always be overridden by the :attr:`.Parameter.converter` field.
Typically, the ``converter`` function will receive a single token, but it may receive multiple tokens
if the annotated type is iterable (e.g. :class:`list`, :class:`set`).

*******
No Hint
*******
If no explicit type hint is provided:

* If the parameter is optional and has a non-None default value, interpret the type ``type(default_value)``.

.. code-block:: python

   @app.default
   def default(value=5):
       print(f"{value=} {type(value)=}")

.. code-block:: console

   $ my-program 3
   value=3 type(value)=<class 'int'>

* Otherwise, interpret the type as string. See `Str`_.

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

***
Set
***
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

For a user provided token, a **case-insensitive name** lookup is performed.
If an enum name contains an underscore, the CLI parameter **may** instead contain a hyphen, ``-``.
Leading/Trailing underscores will be stripped.
TODO: refer to ``name_transform``.

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
