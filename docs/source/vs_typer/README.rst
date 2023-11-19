================
Typer Comparison
================

Much of Cyclopts was inspired by the excellent `Typer`_ library.
Despite it's popularity, Typer has some traits that I (and others) find less than ideal.
Part of this stems from Typer's age, with it's first release in late 2019, soon after Python 3.8's release.
Because of this, most of it's API was initially designed around assigning proxy default values to function parameters.
This made the decorated command functions difficult to use outside of typer.
With the introduction of ``Annotated`` in python3.9, type hints were able to be directly annotated, allowing for the removal of these proxy defaults.

Additionally, Typer is built on top of `Click`_.
This makes it difficult for newcomers to figure out which elements are typer-related and which elements are click-related.
It's also hard to tell whether the following criticisms stem from Typer, or the underlying Click.
For better-or-worse, Cyclopts uses it's own internal parsing strategy, gaining complete control over the process.

This section was written about the current version of Typer: ``v0.9.0``.

.. toctree::
   :maxdepth: 1
   :caption: Topics

   argument_vs_option/README.rst
   positional_or_keyword/README.rst
   choices/README.rst
   default_command/README.rst
   optional_list/README.rst
   help_defaults/README.rst
   flag_negation/README.rst
   validation/README.rst
   union_support/README.rst
   version_flag/README.rst
   unit_testing/README.rst


.. _Typer: https://typer.tiangolo.com
.. _Click: https://click.palletsprojects.com
