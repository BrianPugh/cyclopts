=======================
Keyword Multiple Values
=======================
In some applications, it is desirable to supply multiple values to a keyword argument.
For example, lets consider an application where we want to specify multiple input files.
We want our application to look like the following:

.. code-block:: console

   $ my-program output.bin --input input1.bin input2.bin input3.bin

Interpreted as:

.. code-block:: python

   output=PosixPath('output.bin')
   input=[PosixPath('input1.bin'), PosixPath('input2.bin'), PosixPath('input3.bin')]

In Typer, `it is impossible to accomplish this <https://github.com/pallets/click/issues/484>`_.
With Typer, the keyword must be specified before each value:

.. code-block:: console

   $ my-program output.bin --input input1.bin --input input2.bin --input input3.bin

By default, Cyclopts behavior mimics Typer, where a single element worth of CLI tokens are consumed.
However, by setting :attr:`.Parameter.consume_multiple` to :obj:`True`, multiple elements worth of CLI tokens will be consumed.
Consider the following example program with a single output path, and multiple input paths.

.. code-block:: python

   from cyclopts import App, Parameter
   from pathlib import Path
   from typing import Annotated

   app = App()

   @app.default
   def main(output: Path, input: Annotated[list[Path], Parameter(consume_multiple=True)]):
      print(f"{input=} {output=}")

   if __name__ == "__main__":
      app()

All of the following invocations are equivalent:

.. code-block:: console

   $ my-program output.bin input1.bin input2.bin input3.bin                         # Supplying arguments positionally.
   $ my-program output.bin --input input1.bin --input input2.bin --input input3.bin # Supplying input arguments via multiple keywords.
   $ my-program output.bin --input input1.bin input2.bin input3.bin                 # Supplying input arguments via a single keyword.
   $ my-program --input input1.bin input2.bin input3.bin --output output.bin        # Supplying all arguments via keywords.
   $ my-program --input input1.bin input2.bin input3.bin -- output.bin              # Using the POSIX convention to indicate the end of keywords

To set this configuration for your entire application, supply it to your root :attr:`.App.default_parameter`:

.. code-block:: python

   from cyclopts import App, Parameter

   app = App(default_parameter=Parameter(consume_multiple=True))
