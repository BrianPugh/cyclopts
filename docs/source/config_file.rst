.. _Config Files:

============
Config Files
============
For more complicated CLI applications, it is common to have an external user configuration file. For example, the popular python tools ``poetry``, ``ruff``, and ``pytest`` are all configurable from a ``pyproject.toml`` file. The :attr:`App.config <cyclopts.App.config>` attribute accepts a `callable <https://docs.python.org/3/glossary.html#term-callable>`_ (or list of callables) that add (or remove) values to the parsed CLI tokens. The provided callable must have signature:

.. code-block:: python

   def config(apps: List["App"], commands: Tuple[str, ...], arguments: ArgumentCollection):
       """Modifies the argument collection inplace with some injected values.

       Parameters
       ----------
       apps: Tuple[App, ...]
          The application hierarchy that led to the current command function.
          The current command app is the last element of this tuple.
       commands: Tuple[str, ...]
          The CLI strings that led to the current command function.
       arguments: ArgumentCollection
          Complete ArgumentCollection for the app.
          Modify this collection inplace to influence values provided to the function.
       """
       ...

The provided ``config`` does not have to be a function; all the Cyclopts builtin configs are classes that implement the ``__call__`` method. The Cyclopts builtins offer good standard functionality for common configuration files like yaml or toml.

.. _TOML Example:

------------
TOML Example
------------
In this example, we create a small CLI tool that counts the number of times a given character occurs in a file.

.. code-block:: python

   # character-counter.py
   import cyclopts
   from cyclopts import App
   from pathlib import Path

   app = App(
       name="character-counter",
       config=cyclopts.config.Toml(
           "pyproject.toml",  # Name of the TOML File
           root_keys=["tool", "character-counter"],  # The project's namespace in the TOML.
           # If "pyproject.toml" is not found in the current directory,
           # then iteratively search parenting directories until found.
           search_parents=True,
       ),
   )

   @app.command
   def count(filename: Path, *, character="-"):
       print(filename.read_text().count(character))

   if __name__ == "__main__":
       app()

Running this code without a ``pyproject.toml`` present:

.. code-block:: console

   $ python character-counter.py count README.md
   70
   $ python character-counter.py count README.md --character=t
   380

We can have the new default character be ``t`` by adding the following to ``pyproject.toml``:

.. code-block:: toml

   [tool.character-counter.count]
   character = "t"

Rerunning the app without a specified ``--character`` will result in using the toml-provided value:

.. code-block:: console

   $ python character-counter.py count README.md
   380

--------------------------
User-Specified Config File
--------------------------
Extending the above :ref:`TOML Example`, what if we want to allow the user to specify the toml configuration file?
This can be accomplished via a :ref:`Meta App`.

.. code-block:: python

    # character-counter.py
    from pathlib import Path
    from typing import Annotated

    import cyclopts
    from cyclopts import App, Parameter

    app = App(name="character-counter")

    @app.command
    def count(filename: Path, *, character="-"):
        print(filename.read_text().count(character))

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        config: Path = Path("pyproject.toml"),
    ):
        app.config = cyclopts.config.Toml(
            config,
            root_keys=["tool", "character-counter"],
            search_parents=True,
        )

        app(tokens)

    if __name__ == "__main__":
        app.meta()

----------------------------
Environment Variable Example
----------------------------
To automatically derive and read appropriate environment variables, use the :class:`cyclopts.config.Env` class. Continuing the above TOML example:


.. code-block:: python

   # character-counter.py
   import cyclopts
   from pathlib import Path

   app = cyclopts.App(
       name="character-counter",
       config=cyclopts.config.Env(
           "CHAR_COUNTER_",  # Every environment variable will begin with this.
       ),
   )

   @app.command
   def count(filename: Path, *, character="-"):
       print(filename.read_text().count(character))

   app()

:class:`~cyclopts.config.Env` assembles the environment variable name by joining the following components (in-order):

1. The provided ``prefix``. In this case, it is ``"CHAR_COUNTER_"``.

2. The command and subcommand(s) that lead up to the function being executed.

3. The parameter's CLI name, with the leading ``--`` stripped, and hyphens ``-`` replaced with underscores ``_``.

Running this code without a specified ``--character`` results in counting the default ``-`` character.

.. code-block:: console

   $ python character-counter.py count README.md
   70

By exporting a value to ``CHAR_COUNTER_COUNT_CHARACTER``, that value will now be used as the default:

.. code-block:: console

   $ export CHAR_COUNTER_COUNT_CHARACTER=t
   $ python character-counter.py count README.md
   380
   $ python character-counter.py count README.md --character=q
   3
