.. _Reading/Writing From File or Stdin/Stdout:

=========================================
Reading/Writing From File or Stdin/Stdout
=========================================
In many CLI applications, it's common to be able to read from a file or stdin, and write to a file or stdout.
This allows for the chaining of many CLI applications via pipes ``|``.

---------
StdioPath
---------

.. note::
   :class:`~cyclopts.types.StdioPath` requires **Python 3.12+**.
   For older Python versions, see :ref:`Alternative Approach (Python < 3.12)` below.

The recommended approach is to use :class:`~cyclopts.types.StdioPath`, a :class:`~pathlib.Path` subclass that treats ``-`` as stdin (for reading) or stdout (for writing).
This follows `common Unix convention <https://clig.dev/#arguments-and-flags>`_ used by many command-line tools.

.. code-block:: python

   from cyclopts import App
   from cyclopts.types import StdioPath

   app = App()

   @app.default
   def scream(input_: StdioPath, output: StdioPath):
       """Uppercase all input data.

       Parameters
       ----------
       input_:
           Input file path, or "-" for stdin.
       output:
           Output file path, or "-" for stdout.
       """
       data = input_.read_text()
       output.write_text(data.upper())

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ echo "hello cyclopts users." > demo.txt

   $ python scream.py demo.txt -
   HELLO CYCLOPTS USERS.

   $ python scream.py demo.txt output.txt && cat output.txt
   HELLO CYCLOPTS USERS.

   $ echo "foo" | python scream.py - -
   FOO

:class:`~cyclopts.types.StdioPath` is pre-configured with ``allow_leading_hyphen=True``, so ``-`` can be passed as an argument without being interpreted as an option.

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Defaulting to Stdin/Stdout
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To make stdin/stdout the default when no argument is provided, use ``StdioPath("-")`` as the default value:

.. code-block:: python

   from cyclopts import App
   from cyclopts.types import StdioPath

   app = App()

   @app.default
   def scream(input_: StdioPath = StdioPath("-"), output: StdioPath = StdioPath("-")):
       """Uppercase all input data.

       Parameters
       ----------
       input_:
           Input file path. Defaults to stdin if not provided.
       output:
           Output file path. Defaults to stdout if not provided.
       """
       data = input_.read_text()
       output.write_text(data.upper())

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ echo "hello cyclopts users." > demo.txt

   $ python scream.py demo.txt
   HELLO CYCLOPTS USERS.

   $ python scream.py demo.txt output.txt && cat output.txt
   HELLO CYCLOPTS USERS.

   $ echo "foo" | python scream.py
   FOO

^^^^^^^^^^^^^
Binary Data
^^^^^^^^^^^^^

``StdioPath`` also supports binary reading and writing:

.. code-block:: python

   @app.default
   def process_binary(input_: StdioPath = StdioPath("-"), output: StdioPath = StdioPath("-")):
       data = input_.read_bytes()
       output.write_bytes(data)

Or using the context manager interface:

.. code-block:: python

   @app.default
   def process_binary(input_: StdioPath = StdioPath("-"), output: StdioPath = StdioPath("-")):
       with input_.open("rb") as f_in, output.open("wb") as f_out:
           f_out.write(f_in.read())

.. _Alternative Approach (Python < 3.12):

-------------------------------------
Alternative Approach (Python < 3.12)
-------------------------------------

For Python versions before 3.12, or when you prefer an ``Optional[Path]`` pattern where ``None`` indicates stdin/stdout, you can use helper functions:

.. code-block:: python

   import sys
   from cyclopts import App
   from pathlib import Path
   from typing import Optional

   def read_str(input_: Optional[Path]) -> str:
       return sys.stdin.read() if input_ is None else input_.read_text()

   def write_str(output: Optional[Path], data: str):
       sys.stdout.write(data) if output is None else output.write_text(data)

   def read_bytes(input_: Optional[Path]) -> bytes:
       return sys.stdin.buffer.read() if input_ is None else input_.read_bytes()

   def write_bytes(output: Optional[Path], data: bytes):
       sys.stdout.buffer.write(data) if output is None else output.write_bytes(data)

   app = App()

   @app.default
   def scream(input_: Optional[Path] = None, output_: Optional[Path] = None):
       """Uppercase all input data.

       Parameters
       ----------
       input_ : Optional[Path]
           If provided, read data from file. If not provided, read from stdin.
       output_ : Optional[Path]
           If provided, write data to file. If not provided, write to stdout.
       """
       data = read_str(input_)
       processed = data.upper()
       write_str(output_, processed)

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ echo "hello cyclopts users." > demo.txt
   $ python scream.py demo.txt
   HELLO CYCLOPTS USERS.
   $ python scream.py demo.txt output.txt
   $ cat output.txt
   HELLO CYCLOPTS USERS.
   $ echo "foo" | python scream.py
   FOO
