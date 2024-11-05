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


.. _Poetry: https://python-poetry.org
.. _entrypoint: https://setuptools.pypa.io/en/latest/userguide/entry_point.html#entry-points
