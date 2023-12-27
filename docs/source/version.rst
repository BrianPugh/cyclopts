=======
Version
=======

All CLI applications should have the basic ability to check the installed version; i.e.:

.. code-block:: console

   $ my-application --version
   7.5.8

By default, cyclopts parses the special flag ``--version``.

The resolution order for determining the version string is as follows:

1. An explicitly supplied version string or callable to the root Cyclopts application:

   .. code-block:: python

      app = cyclopts.App(version="7.5.8")

   If a callable is provided, it will be invoked when running the ``--version`` command:

   .. code-block:: python

      def get_my_application_version() -> str:
          return "7.5.8"


      app = cyclopts.App(version=get_my_application_version)

2. The invoking-package's `Distribution Package's Version Number`_ via `importlib.metadata.version`_.
   Cyclopts attempts to derive the package module that instantiated the :class:`App <cyclopts.App>` object by traversing the call stack.

3. The invoking-package's `defacto PEP8 standard`_ ``__version__`` string.
   Cyclopts attempts to derive the package module that instantiated the :class:`App <cyclopts.App>` object by traversing the call stack.

   .. code-block:: python

      # mypackage/__init__.py
      __version__ = "7.5.8"

      # mypackage/__main__.py
      # ``App`` will use ``mypackage.__version__``.
      app = cyclopts.App()

4. The default version string ``"0.0.0"`` will be displayed.

The ``--version`` flag can be changed to a different name(s) via the ``version_flags`` parameter.

.. code-block:: python

   app = cyclopts.App(version_flags="--show-version")
   app = cyclopts.App(version_flags=["--version", "-v"])

To disable the ``--version`` flag, set ``version_flags`` to an empty string or iterable.

.. code-block:: python

   app = cyclopts.App(version_flags="")
   app = cyclopts.App(version_flags=[])


.. _Distribution Package's Version Number: https://packaging.python.org/en/latest/glossary/#term-Distribution-Package
.. _importlib.metadata.version: https://docs.python.org/3.12/library/importlib.metadata.html#distribution-versions
.. _defacto PEP8 standard: https://peps.python.org/pep-0008/#module-level-dunder-names
