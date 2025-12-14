.. _cyclopts-complex-cli:

complex-cli
-----------

Complex CLI application for comprehensive documentation testing.

.. contents:: Table of Contents
   :local:
   :depth: 6

::

    complex-cli COMMAND

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, --no-quiet, -q``
    Suppress non-essential output. [Default: ``False``]

``--log-level``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

**Subcommands:**

``server``
    Server management commands.

.. _cyclopts-complex-cli-server:

server
^^^^^^

Server management commands.

**Commands:**

``restart``
    Restart the server.

``start``
    Start the server with configuration.

``stop``
    Stop the server.

.. _cyclopts-complex-cli-server-start:

start
"""""

Start the server with configuration.

Demonstrates Pydantic model support for CLI parameters.

::

    complex-cli server start [OPTIONS]

**Parameters:**

``--server.host``
    Server bind address. [Default: ``0.0.0.0``]

``--server.port``
    Server port number. [Default: ``8000``]

``--server.workers``
    Number of worker processes. [Default: ``4``]

``--server.timeout``
    Request timeout in seconds. [Default: ``30.0``]

``--server.debug, --server.no-debug``
    Enable debug mode. [Default: ``False``]

``--auth.provider``
    Authentication provider type. [Choices: ``oauth2``, ``jwt``, ``basic``, ``none``, Default: ``jwt``]

``--auth.token-expiry``
    Token expiration time in seconds. [Default: ``3600``]

``--auth.refresh-enabled, --auth.no-refresh-enabled``
    Enable token refresh. [Default: ``True``]

``--auth.allowed-origins, --auth.empty-allowed-origins``
    List of allowed CORS origins.

.. _cyclopts-complex-cli-server-stop:

stop
""""

Stop the server.

::

    complex-cli server stop [OPTIONS]

**Parameters:**

``--graceful, --no-graceful``
    Perform graceful shutdown. [Default: ``True``]

``--timeout``
    Shutdown timeout in seconds. [Default: ``30``]

``--force, --no-force, -f``
    Force immediate shutdown. [Default: ``False``]

.. _cyclopts-complex-cli-server-restart:

restart
"""""""

Restart the server.

::

    complex-cli server restart [ARGS]

**Parameters:**

``ROLLING, --rolling, --no-rolling``
    Perform rolling restart (zero downtime). [Default: ``False``]

``DELAY, --delay``
    Delay between worker restarts in seconds. [Default: ``5``]
