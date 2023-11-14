=============
Flag Negation
=============
By default, for boolean parameters, Typer adds a ``--no-MY-FLAG-NAME`` to allow a ``False`` argument to be provided.
Frequently, this is useful.


.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo(my_flag: bool = False):
       print(f"{my_flag=}")


   typer_app(["--my-flag"], standalone_mode=False)
   # my_flag=True
   typer_app(["--no-my-flag"], standalone_mode=False)
   # my_flag=False

If you don't want the ``--no-my-flag``, you have to override the provided name, which will disable the negative-flag generation logic:

.. code-block:: python

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

   @typer_app.command()
   def foo(my_flag: Annotated[bool, Option("--my-flag/--your-flag")] = False):
       print(f"{my_flag=}")


   typer_app(["--my-flag"], standalone_mode=False)
   # my_flag=True
   typer_app(["--your-flag"], standalone_mode=False)
   # my_flag=False

Cyclopts's ``Parameter`` takes in an optional ``negative`` flag.
To suppress the negative-flag generation, set this argument to either an empty string or list.

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.default
   def foo(my_flag: Annotated[bool, cyclopts.Parameter(negative="")] = False):
       print(f"{my_flag=}")


   print("Cyclopts:")
   cyclopts_app(["--my-flag"])
   # my_flag=True
   cyclopts_app(["--your-flag"])
   # TODO: WHAT EXCEPTION IS RAISED?

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
