==========================
Using ``pyproject.toml``
==========================
Let's create a CLI tool that is configurable via the user's ``pyproject.toml``. Think tools like Poetry_, Ruff_, and Codespell_.

----------------
Base Application
----------------
For this example, we'll be creating a simple CLI named ``compact`` that can compress data with either the ``zip`` or the ``lzma`` algorithm.

.. code-block:: python

   from cyclopts import App, Parameter
   from cyclopts.types import ExistingFile, File
   from typing import Annotated, Literal, Optional
   import lzma
   import zlib

   app = App(name="compact", help="Data compression tool.")


   @app.command
   def compress(src: ExistingFile, dst: Optional[File] = None, *, method: Literal["lzma", "zip"] = "zip"):
       """Compress a file."""
       data = src.read_bytes()
       if method == "lzma":
           out = lzma.compress(data)
       elif method == "zip":
           out = zlib.compress(data)
       else:
           raise NotImplementedError
       dst = dst or src.with_suffix(src.suffix + "." + method)
       dst.write_bytes(out)


   if __name__ == "__main__":
       app()

This application works as-is, but it may be useful for the caller to set the default ``method`` field from their ``pyproject.toml``.
More precisely, we want to be able to use the following configuration:

.. code-block:: toml

   # pyproject.toml
   [tool.compact.compress]
   method = "lzma"

------------------
Customizing Launch
------------------
First, we need to hook into the application launch process. In Cyclopts, this is done with the :ref:`Meta App` (an app that launches an app). The most basic meta-app is:

.. code-block:: python

   @app.meta.default
   def main(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       app(tokens)


   if __name__ == "__main__":
       app.meta()  # Call app.meta() instead of app()

For our purposes, we'll want to dive into the Cyclopts machinery a little further.

.. code-block:: python

   @app.meta.default
   def main(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       command, bound = app.parse_args(tokens)
       return command(*bound.args, **bound.kwargs)

``command`` is the actual python function to-be-executed.  ``bound`` is a :class:`~inspect.BoundArguments` object containing all the parsed & converted CLI arguments. It follows that ``command(*bound.args, **bound.kwargs)`` would execute the function with all of our supplied arguments.

-----------------------------
Reading in ``pyproject.toml``
-----------------------------
We now have an appropriate place to read ``pyproject.toml`` from the current working directory.
Add the following to the beginning of the ``main`` meta-app function:

.. code-block:: python

   import tomli  # Or you can just use ``toml`` in Python >=3.11

   try:
       with open("pyproject.toml", "rb") as f:
           config = tomli.load(f)["tool"]["compact"]  # Reads the [tool.compact] table.
   except (FileNotFoundError, KeyError):
       config = {}

``config`` will be empty if ``pyproject.toml`` does not exist, or if it does not contain a ``[tool.compact]`` table.

.. note::

   Many applications search the current working directory for ``pyproject.toml``, and will fallback to searching parenting directories until a ``pyproject.toml`` is found. Here's a snippet for that:


   .. code-block::

      from pathlib import Path

      def find_pyproject() -> Path:
          """Searches current directory, then parenting directories until a pyproject.toml is found."""
          for parent in Path("pyproject.toml").absolute().parents:
              if (candidate := parent / path.name).exists():
                  return candidate
          raise FileNotFoundError("Cannot find a pyproject.toml")

--------------------------
Getting the command string
--------------------------
We want to dynamically parse what sub-table of the config we need to access based on the command being executed.
The :meth:`~.App.parse_commands` method returns a bunch of data; the first returned element is a list of strings containing the parsed command names.

.. code-block:: python

    command_names, _, _ = app.parse_commands(tokens)

If we invoked our program:

.. code-block:: console

   $ python compact.py compress foo.bin

Then the resulting ``command_names`` would be ``["compress"]``.

We can now access the config for this specific subcommand:

.. code-block:: python

    for command_name in command_names:
        config = config.get(command_name, {})

------------------------
Updating bound arguments
------------------------
Finally, we need to set these values as defaults to the :attr:`bound.arguments <inspect.BoundArguments.arguments>` dictionary.
We don't want to simply update the dictionary, as that would mean our toml-configured values would overwrite CLI-provided values. Using :meth:`dict.setdefault` will only set values for previously non-existent keys.

.. code-block:: python

    # Update the bound arguments for unset keys:
    for key, value in config.items():
        bound.arguments.setdefault(key, value)

.. warning::

   You are responsible to correctly interpreting/coercing data types from non-cli sources to the correct type.
   E.g. A value from ``toml`` may be a string, but the function might be expecting a :class:`~pathlib.Path` object.

----------
Final Code
----------
Putting it all together, here's the complete copy/pastable example code:

.. code-block:: python

   from cyclopts import App, Parameter
   from cyclopts.types import ExistingFile, File
   from typing import Annotated, Literal, Optional
   import tomli
   import lzma
   import zlib

   app = App(name="compact", help="Data compression tool.")


   @app.command
   def compress(src: ExistingFile, dst: Optional[File] = None, *, method: Literal["lzma", "zip"] = "zip"):
       """Compress a file."""
       data = src.read_bytes()
       if method == "lzma":
           out = lzma.compress(data)
       elif method == "zip":
           out = zlib.compress(data)
       else:
           raise NotImplementedError
       dst = dst or src.with_suffix(src.suffix + "." + method)
       dst.write_bytes(out)


   @app.meta.default
   def main(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
       try:
           with open("pyproject.toml", "rb") as f:
               config = tomli.load(f)["tool"]["compact"]
       except (FileNotFoundError, KeyError):
           config = {}

       # The main Cyclopts parsing/conversion
       command, bound = app.parse_args(tokens)

       # Get the config dictionary for the specified command.
       command_names, _, _ = app.parse_commands(tokens)
       for command_name in command_names:
           config = config.get(command_name, {})

       # Update the bound arguments for unset keys:
       for key, value in config.items():
           bound.arguments.setdefault(key, value)

       # Actual function execution.
       return command(*bound.args, **bound.kwargs)


   if __name__ == "__main__":
       app.meta()


.. _Poetry: https://github.com/python-poetry/poetry
.. _Ruff: https://github.com/astral-sh/ruff
.. _Codespell: https://github.com/codespell-project/codespell
