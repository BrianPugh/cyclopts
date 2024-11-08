===============
Fire Comparison
===============
Fire_ is a CLI parsing library by Google that attempts to generate a CLI from any Python object.
To that end, I think Fire definitely achieves its goal.
However, I think Fire has too much magic, and not enough control.

From the `Fire documentation`_:

    The types of the arguments are determined by their values, rather than by the function signature where they're used.
    You can pass any Python literal from the command line: numbers, strings, tuples, lists, dictionaries, (sets are only supported in some versions of Python).
    You can also nest the collections arbitrarily as long as they only contain literals.

Essentially, Fire ignores type hints and parses CLI parameters as if they were python expressions.

.. code-block:: python

   import fire


   def hello(name: str = "World"):
       print(f"{name=} {type(name)=}")


   if __name__ == "__main__":
       fire.Fire(hello)

.. code-block:: console

   $ my-script foo
   name='foo' type(name)=<class 'str'>

   $ my-script 100
   name=100 type(name)=<class 'int'>

   $ my-script true
   name='true' type(name)=<class 'str'>

   $ my-script True
   name=True type(name)=<class 'bool'>


The equivalent in Cyclopts:

.. code-block:: python

   import cyclopts


   app = cyclopts.App()


   @app.default
   def hello(name: str = "World"):
       print(f"{name=} {type(name)=}")


   if __name__ == "__main__":
       app()

.. code-block:: console

   $ my-script foo
   name='foo' type(name)=<class 'str'>

   $ my-script 100
   name='100' type(name)=<class 'str'>

   $ my-script true
   name='true' type(name)=<class 'str'>

   $ my-script True
   name='True' type(name)=<class 'str'>

Fire is fine for some quick prototyping and has some cool parlour tricks, but is not suitable for a serious CLI.
Therefore, I wouldn't say Fire is a direct competitor to Cyclopts.



.. _Fire: https://github.com/google/python-fire
.. _Fire documentation: https://github.com/google/python-fire/blob/master/docs/guide.md#argument-parsing
