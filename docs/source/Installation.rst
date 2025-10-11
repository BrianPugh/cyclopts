.. _Detailed Installation:

============
Installation
============

Cyclopts requires Python >=3.10 and can be installed from PyPI via:

.. code-block:: console

   python -m pip install cyclopts


To install directly from github, you can run:

.. code-block:: console

   python -m pip install git+https://github.com/BrianPugh/cyclopts.git

For Cyclopts development, its recommended to use uv:

.. code-block:: console

   git clone https://github.com/BrianPugh/cyclopts.git
   cd cyclopts
   uv sync --all-extras
