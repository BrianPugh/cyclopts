=======
Choices
=======
Frequently, a CLI will want to limit values provided to a parameter to a specific set of choices.
With Typer, this is accomplished via declaring an enum.

.. code-block:: python

   class Environment(str, Enum):
       DEV = "dev_value"
       STAGING = "staging_value"
       PROD = "prod_value"


   typer_app = typer.Typer()


   @typer_app.command()
   def foo(env: Environment = Environment.DEV):
       env = env.name
       print(f"Using: {env}")


   print("Typer (Enum):")
   typer_app(["--env", "staging_value"])
   # Using: STAGING

In this example, the enum's values end in "_value" to avoid confusion.
From this, we can see that Typer will look for the CLI-provided *value*, and supply the function with the enum member.
IMHO, this is backwards; typically the enum name (e.g. ``DEV``) is intended to be human-friendly, while the value (e.g. ``dev_value``) is more frequently used programmatically. **When using enums, Cyclopts will do the opposite of Typer, and perform a case-insensitive lookup by name.**

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.default()
   def foo(env: Environment = Environment.DEV):
       env = env.name
       print(f"Using: {env}")


   print("Cyclopts (Enum):")
   cyclopts_app(["--env", "staging"])
   # Using: STAGING


-------
Literal
-------
Enums don't work well with everyone's workflow.
Many people prefer to directly use strings for their functions' options.
The much more intuitive, convenient method of doing this is with the ``Literal`` type annotation.
Unfortuneately, Typer has not provided support, despite `a feature request dating back to early 2020`_
Cyclopts has builtin support for ``Literal``.

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.default()
   def foo(env: Literal["dev", "staging", "prod"] = "staging"):
       print(f"Using: {env}")


   print("Cyclopts (Literal):")
   cmd = ["--env", "staging"]
   print(cmd)
   cyclopts_app(cmd)
   # Using: staging


.. _a feature request dating back to early 2020: https://github.com/tiangolo/typer/issues/76
