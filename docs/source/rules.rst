========================
Automatic Coercion Rules
========================
This page intends to serve as a terse list of rules Cyclopts follows for more ambiguous typing/situations.
If a specific type (including custom types) is not specified, the coercion defaults to ``type(token: str)``.
For example, cyclopts doesn't have an explicit rule for ``pathlib.Path``, so if the value ``"foo.bin"`` is
provided, Cyclopts will default to coercing it as ``pathlib.Path("foo.bin")``.

Automatic coercion can always be overridden via the ``converter`` field of ``Parameter``.
Typically, the ``converter`` function will receive a single token, but it may receive multiple tokens
if the annotated type is iterable (e.g. ``list``, ``set``).


****
List
****
* The inner annotation type will be applied independently to each element.
* If provided as a positional parameter, all remaining positional tokens will be consumed.
  + It is frequently more appropriate to use ``*args``.
* If provided as a keyword parameter, a single element will be added per token pair.
  For example, if we have a command:

  .. code-block:: python

      @app.default
      def main(favorite_numbers: List[int]):
          pass

  And invoke our script:

  .. code-block:: console

     my-program --favorite-numbers 1 --favorite-numbers 2

  The resulting ``favorite_numbers`` argument will be a list containing 2 integers: ``[1, 2]``.

********
Iterable
********
* Will be interpreted the same as ``List``. The passed in data will be a ``list``. See List_ rules.

*****
Tuple
*****
* Will parse the same number of tokens as the size of the annotated tuple.

  .. code-block:: python

    @app.default
    def main(coordinates: Tuple[float, float]):
        pass

  And invoke our script:

  .. code-block:: console

     my-program --coordinates 3.14 2.718

  The resulting ``favorite_numbers`` argument will be a list containing 2 integers: ``[1, 2]``.



*****
Union
*****

* The unioned types will be iterated over until a successful coercion is performed.

********
Optional
********

* ``Optional[...]`` is syntactic sugar for ``Union[..., None]``.  See Union_ rules.

***
int
***

* Accepts vanilla decimal values (e.g. `123`).
* Accepts hexadecimal values (strings starting with `0x`).
* Accepts binary values (strings starting with `0b`)

****
Enum
****

***
set
***
