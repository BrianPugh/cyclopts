==================
Sharing Parameters
==================
Many subcommands within a CLI may take the same parameters.
For example, all commands for a CLI that deals with a remote server might need a ``url`` and ``port`` number.
Furthermore, there might be common setup required, such as connecting to the remote server.
If you are familiar with `Click`_, this would be accomplished with `contexts <https://click.palletsprojects.com/en/stable/complex/>`_.
In Cyclopts, there are 2 ways to accomplish this:

1. With a :ref:`meta app <Meta App>`. While powerful, it's admittantly a bit heavy-handed and clunky.

2. Via a common dataclass that is passed to each command. While less powerful than using a meta-app,
   it still accomplishes many of the same goals with simpler, terser code.

In this section, we'll be investigating option (2) by constructing an example application that has 2 commands:

1. ``create`` - Connect to a server and send a POST command to it.

2. ``info`` - Connect to a server and GET information about a user.


.. code-block:: python

   # demo.py
   from cyclopts import App, Parameter
   from cyclopts.types import UInt16
   from dataclasses import dataclass
   from functools import cached_property
   from httpx import Client

   @Parameter(name="*")  # Flatten the namespace; i.e. option will be "--url" instead of "--common.url"
   @dataclass
   class Common:
       url: str = "http://cyclopts.readthedocs.io"
       "URL of remote server."

       port: UInt16  = 8080  # an "int" that is limited to range [0, 65535]
       "Port of remote server."

       verbose: bool = False
       "Increased printing verbosity."

       def __post_init__(self):
          # dataclasses call this method after calling the auto-generated __init__.
          if self.verbose:
             print(f"Server: {self.base_url}")

       @property
       def base_url(self) -> str:
          return f"{self.url}:{self.port}"

       @cached_property
       def client(self) -> Client:
           return Client(base_url=self.base_url)

   app = App()

   @app.command
   def create(name: str, age: int, *, common: Common | None = None):
       """Create a user on remote server.

       Parameters
       ----------
       name: str
          Name of the user to create.
       age: int
          Age of the user in years.
       """
       if common is None:
          common = Common()
       json = {"name": name, "age": age}
       if common.verbose:
           print(f"Creating user: {json}")
       common.client.post("/users", json=json)
       # TODO: in a real application, we should error-check the response here.

   @app.command
   def info(name: str, *, common: Common | None = None):
       """List a user on remote server.

       Parameters
       ----------
       name: str
          Name of the user to get info about.
       """
       if common is None:
          common = Common()
       response = common.client.get("/users", params={"name": name})
       user = response.json()
       print(f"User: {user}")

   if __name__ == "__main__":
       app()

From the root help-page, we can see our two commands:

.. code-block:: console

   $ python demo.py --help
   Usage: demo.py COMMAND

   ╭─ Commands ─────────────────────────────────────────────────────────────────╮
   │ create     Create a user on remote server.                                 │
   │ info       List a user on remote server.                                   │
   │ --help -h  Display this message and exit.                                  │
   │ --version  Display application version.                                    │
   ╰────────────────────────────────────────────────────────────────────────────╯

From the ``create`` help-page, we can see all of our parameters:

.. code-block:: console

   $ python demo.py create --help
   Usage: demo.py create [ARGS] [OPTIONS]

   Create a user on remote server.

   ╭─ Parameters ───────────────────────────────────────────────────────────────╮
   │ *  NAME --name             Name of the user to create. [required]          │
   │ *  AGE --age               Age of the user in years. [required]            │
   │    --url                   URL of remote server. [default:                 │
   │                            http://cyclopts.readthedocs.io]                 │
   │    --port                  Port of remote server. [default: 8080]          │
   │    --verbose --no-verbose  Increased printing verbosity. [default: False]  │
   ╰────────────────────────────────────────────────────────────────────────────╯

Some example command-line invocations:

.. code-block:: console

   $ python demo.py create Alice 42
   # No response from the CLI.

   $ python demo.py create Alice 42 --verbose
   Creating user: {'name': 'Alice', 'age': 42}

By organizing the code this way, we can centralize shared parameters and logic between many commands.

.. _Click: https://click.palletsprojects.com
