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

   typer_app = typer.Typer()


   def version_callback(value: bool):
       if not value:
           return
       print("1.2.3")
       raise typer.Exit()


   @typer_app.callback()
   def common(
       version: Annotated[
           bool,
           typer.Option(
               "--version",
               "-v",
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

With Cyclopts, the version is automatically detected by checking the package's version ``cyclopts.App`` is instantiated from. If you prefer explicitness, ``version`` can also be explicitly supplied to ``App``.


.. code-block:: python

   cyclopts_app = cyclopts.App(version="1.2.3")
   cyclopts_app(["--version"])
   # 1.2.3

.. _bulky implementation: https://github.com/tiangolo/typer/issues/52
.. _whether or not you need to specify the command in a single-command program.: ../default_command/README.html
