=============
Union Support
=============

Currently, Typer does not support ``Union`` type annotations.

.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo(value: Union[int, str] = "default_str"):
       print(f"{type(value)=} {value=}")


   typer_app(["123"])
   # AssertionError: Typer Currently doesn't support Union types


Cyclopts fully supports ``Union``s. Automatic coercion can be a bit ambiguous, for example, should a provided value ``"123"`` for a ``Union[int, str]`` type be coerced into an ``int``, or left as a ``str``?

Cyclopt's automatic coercion rules iterates over the unioned types from left to right, until one can be coerced without error. In this case, it would be coerced into an ``int``.

.. code-block:: python

   cyclopts_app = cyclopts.App()


   @cyclopts_app.default
   def foo(value: Union[int, str] = "default_str"):
       print(f"{type(value)=} {value=}")


   print("Cyclopts:")
   cyclopts_app(["123"])
   # type(value)=<class 'int'> value=123
   cyclopts_app(["bar"])
   # type(value)=<class 'str'> value='bar'

Naturally, Cyclopts also supports ``Optional`` types, since ``Optional`` is actually just syntactic sugar for ``Union[..., None]``.
