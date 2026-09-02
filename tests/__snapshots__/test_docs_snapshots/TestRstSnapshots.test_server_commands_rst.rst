.. _cyclopts-complex-cli:

complex-cli
-----------

::

    complex-cli COMMAND [OPTIONS]

Complex CLI application for comprehensive documentation testing.

.. contents:: Table of Contents
   :local:
   :depth: 6

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
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

::

    complex-cli server start [OPTIONS]

Start the server with configuration.

Demonstrates Pydantic model support for CLI parameters.

**Parameters:**

``--server.host STR``
    Server bind address. [Default: ``0.0.0.0``]

``--server.port INT``
    Server port number. [Default: ``8000``]

``--server.workers INT``
    Number of worker processes. [Default: ``4``]

``--server.timeout FLOAT``
    Request timeout in seconds. [Default: ``30.0``]

``--server.debug, --server.no-debug``
    Enable debug mode. [Default: ``False``]

``--auth.provider``
    Authentication provider type. [Choices: ``oauth2``, ``jwt``, ``basic``, ``none``, Default: ``jwt``]

``--auth.token-expiry INT``
    Token expiration time in seconds. [Default: ``3600``]

``--auth.refresh-enabled, --auth.no-refresh-enabled``
    Enable token refresh. [Default: ``True``]

``--auth.allowed-origins LIST[STR], --auth.empty-allowed-origins``
    List of allowed CORS origins. [Default: ``['*']``]

.. _cyclopts-complex-cli-server-stop:

stop
""""

::

    complex-cli server stop [OPTIONS]

Stop the server.

**Parameters:**

``--graceful, --no-graceful``
    Perform graceful shutdown. [Default: ``True``]

``--timeout INT``
    Shutdown timeout in seconds. [Default: ``30``]

``--force, -f, --no-force``
    Force immediate shutdown. [Default: ``False``]

.. _cyclopts-complex-cli-server-restart:

restart
"""""""

::

    complex-cli server restart [ARGS]

Restart the server.

**Parameters:**

``ROLLING, --rolling, --no-rolling``
    Perform rolling restart (zero downtime). [Default: ``False``]

``DELAY, --delay``
    Delay between worker restarts in seconds. [Default: ``5``]
