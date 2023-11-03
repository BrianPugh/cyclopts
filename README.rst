|Python compat| |GHA tests|

A template to quickly get you creating an open-source python library
or project with linting, static analysis, CI, and CD to PyPI.

Usage
=====

To use this template, click the green "Use this template" button in the github web interface.
Then run:

.. code-block:: bash

   git clone YOUR_REPO
   # then cd into your local repo, and run:
   ./bootstrap

And follow the on-screen prompts. ``bootstrap`` uses some git data (like detecting your username and repository name), so cloning the repo generated from the template is necessary.

Compatibility
=============

This template's ``bootstrap`` functionality only works on MacOS/Linux/WSL, it *will not work natively on windows*.
The resulting project, however, may be windows-compatible.

Features
========

* Features dependent if project is a library or a standalone project.

* `Poetry`_ support.

  * If not installed, Poetry will automatically be installed when running ``bootstrap``.

  * `Poetry Dynamic Versioning`_ - Dynamically handles your project version based on git tags.

* Optional command line interface boilerplate using Typer_.

* Optional C binding support via Cython.

* `Sphinx`_ + `ReadTheDocs`_.

  * To setup, goto `ReadTheDocs Dashboard`_ and click on "Import a Project".

* `Pre-commit`_ linting and static analysis. The following hooks are pre-configured:

  * `Black <https://github.com/psf/black>`_ - The uncompromising Python code formatter.

  * `Ruff <https://github.com/charliermarsh/ruff>`_ - An extremely fast Python linter.

  * `Creosote <https://github.com/fredrikaverpil/creosote>`_ - Identifies unused dependencies.

  * `Codespell <https://github.com/codespell-project/codespell>`_ - Checks code and documentation for common misspellings.

  * `Pyright <https://github.com/microsoft/pyright>`_ - Static type checker.

* `Docker`_ support for standalone projects.

* GitHub Actions for:

  * Running ``pre-commit`` on pull requests and commits to ``main``.

  * Running unit tests, coverage, and verify docs build on pull requests and commits to ``main``.

    * Goto your `Codecov Dashboard`_ and add your repo.

  * Build and upload wheels to PyPI on semver tags ``vX.Y.Z``.

    * Add your `PyPI API token`_ to your `GitHub secrets`_ for key ``PYPI_TOKEN``.

    * If using Cython, pre-built binary packages will be created for all major operating systems, python versions, and computer architectures.

  * Build and upload docker images to Dockerhub.

    * Add your Dockerhub username and `token`_ to your `GitHub secrets`_
      ``DOCKERHUB_USERNAME`` and ``DOCKERHUB_TOKEN``.

    * Optionally, modify the ``tags`` field in ``.github/workflows/docker.yaml``.
      By default, it assumes your docker username is the same as your github username.


Cython
======
This template has an option to add boilerplate for Cython_.
Cython is a programming language that simplifies the creation of C extensions for Python.
The Cython documentation is quite good; the aim of this section is to explain what this
template sets up, and what actions will still need to be performed by you.
This explanation assumes you are familiar with C.
Replace any reference here to ``pythontemplate`` with your project name.

1. Place all C and header files in the ``pythontemplate/_c_src`` directory.
   If you don't plan on using any explicit C files, you may delete this directory.

2. Update ``pythontemplate/cpythontemplate.pxd`` with header information from the files in (1).
   Example of common definitions (functions, structs, and enums) are provided.
   Think of ``*.pxd`` as a header file that allows Cython ``.pyx`` code to access pure C files.
   This file will be compiled into a package that can be imported in a ``.pyx`` file via ``cimport``.
   If you don't plan on using any explicit C files, you may delete this file.

3. Add Cython code to ``pythontemplate/_c_extension.pyx``. Some class starter code is provided.
   This is where a good pythonic interface (functions and classes) should be written.

4. Optionally tweak ``build.py`` (runs at setup/installation) with compiler options.
   The default ``build.py`` offers a good, working starting point for most projects and performs the following:

   a. Recursively searches for all C files in ``pythontemplate/_c_src/``.
      To change this action, modify the variable ``c_files``.

   b. Compiles the code defined in ``_c_extension.pyx`` into a shared object file.

   c. Adds ``pythontemplate`` and ``pythontemplate/_c_src`` to the Include Path (variable ``include_dirs``).

   d. If your codebase contains a slower, python implementation of your Cython code,
      we can allow building to fail by uncommenting the ``allowed_to_fail`` logic at the top.

5. The Github Action workflow defined in ``.github/workflows/build_wheels.yaml`` will create pre-built
   binaries for all major Python versions, operating systems, and computer architectures.
   It will also create a Source Distribution (sdist).
   Finally, on git semver tags (``vX.X.X``), it will upload all the resulting wheels to PyPI.


Reference
=========
If you find this in the git history of a project and you like the structure, visit
this template at https://github.com/BrianPugh/python-template .


.. |GHA tests| image:: https://github.com/BrianPugh/python-template/workflows/tests/badge.svg
   :target: https://github.com/BrianPugh/python-template/actions?query=workflow%3Atests
   :alt: GHA Status
.. |Python compat| image:: https://img.shields.io/badge/>=python-3.8-blue.svg

.. _Codecov Dashboard: https://app.codecov.io/gh
.. _Docker: https://www.docker.com
.. _GitHub secrets: https://docs.github.com/en/actions/security-guides/encrypted-secrets
.. _Poetry: https://python-poetry.org
.. _Pre-commit: https://pre-commit.com
.. _PyPI API token: https://pypi.org/help/#apitoken
.. _ReadTheDocs Dashboard: https://readthedocs.org/dashboard/
.. _ReadTheDocs: https://readthedocs.org
.. _Sphinx: https://www.sphinx-doc.org/en/master/
.. _token: https://docs.docker.com/docker-hub/access-tokens/
.. _Cython: https://cython.readthedocs.io/en/latest/
.. _Poetry Dynamic Versioning: https://github.com/mtkennerly/poetry-dynamic-versioning
.. _Typer: https://typer.tiangolo.com
