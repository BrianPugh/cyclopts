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

   if __name__ == "__main__":
       app()


.. code-block:: console

   $ python -m mypackage World
   Hello World!

-----------
Entrypoints
-----------
If you want your application to be callable like a standard bash executable (i.e. ``my-package`` instead of ``python -m mypackage``), we'll need to add an entrypoint_.

Modern Python projects typically use ``pyproject.toml`` for configuration. The standard way to define console scripts is:

.. code-block:: toml

   # pyproject.toml
   [project.scripts]
   my-package = "mypackage.__main__:app"

This creates an executable named ``my-package`` that executes the callable ``app`` object (from the right of the colon) from the python module ``mypackage.__main__``.
Note that this configuration is independent of any special naming, like ``__main__`` or ``app``.

^^^^^^^^^^^^^^^^^^^^^
Legacy Configurations
^^^^^^^^^^^^^^^^^^^^^

For older projects, you may encounter these alternative formats:

**setup.py:**

.. code-block:: python

    # setup.py
    from setuptools import setup

    setup(
        # There should be a lot more fields populated here.
        entry_points={
            "console_scripts": [
                "my-package = mypackage.__main__:app",
            ]
        },
    )

**setup.cfg:**

.. code-block:: cfg

    # setup.cfg
    [options.entry_points]
    console_scripts =
        my-package = mypackage.__main__:app

**Poetry:**

.. code-block:: toml

   # pyproject.toml
   [tool.poetry.scripts]
   my-package = "mypackage.__main__:app"

The setuptools entrypoint_ documentation goes into further detail.

.. _Result Action:

-------------
Result Action
-------------

When using Cyclopts as a CLI application, command return values are automatically handled appropriately. By default, :class:`~cyclopts.App` uses ``"print_non_int_sys_exit"`` mode, which calls :func:`sys.exit` with the appropriate exit code:

- String returns are printed to stdout, then :func:`sys.exit(0) <sys.exit>` is called
- Integer returns are passed to :func:`sys.exit(int) <sys.exit>` as the exit code
- Boolean returns are converted: :obj:`True` → :func:`sys.exit(0) <sys.exit>`, :obj:`False` → :func:`sys.exit(1) <sys.exit>`
- :obj:`None` returns call :func:`sys.exit(0) <sys.exit>`

This default behavior makes Cyclopts applications work consistently whether run directly as scripts or installed via `console_scripts entry points <https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts>`_. The :attr:`~cyclopts.App.result_action` can be customized if different behavior is needed:


.. _custom-return-code-protocol:

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Custom Return Code Protocol
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Whenever a built-in :attr:`~cyclopts.App.result_action` would otherwise use ``0`` as the exit code, Cyclopts checks the return value for a ``__cyclopts_returncode__`` method. If present, its return value is used as the exit code instead. This lets returned objects describe their own success/failure without forcing the CLI layer to translate them.

A common use case is a CLI that wraps a library and returns rich result objects directly, deferring presentation to the object's ``__rich__`` method:

.. code-block:: python

   from cyclopts import App


   class HealthCheck:
       def __init__(self, service: str, healthy: bool):
           self.service = service
           self.healthy = healthy

       def __rich__(self) -> str:
           status = "[green]OK[/green]" if self.healthy else "[red]FAIL[/red]"
           return f"{self.service}: {status}"

       def __cyclopts_returncode__(self) -> int:
           return 0 if self.healthy else 1


   app = App()


   @app.command
   def check(service: str) -> HealthCheck:
       """Check the health of a service."""
       return HealthCheck(service, healthy=ping(service))


   app()

.. code-block:: console

   $ my-script check database; echo "exit=$?"
   database: OK
   exit=0

   $ my-script check cache; echo "exit=$?"
   cache: FAIL
   exit=1

The protocol is opt-in: objects that don't define ``__cyclopts_returncode__`` continue to use the previous ``0`` default. The method must be a zero-argument callable that returns an :class:`int`; non-callable attributes are ignored. Branches that derive their exit code from an :class:`int` or :class:`bool` return value (e.g. ``sys.exit(result)``) ignore the protocol — return an integer/bool directly to set those exit codes.

Custom ``result_action`` callables can opt into the same protocol via :func:`cyclopts.resolve_returncode`:

.. code-block:: python

   import sys
   from typing import Any

   from cyclopts import App, resolve_returncode


   def result_action(result: Any) -> None:
       if isinstance(result, bool):
           sys.exit(0 if result else 1)
       if isinstance(result, int):
           sys.exit(result)
       if result is not None:
           print(result)
       sys.exit(resolve_returncode(result))


   app = App(result_action=result_action)


.. _Poetry: https://python-poetry.org
.. _entrypoint: https://setuptools.pypa.io/en/latest/userguide/entry_point.html#entry-points
