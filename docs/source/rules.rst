=====
Rules
=====
This page intends to serve as a terse list of rules Cyclopts follows for more ambiguous typing/situations.

Operations that are not allowed arise from overly-ambiguous CLI commands.

****
List
****

* Lists are only allowed for keyword arguments.

* For the CLI input, only one element will be added per keyword specified.

  .. code-block:: bash

     my-program --list-argument foo --list-argument bar

* If you want a positional list, use ``*args``.

* List nesting is not allowed. E.g. `List[List[int]]`

*****
Tuple
*****

* Currently not supported.

********
Iterable
********
* Will be interpreted the same as ``List``. The passed in data will be a ``list``. See List_ rules.

*****
Union
*****

* If an explicit ``coercion`` is not provided, the coercion will be interpreted based on the first non ``NoneType`` annotation.

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

* not supported