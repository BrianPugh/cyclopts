=====
Rules
=====
This page intends to serve as a terse list of rules Cyclopts follows for more ambiguous typing/situations.

Operations that are not allowed arise from overly-ambiguous CLI commands.

****
List
****

* If provided as a keyword, only one element will be added per token pair.

  .. code-block:: bash

     my-program --list-argument foo --list-argument bar

* If you want a positional list, use ``*args``.

* List nesting is not allowed. E.g. `List[List[int]]`

*****
Tuple
*****


********
Iterable
********
* Will be interpreted the same as ``List``. The passed in data will be a ``list``. See List_ rules.

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
