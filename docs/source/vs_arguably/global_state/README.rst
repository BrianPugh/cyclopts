============
Global State
============

Unlike Cyclopts or Typer, with ``arguably`` you directly jump into decorating functions:


.. code-block:: python

   import arguably


   @arguably.command
   def some_function(required, not_required=2, *others: int, option: float = 3.14):
       """
       this function is on the command line!

       Args:
           required: a required argument
           not_required: this one isn't required, since it has a default value
           *others: all the other positional arguments go here
           option: [-x] keyword-only args are options, short name is in brackets
       """
       print(f"{required=}, {not_required=}, {others=}, {option=}")


   if __name__ == "__main__":
       arguably.run()

With Arguably, no application object is created.
This immediately becomes an issue if you use a library that uses arguably on import.

Lets consider the following file:

.. code-block:: python

   # library_using_arguably.py
   import arguably


   @arguably.command
   def some_library_function(name):
       print(f"{name=}")


   if __name__ == "__main__":
       arguably.run()

.. code-block:: console

   $ python library_using_arguably.py foo
   name='foo'

So this by itself works fine, but lets create another script that imports this library:

.. code-block:: python

   import arguably
   import library_using_arguably


   @arguably.command
   def my_function(name):
       print(f"{name=}")


   if __name__ == "__main__":
       arguably.run()

Now, lets check the help screen:

.. code-block:: console

   $ python my-script.py --help
   usage: my-script.py [-h] command ...

   positional arguments:
     command
       some-library-function
       my-function

   options:
     -h, --help               show this help message and exit

The two CLI applications got combined into one, making Arguably dangerous for CLIs that are also libraries.
