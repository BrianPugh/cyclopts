.. _Typer Flag Negation:

=============
Flag Negation
=============
For boolean parameters, Typer adds a ``--no-MY-FLAG-NAME`` to specify a ``False`` argument.

.. code-block:: python

   import typer

   typer_app = typer.Typer()

   @typer_app.command()
   def foo(my_flag: bool = False):
       print(f"{my_flag=}")

   typer_app(["--my-flag"], standalone_mode=False)
   # my_flag=True
   typer_app(["--no-my-flag"], standalone_mode=False)
   # my_flag=False

Overriding the option's name will disable Typer's negative-flag generation logic:

.. code-block:: python

   import typer
   from typing import Annotated

   typer_app = typer.Typer()

   @typer_app.command()
   def foo(my_flag: Annotated[bool, Option("--my-flag")] = False):
       print(f"{my_flag=}")

   typer_app(["--my-flag"], standalone_mode=False)
   # my_flag=True
   typer_app(["--no-my-flag"], standalone_mode=False)
   # NoSuchOption: No such option: --no-my-flag

This is not the worst, but there is a tiny bit of duplication.
To use a different negative flag, you can supply the name after a slash in your option-name-string.

.. code-block:: python

   import typer

   typer_app = typer.Typer()

   @typer_app.command()
   def foo(my_flag: Annotated[bool, Option("--my-flag/--your-flag")] = False):
       print(f"{my_flag=}")

   typer_app(["--my-flag"], standalone_mode=False)
   # my_flag=True
   typer_app(["--your-flag"], standalone_mode=False)
   # my_flag=False

Cyclopts's :class:`~.Parameter` takes in an optional :attr:`~.Parameter.negative` flag.
To suppress the negative-flag generation, set this argument to either an empty string or list.

.. code-block:: python

   import cyclopts
   from typing import Annotated

   cyclopts_app = cyclopts.App()

   @cyclopts_app.default
   def foo(my_flag: Annotated[bool, cyclopts.Parameter(negative="")] = False):
       print(f"{my_flag=}")

   print("Cyclopts:")
   cyclopts_app(["--my-flag"])
   # my_flag=True
   cyclopts_app(["--your-flag"], exit_on_error=False)
   # ╭─ Error ─────────────────────────────────────────────────────────────────────╮
   # │ Error converting value "--your-flag" to <class 'bool'> for "--my-flag".     │
   # ╰─────────────────────────────────────────────────────────────────────────────╯
   # CoercionError: Error converting value "--your-flag" to <class 'bool'> for "--my-flag".

To define your own custom negative flag, just provide it as a string or list of strings.

.. code-block:: python

   @cyclopts_app.default
   def foo(my_flag: Annotated[bool, cyclopts.Parameter(negative="--your-flag")] = False):
       print(f"{my_flag=}")

   print("Cyclopts:")
   cyclopts_app(["--my-flag"])
   # my_flag=True
   cyclopts_app(["--your-flag"])
   # my_flag=False

The default ``--no-`` negation prefix can also be customized with :attr:`~.Parameter.negative_bool`.

.. code-block:: python

   @cyclopts_app.default
   def foo(my_flag: Annotated[bool, cyclopts.Parameter(negative_bool="--disable-")] = False):
       print(f"{my_flag=}")

   print("Cyclopts:")
   cyclopts_app(["--my-flag"])
   # my_flag=True
   cyclopts_app(["--disable-my-flag"])
   # my_flag=False
