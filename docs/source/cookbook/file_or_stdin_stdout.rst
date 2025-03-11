=========================================
Reading/Writing From File or Stdin/Stdout
=========================================
In many CLI applications, it's common to be able to read from a file or stdin, and write to a file or stdout.
This allows for the chaining of many CLI applications via pipes ``|``.
The following code demonstrates how to do this with Cyclopts:

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
