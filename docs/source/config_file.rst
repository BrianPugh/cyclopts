============
Config Files
============
For more complicated CLI tools, it's common to have an external user configuration file. For example, the popular python tools ``poetry``, ``ruff``, and ``pytest`` all are configurable from a ``pyproject.toml`` file.


-------
Example
-------

.. code-block:: python

   import cyclopts
   from pathlib import Path

   app = cyclopts.App(name="myproject", config=cyclopts.config.Toml("pyproject.toml", search_parents=True))


   @app.command
   def count(filename: Path, *, character="-"):
       print(filename.readtext().count(character))

.. code-block:: toml

   [tool.myproject.count]
   character = "t"
