============
User Classes
============
Cyclopts supports classically defined user classes, as well as classes defined by the following dataclass-like libraries:

* `attrs <https://www.attrs.org/en/stable/>`_
* `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
* `NamedTuple <https://docs.python.org/3/library/typing.html#typing.NamedTuple>`_
* `pydantic <https://docs.pydantic.dev/latest/>`_
* `TypedDict <https://docs.python.org/3/library/typing.html#typing.TypedDict>`_

As an example, lets consider using the builtin :obj:`~dataclasses.dataclass` to make a CLI that manages a movie collection.

.. code-block:: python

   from cyclopts import App
   from dataclasses import dataclass

   app = App(name="movie-maintainer")

   @dataclass
   class Movie:
      title: str
      year: int

   @app.command
   def add(movie: Movie):
      print(f"Adding movie: {movie}")

   app()

.. code-block:: console

   $ movie-maintainer add --help
   Usage: movie-maintainer add [ARGS] [OPTIONS]

   ╭─ Parameters ────────────────────────────────────────────────╮
   │ *  MOVIE.TITLE              [required]                      │
   │      --movie.title                                          │
   │ *  MOVIE.YEAR --movie.year  [required]                      │
   ╰─────────────────────────────────────────────────────────────╯

   $ movie-maintainer add 'Mad Max: Fury Road' 2015
   Adding movie: Movie(title='Mad Max: Fury Road', year=2015)

   $ movie-maintainer add --movie.title 'Furiosa: A Mad Max Saga' --movie.year 2024
   Adding movie: Movie(title='Furiosa: A Mad Max Saga', year=2024)

--------------------
Namespace Flattening
--------------------

It is likely that the actual movie class/object is not important to the CLI user, and the parameter names like ``--movie.title`` are unnecessarily verbose. We can remove ``movie`` from the name by giving the ``Movie`` type annotation the special name ``"*"``.

.. code-block:: python

   from cyclopts import App, Parameter
   from dataclasses import dataclass
   from typing import Annotated

   app = App(name="movie-maintainer")

   @dataclass
   class Movie:
      title: str
      year: int

   @app.command
   def add(movie: Annotated[Movie, Parameter(name="*")]):
      print(f"Adding movie: {movie}")

   app()

.. code-block:: console

   $ movie-maintainer add --help
   Usage: movie-maintainer add [ARGS] [OPTIONS]

   ╭─ Parameters ────────────────────────────────────────────────╮
   │ *  TITLE --title  [required]                                │
   │ *  YEAR --year    [required]                                │
   ╰─────────────────────────────────────────────────────────────╯

------------------
Sharing Parameters
------------------
A flattened dataclass provides a natural way of easily sharing a set of parameters between commands.

.. code-block:: python

   from cyclopts import App, Parameter
   from dataclasses import dataclass
   from typing import Annotated

   app = App(name="movie-maintainer")

   @dataclass
   class _Config:
      user: str
      server: str = "media.sqlite"

   Config = Annotated[_Config, Parameter(name="*")]

   @dataclass
   class Movie:
      title: str
      year: int

   @app.command
   def add(movie: Movie, *, config: Config):
      print(f"Config: {config}")
      print(f"Adding movie: {movie}")

   @app.command
   def remove(movie: Movie, *, config: Config):
      print(f"Config: {config}")
      print(f"Removing movie: {movie}")

   app()

.. code-block:: console

   $ movie-maintainer remove --help
   Usage: movie-maintainer remove [ARGS] [OPTIONS]

   ╭─ Parameters ────────────────────────────────────────────────╮
   │ *  MOVIE.TITLE              [required]                      │
   │      --movie.title                                          │
   │ *  MOVIE.YEAR --movie.year  [required]                      │
   │ *  --user                   [required]                      │
   │    --server                 [default: media.sqlite]         │
   ╰─────────────────────────────────────────────────────────────╯

   $ movie-maintainer remove 'Mad Max: Fury Road' 2015 --user Guido
   Config: _Config(user='Guido', server='media.sqlite')
   Removing movie: Movie(title='Mad Max: Fury Road', year=2015)


-----------
Config File
-----------
Having the user specify ``--user`` every single call is a bit cumbersome, especially if they're always going to provide the same value.
We can have Cyclopts fallback to a configuration file.

Consider the following toml data saved to ``config.toml``:

.. code-block:: toml

   # config.toml
   user = "Guido"

We can update our app to fill in missing CLI parameters from this file:

.. code-block:: python

   from cyclopts import App, Parameter, config
   from dataclasses import dataclass
   from typing import Annotated

   app = App(
      name="movie-maintainer",
      config=config.Toml("config.toml", use_commands_as_keys=False),
   )

   @dataclass
   class _Config:
      user: str
      server: str = "media.sqlite"

   Config = Annotated[_Config, Parameter(name="*")]

   @dataclass
   class Movie:
      title: str
      year: int

   @app.command
   def add(movie: Movie, *, config: Config):
      print(f"Config: {config}")
      print(f"Adding movie: {movie}")

   app()

.. code-block:: console

   $ movie-maintainer add 'Mad Max: Fury Road' 2015
   Config: _Config(user='Guido', server='media.sqlite')
   Adding movie: Movie(title='Mad Max: Fury Road', year=2015)
