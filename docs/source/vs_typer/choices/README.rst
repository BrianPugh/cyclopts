.. _Typer Choices:

=======
Choices
=======

----
Enum
----
Frequently, a CLI will want to limit values provided to a parameter to a specific set of choices.
With Typer, this is accomplished via declaring an :class:`~enum.Enum`.

.. code-block:: python

   import typer
   from enum import Enum

   class Environment(str, Enum):
       # Values end in "_value" to avoid confusion in this example.
       DEV = "dev_value"
       STAGING = "staging_value"
       PROD = "prod_value"

   typer_app = typer.Typer()

   @typer_app.command
   def foo(env: Environment = Environment.DEV):
       print(f"Using: {env.name}")

   print("Typer (Enum):")
   typer_app(["--env", "staging_value"])
   # Using: STAGING

Typer looks for the CLI-provided *value*, and supplies the function with the enum member.
IMHO, this is backwards; typically the enum name (e.g. ``DEV``) is intended to be more human-friendly, while the value (e.g. ``dev_value``) more frequently has a programmatic-meaning. **When using enums, Cyclopts will do the opposite of Typer**, performing a **case-insensitive** lookup by **name**.

.. code-block:: python

   import cyclopts

   cyclopts_app = cyclopts.App()

   @cyclopts_app.default
   def foo(env: Environment = Environment.DEV):
       print(f"Using: {env.name}")

   print("Cyclopts (Enum):")
   cyclopts_app(["--env", "staging"])
   # Using: STAGING

-------
Literal
-------
Enums don't work well with everyone's workflow.
Many people prefer to directly use strings for their functions' options.
The much more intuitive, convenient method of doing this is with the :obj:`~typing.Literal` type annotation.

.. note::

   Typer added support for :obj:`~typing.Literal` in version 0.19.0 (September 2025), resolving `a feature request from early 2020`_.

Cyclopts has builtin support for :obj:`~typing.Literal`, see :ref:`Coercion Rules - Literal <Coercion Rules - Literal>`.

.. code-block:: python

   import cyclopts
   from typing import Literal

   cyclopts_app = cyclopts.App()

   @cyclopts_app.default
   def foo(env: Literal["dev", "staging", "prod"] = "staging"):
       print(f"Using: {env}")


   print("Cyclopts (Literal):")
   cmd = ["--env", "staging"]
   print(cmd)
   cyclopts_app(cmd)
   # Using: staging

.. _a feature request from early 2020: https://github.com/tiangolo/typer/issues/76
