============
Config Files
============
For more complicated CLI applications, it is common to have an external user configuration file. For example, the popular python tools ``poetry``, ``ruff``, and ``pytest`` are all configurable from a ``pyproject.toml`` file. The :attr:`App.config <cyclopts.App.config>` attribute accepts a callable (or list of callables) that add (or remove) values to the parsed CLI tokens. The provided callable must have signature:

.. code-block:: python

   def config(apps: Tuple[App, ...], commands: Tuple[str, ...], mapping: Dict[str, Union[Unset, List[str]]]):
       """Modifies given mapping inplace with some injected values.

       Parameters
       ----------
       apps: Tuple[App, ...]
          The application hierarchy that led to the current command function.
          The current command app is the last element of this tuple.
       commands: Tuple[str, ...]
          The CLI strings that led to the current command function.
       mapping: Dict[str, Union[Unset, List[str]]]
          A dictionary mapping CLI keyword names to their tokens (before App and Group converters/validators have been invoked).
          For example, if the user specifies --my-var=foo, then this dictionary will be {"my-var": ["foo"]}.
          If the value is an cyclopts.config.Unset object, then no tokens have been parsed for that parameter yet.
          Deleting keys from this dictionary will unset their value.
       """
       ...

The provided ``config`` does not have to be a function; all the Cyclopts builtin configs are classes that implement the ``__call__`` method. The Cyclopts builtins offer good standard functionality for common configuration files like yaml or toml. See :ref:`cyclopts.config <API Config>`.

------------
TOML Example
------------
In this example, we create a small CLI tool that counts the number of times a given character occurs in a file.

.. code-block:: python

   # character-counter.py
   import cyclopts
   from pathlib import Path

   app = cyclopts.App(
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


   if __name__ == "__main__":
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
