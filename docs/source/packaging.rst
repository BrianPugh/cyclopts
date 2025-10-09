=========
Packaging
=========
Packaging is bundling up your python library so that it can be easily ``pip install`` by others.

Typically this involves:

1. Bundling the code into a Built Distribution (wheel) and/or Source Distribution (sdist).

2. Uploading (publishing) the distribution(s) to python package repository, like PyPI.

This section is a brief bootcamp on package **configuration** for a CLI application.
This is **not** intended to be a complete tutorial on python packaging and publishing.
In this tutorial, replace all instances of ``mypackage`` with your own project name.

---------------
\_\_main\_\_.py
---------------

In python, if you have a module ``mypackage/__main__.py``, it will be executed with the bash command ``python -m mypackage``.

A pretty bare-bones Cyclopts ``mypackage/__main__.py`` will look like:

.. code-block:: python

   # mypackage/__main__.py

   import cyclopts

   app = cyclopts.App()

   @app.command
   def foo(name: str):
       print(f"Hello {name}!")

   def main():
       app()

   if __name__ == "__main__":
       main()


.. code-block:: console

   $ python -m mypackage World
   Hello World!

In the current state, the :func:`main` function is an unnecessary extra level of indirection (could just directly call :obj:`app`), but it can sometimes offer you additional flexibility in the future if you need it.

-----------
Entrypoints
-----------
If you want your application to be callable like a standard bash executable (i.e. ``my-package`` instead of ``python -m mypackage``), we'll need to add an entrypoint_.
We'll investigate the setuptools solution, and the poetry solution.

^^^^^^^^^^
Setuptools
^^^^^^^^^^
``setup.py`` is a script at the root of your project that gets executed upon installation.
``setup.cfg`` and ``pyproject.toml`` are two other alternatives that are supported.

The following are all equivalent, **but should not be used at the same time**.
It is important that the function specified **takes no arguments**.

.. code-block:: python

    # setup.py

    from setuptools import setup

    setup(
        # There should be a lot more fields populated here.
        entry_points={
            "console_scripts": [
                "my-package = mypackage.__main__:main",
            ]
        },
    )

.. code-block:: toml

   # pyproject.toml
   [project.scripts]
   my-package = "mypackage.__main__:main"

.. code-block:: cfg

    # setup.cfg
    [options.entry_points]
    console_scripts =
        my-package = mypackage.__main__:main

All of these represent the same thing: create an executable named ``my-package`` that executes function ``main`` (from the right of the colon) from the python module ``mypackage.__main__``.
Note that this configuration is independent of any special naming, like ``__main__`` or ``main``.
The setuptools entrypoint_ documentation goes into further detail.

^^^^^^
Poetry
^^^^^^
Poetry_ is a tool for dependency management and packaging in Python (and what Cyclopts uses).
The syntax is very similar to setuptools:

.. code-block:: toml

   # pyproject.toml

   [tool.poetry.scripts]
   my-package = "mypackage.__main__:main"

.. _Result Action:

-------------
Result Action
-------------

When using Cyclopts as a CLI application (via `console_scripts entry points <https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts>`_), command return values are automatically handled appropriately. By default, :class:`~cyclopts.App` uses ``"print_non_int_return_int_as_exit_code"`` mode, which is designed for CLI usage and works correctly with console scripts out of the box.

Console scripts wrap your entry point with :func:`sys.exit`. Without proper handling:

- Returning a string to :func:`sys.exit("string") <sys.exit>` prints to stderr and exits with code 1 (error)
- Returning an integer to :func:`sys.exit(int) <sys.exit>` uses it as the exit code
- Returning :obj:`None` to :func:`sys.exit(None) <sys.exit>` exits with code 0 (success)

The default :attr:`~cyclopts.App.result_action` handles these cases correctly, but can be customized if needed:

^^^^^^^^^^^^^^^^^^
Boolean Handling
^^^^^^^^^^^^^^^^^^

All modes that return integers as exit codes automatically handle boolean values intuitively:

- :obj:`True` → exit code ``0`` (success)
- :obj:`False` → exit code ``1`` (failure)

This applies to: ``print_non_int_return_int_as_exit_code``, ``print_str_return_int_as_exit_code``, ``print_non_none_return_int_as_exit_code``, ``return_int_as_exit_code_else_zero``, and ``print_non_int_sys_exit``.

.. code-block:: python

   import cyclopts

   app = cyclopts.App()  # Uses default: print_non_int_return_int_as_exit_code

   @app.command
   def is_valid(path: str) -> bool:
       return Path(path).exists()

   exit_code = app(["is-valid", "/tmp"])  # Returns 0 if exists, 1 if not (no output)

^^^^^^^^^^^^^^^^^^^^^^^^
Custom Callable Handlers
^^^^^^^^^^^^^^^^^^^^^^^^

You can provide a custom callable as :attr:`~cyclopts.App.result_action` that receives the command's return value and can perform any custom processing:

.. code-block:: python

   import cyclopts

   def custom_handler(result):
       """Custom result handler that logs and transforms results."""
       if result is None:
           return 0
       elif isinstance(result, str):
           print(f"[OUTPUT] {result}")
           return 0
       elif isinstance(result, int):
           return result
       else:
           print(f"[RESULT] {result}")
           return 0

   app = cyclopts.App(result_action=custom_handler)

   @app.command
   def process(data: str) -> str:
       return f"Processed: {data}"

   exit_code = app(["process", "test"])  # Prints "[OUTPUT] Processed: test", returns 0

^^^^^^^^^^^^^^^^^
Recommended Setup
^^^^^^^^^^^^^^^^^

For CLI applications installed via `console_scripts <https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts>`_, point directly to the :class:`~cyclopts.App` object. The default :attr:`~cyclopts.App.result_action` (``"print_non_int_return_int_as_exit_code"``) handles return values appropriately for CLI usage:

.. code-block:: python

   # mypackage/cli.py

   import cyclopts

   app = cyclopts.App()

   @app.command
   def greet(name: str) -> str:
       return f"Hello {name}!"

.. code-block:: toml

   # pyproject.toml
   [project.scripts]
   my-package = "mypackage.cli:app"

^^^^^^^^^^^^^^^^^^^^^^^^
Testing CLI Applications
^^^^^^^^^^^^^^^^^^^^^^^^

When testing CLI applications with the default :attr:`~cyclopts.App.result_action`, you can:

1. Test CLI behavior by capturing stdout:

   .. code-block:: python

      from io import StringIO
      from contextlib import redirect_stdout

      def test_greet():
          buf = StringIO()
          with redirect_stdout(buf):
              exit_code = app(["greet", "Alice"])
          assert buf.getvalue() == "Hello Alice!\n"
          assert exit_code == 0

2. Create a test-specific :class:`~cyclopts.App` with ``result_action="return_value"``:

   .. code-block:: python

      import cyclopts

      def test_greet_return_value():
          test_app = cyclopts.App(result_action="return_value")
          test_app.update(app)  # Copy commands from CLI app

          result = test_app(["greet", "Alice"])
          assert result == "Hello Alice!"


.. _Poetry: https://python-poetry.org
.. _entrypoint: https://setuptools.pypa.io/en/latest/userguide/entry_point.html#entry-points
