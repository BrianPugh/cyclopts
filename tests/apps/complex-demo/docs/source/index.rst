Complex CLI Documentation
=========================

Welcome to the Complex CLI documentation. This application demonstrates
comprehensive coverage of cyclopts features for documentation testing.

Features
--------

This demo includes:

* **Dataclass parameter flattening** - Using ``@Parameter(name="*")``
* **Pydantic model support** - If pydantic is installed
* **attrs class support** - If attrs is installed
* **4-level nested commands** - ``admin → users → permissions → roles``
* **Complex union types** - ``int | Literal["auto"]`` patterns
* **Custom groups** - Organized command structure
* **Validators** - Number and Path validators
* **Hidden commands** - Commands excluded from help
* **Multiple docstring formats** - NumPy, Google, Sphinx styles

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   cli/index
   cli/admin
   cli/data
   cli/server
   cli/utilities
   cli/full

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
