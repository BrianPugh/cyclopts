=====================
Adding a Version Flag
=====================

It's common to check a CLI app's version via a ``--version`` flag.

Concretely, we want the following behavior:

.. code-block:: console

   $ mypackage --version
   1.2.3

To achieve this in Typer, we need the following `bulky implementation`_:

.. code-block:: python

   import typer
   from typing import Annotated

   typer_app = typer.Typer()

   def version_callback(value: bool):
       if value:
           print("1.2.3")
           raise typer.Exit()

   @typer_app.callback()
   def common(
       version: Annotated[
           bool,
           typer.Option(
               "--version",
               callback=version_callback,
               help="Print version.",
           ),
       ] = False,
   ):
       print("Callback body executed.")

   print("Typer:")
   typer_app(["--version"])
   # 1.2.3

Not only is this a lot of boilerplate, but it also has some nasty side-effects, such as impacting `whether or not you need to specify the command in a single-command program.`_
On top of that, it's not very intuitive.
Would you expect ``"Callback body executed."`` to be printed?
When does ``version_callback`` get called?
What is ``value``?

With Cyclopts, the version is automatically detected by checking the version of the package instantiating :class:`App <cyclopts.App>`.
If you prefer explicitness, :attr:`~.App.version` can also be explicitly supplied to :class:`App <cyclopts.App>`.


.. code-block:: python

   import cyclopts

   cyclopts_app = cyclopts.App(version="1.2.3")
   cyclopts_app(["--version"])
   # 1.2.3

.. _bulky implementation: https://github.com/tiangolo/typer/issues/52
.. _whether or not you need to specify the command in a single-command program.: ../default_command/README.html
