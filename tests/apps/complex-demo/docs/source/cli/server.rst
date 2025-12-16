Server Commands
===============

Server management commands demonstrating **Pydantic model support**.

.. note::

   If Pydantic is not installed, the server commands will use simpler
   parameter definitions as a fallback.

Server Management
-----------------

.. cyclopts:: complex_app:app
   :heading-level: 3
   :recursive:
   :commands: server

Pydantic Integration
--------------------

When Pydantic is available, the ``start`` command accepts two Pydantic models:

* ``ServerConfig`` - Server bind address, port, workers, timeout
* ``AuthConfig`` - Authentication provider, token settings, CORS origins

Pydantic's field validators are respected, providing automatic validation
of port numbers, worker counts, etc.
