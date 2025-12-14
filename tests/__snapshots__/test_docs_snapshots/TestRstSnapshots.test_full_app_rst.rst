.. _cyclopts-complex-cli:

===========
complex-cli
===========

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

``admin``
    Administrative commands for system management.

``data``
    Data processing commands.

``server``
    Server management commands.

**Utilities:**

``cache``
    Cache management commands.

``complex-types``
    Demonstrate complex type annotations.

``google-style``
    Command with Google-style docstring.

``info``
    Show application information.

``numpy-style``
    Command with NumPy-style docstring.

``sphinx-style``
    Command with Sphinx-style docstring.

``version``
    Show version information.

.. _cyclopts-complex-cli-version:

version
-------

Show version information.

Displays the application version and system information.

::

    complex-cli version

.. _cyclopts-complex-cli-info:

info
----

Show application information.

::

    complex-cli info [ARGS]

**Parameters:**

``DETAILED, --detailed, --no-detailed``
    Show detailed information including dependencies. [Default: ``False``]

``FORMAT, --format``
    Output format for the information. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

.. _cyclopts-complex-cli-admin:

admin
-----

Administrative commands for system management.

**Commands:**

``config-cmd``
    Configure database settings.

``status``
    Show system status.

``users``
    User management commands.

.. _cyclopts-complex-cli-admin-status:

status
^^^^^^

Show system status.

::

    complex-cli admin status [OPTIONS] [ARGS]

**Parameters:**

``SERVICES, --services``
    Specific services to check (all if not specified).

``--watch, -w``
    Continuously watch status. [Default: ``False``]

``--interval``
    Refresh interval in seconds when watching. [Default: ``5``]

.. _cyclopts-complex-cli-admin-config-cmd:

config-cmd
^^^^^^^^^^

Configure database settings.

::

    complex-cli admin config-cmd [OPTIONS]

**Parameters:**

``--host``
    Database server hostname. [Default: ``localhost``]

``--port``
    Database server port number. [Default: ``5432``]

``--username``
    Authentication username. [Default: ``admin``]

``--password``
    Authentication password (optional).

``--ssl-mode``
    SSL connection mode. [Choices: ``disable``, ``prefer``, ``require``, ``verify-full``, Default: ``prefer``]

``--pool-size``
    Connection pool size. [Default: ``10``]

.. _cyclopts-complex-cli-admin-users:

users
^^^^^

User management commands.

**Commands:**

``create``
    Create a new user.

``delete``
    Delete a user.

``list-users``
    List all users.

``permissions``
    Permission management for users.

.. _cyclopts-complex-cli-admin-users-list-users:

list-users
""""""""""

List all users.

::

    complex-cli admin users list-users [ARGS]

**Parameters:**

``ACTIVE-ONLY, --active-only, --no-active-only``
    Show only active users. [Default: ``False``]

``ROLE, --role``
    Filter by user role. [Choices: ``admin``, ``user``, ``guest``]

``LIMIT, --limit``
    Maximum number of users to display. [Default: ``100``]

``FORMAT, --format``
    Output format. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

.. _cyclopts-complex-cli-admin-users-create:

create
""""""

Create a new user.

::

    complex-cli admin users create [OPTIONS] USERNAME EMAIL

**Arguments:**

``USERNAME``
    Unique username for the new user. [**Required**]

``EMAIL``
    Email address for the new user. [**Required**]

**Parameters:**

``--role``
    User role assignment. [Choices: ``admin``, ``user``, ``guest``, Default: ``user``]

``--permissions.none, --permissions.no-none``
    Initial permission flags. [Default: ``False``]

``--permissions.read, --permissions.no-read``
    Initial permission flags. [Default: ``False``]

``--permissions.write, --permissions.no-write``
    Initial permission flags. [Default: ``False``]

``--permissions.execute, --permissions.no-execute``
    Initial permission flags. [Default: ``False``]

``--permissions.admin, --permissions.no-admin``
    Initial permission flags. [Default: ``False``]

``--send-welcome, --no-send-welcome``
    Send welcome email after creation. [Default: ``True``]

.. _cyclopts-complex-cli-admin-users-delete:

delete
""""""

Delete a user.

::

    complex-cli admin users delete [OPTIONS] USERNAME

**Arguments:**

``USERNAME``
    Username to delete. [**Required**]

**Parameters:**

``--force, --no-force, -f``
    Skip confirmation prompt. [Default: ``False``]

``--backup, --no-backup``
    Create backup before deletion. [Default: ``True``]

.. _cyclopts-complex-cli-admin-users-permissions:

permissions
"""""""""""

Permission management for users.

**Commands:**

``audit``
    Audit permission changes.

``grant``
    Grant permissions to a user.

``revoke``
    Revoke permissions from a user.

``roles``
    Role template management.

.. _cyclopts-complex-cli-admin-users-permissions-grant:

grant
'''''

Grant permissions to a user.

::

    complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to grant. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

**Parameters:**

``--resource``
    Specific resource to grant access to.

``--expires``
    Expiration date (ISO format).

.. _cyclopts-complex-cli-admin-users-permissions-revoke:

revoke
''''''

Revoke permissions from a user.

::

    complex-cli admin users permissions revoke USERNAME PERMISSION

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to revoke. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

.. _cyclopts-complex-cli-admin-users-permissions-audit:

audit
'''''

Audit permission changes.

::

    complex-cli admin users permissions audit [ARGS]

**Parameters:**

``USERNAME, --username``
    Filter by username (all users if not specified).

``DAYS, --days``
    Number of days to look back. [Default: ``30``]

``FORMAT, --format``
    Output format for audit report. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

.. _cyclopts-complex-cli-admin-users-permissions-roles:

roles
'''''

Role template management.

**Commands:**

``create-role``
    Create a new role template.

``list-roles``
    List all role templates.

.. _cyclopts-complex-cli-admin-users-permissions-roles-list-roles:

list-roles
~~~~~~~~~~

List all role templates.

::

    complex-cli admin users permissions roles list-roles [ARGS]

**Parameters:**

``INCLUDE-SYSTEM, --include-system, --no-include-system``
    Include built-in system roles. [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-roles-create-role:

create-role
~~~~~~~~~~~

Create a new role template.

::

    complex-cli admin users permissions roles create-role [OPTIONS] NAME

**Arguments:**

``NAME``
    Role name. [**Required**]

**Parameters:**

``--permissions.none, --permissions.no-none``
    Default permissions for this role. [Default: ``False``]

``--permissions.read, --permissions.no-read``
    Default permissions for this role. [Default: ``False``]

``--permissions.write, --permissions.no-write``
    Default permissions for this role. [Default: ``False``]

``--permissions.execute, --permissions.no-execute``
    Default permissions for this role. [Default: ``False``]

``--permissions.admin, --permissions.no-admin``
    Default permissions for this role. [Default: ``False``]

``--description``
    Role description. [Default: ``""``]

.. _cyclopts-complex-cli-data:

data
----

Data processing commands.

**Commands:**

``pipeline``
    Run a complete data pipeline.

``process``
    Process data files with configurable options.

``validate``
    Validate data files against schema.

.. _cyclopts-complex-cli-data-process:

process
^^^^^^^

Process data files with configurable options.

This command demonstrates dataclass parameter flattening where
all fields from ProcessingConfig and PathConfig become CLI options.

::

    complex-cli data process [OPTIONS] INPUT_FILES

**Arguments:**

``INPUT_FILES``
    Input files to process [**Required**]

**Parameters:**

``--batch-size``
    Number of items to process per batch. [Default: ``32``]

``--num-workers``
    Number of parallel workers. Use "auto" for automatic detection. [Choices: ``auto``, Default: ``auto``]

``--quality-level``
    Processing quality level. Higher values mean better quality but slower. [Choices: ``high``, ``medium``, ``low``, Default: ``high``]

``--device``
    Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. [Choices: ``cuda``, ``cpu``, ``auto``, Default: ``auto``]

``--output-formats, --empty-output-formats``
    List of output formats to generate. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``[json]``]

``--input-dir``
    Input data directory. [Default: ``data/input``]

``--output-dir``
    Output results directory. [Default: ``data/output``]

``--cache-dir``
    Cache directory for intermediate files.

``--log-dir``
    Directory for log files. [Default: ``logs``]

.. _cyclopts-complex-cli-data-pipeline:

pipeline
^^^^^^^^

Run a complete data pipeline.

Demonstrates nested dataclass flattening (PipelineConfig contains
PathConfig and ProcessingConfig).

::

    complex-cli data pipeline [OPTIONS]

**Parameters:**

``--name``
    Pipeline name for identification. [Default: ``default-pipeline``]

``--input-dir``
    Input data directory. [Default: ``data/input``]

``--output-dir``
    Output results directory. [Default: ``data/output``]

``--cache-dir``
    Cache directory for intermediate files.

``--log-dir``
    Directory for log files. [Default: ``logs``]

``--batch-size``
    Number of items to process per batch. [Default: ``32``]

``--num-workers``
    Number of parallel workers. Use "auto" for automatic detection. [Choices: ``auto``, Default: ``auto``]

``--quality-level``
    Processing quality level. Higher values mean better quality but slower. [Choices: ``high``, ``medium``, ``low``, Default: ``high``]

``--device``
    Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. [Choices: ``cuda``, ``cpu``, ``auto``, Default: ``auto``]

``--output-formats, --empty-output-formats``
    List of output formats to generate. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``[json]``]

``--dry-run, --no-dry-run``
    If True, simulate execution without making changes. [Default: ``False``]

.. _cyclopts-complex-cli-data-validate:

validate
^^^^^^^^

Validate data files against schema.

::

    complex-cli data validate [OPTIONS] INPUT_PATH

**Arguments:**

``INPUT_PATH``
    Path to validate. [**Required**]

**Parameters:**

``--strict, --no-strict``
    Enable strict validation mode. [Default: ``False``]

``--schema-file``
    Custom schema file (must exist).

``--ignore-patterns, --empty-ignore-patterns``
    Patterns to ignore during validation.

.. _cyclopts-complex-cli-server:

server
------

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
^^^^^

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
^^^^

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
^^^^^^^

Restart the server.

::

    complex-cli server restart [ARGS]

**Parameters:**

``ROLLING, --rolling, --no-rolling``
    Perform rolling restart (zero downtime). [Default: ``False``]

``DELAY, --delay``
    Delay between worker restarts in seconds. [Default: ``5``]

.. _cyclopts-complex-cli-cache:

cache
-----

Cache management commands.

**Commands:**

``clear``
    Clear cache entries.

``configure``
    Configure cache settings.

``stats``
    Show cache statistics.

.. _cyclopts-complex-cli-cache-configure:

configure
^^^^^^^^^

Configure cache settings.

Demonstrates attrs class support for CLI parameters.

::

    complex-cli cache configure [OPTIONS]

**Parameters:**

``--config.backend``
    Cache backend type. [Choices: ``memory``, ``redis``, ``memcached``, ``disk``, Default: ``memory``]

``--config.ttl``
    Time-to-live in seconds. [Default: ``300``]

``--config.max-size``
    Maximum cache size in MB. [Default: ``1024``]

``--config.compression, --config.no-compression``
    Enable compression. [Default: ``False``]

.. _cyclopts-complex-cli-cache-clear:

clear
^^^^^

Clear cache entries.

::

    complex-cli cache clear [ARGS]

**Parameters:**

``PATTERN, --pattern``
    Pattern to match cache keys. [Default: ``*``]

``DRY-RUN, --dry-run, --no-dry-run``
    Show what would be cleared without actually clearing. [Default: ``False``]

.. _cyclopts-complex-cli-cache-stats:

stats
^^^^^

Show cache statistics.

::

    complex-cli cache stats [ARGS]

**Parameters:**

``DETAILED, --detailed, --no-detailed``
    Show detailed statistics. [Default: ``False``]

``FORMAT, --format``
    Output format. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

.. _cyclopts-complex-cli-complex-types:

complex-types
-------------

Demonstrate complex type annotations.

This command showcases various complex type patterns that the
documentation system needs to handle correctly.

::

    complex-cli complex-types [ARGS]

**Parameters:**

``WORKER-COUNT, --worker-count``
    Number of workers or "auto" for automatic detection. [Choices: ``auto``, Default: ``auto``]

``QUALITY, --quality``
    Quality preset or "custom" for manual configuration. [Choices: ``low``, ``medium``, ``high``, ``custom``, Default: ``medium``]

``TAGS, --tags, --empty-tags``
    Optional list of tags.

``FORMATS, --formats, --empty-formats``
    List of output formats. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``[json]``]

``THRESHOLDS, --thresholds, --empty-thresholds``
    Threshold values or "default" for defaults. [Choices: ``default``, Default: ``default``]

``CONFIG-PATH, --config-path``
    Optional config file path (must exist if provided).

.. _cyclopts-complex-cli-numpy-style:

numpy-style
-----------

Command with NumPy-style docstring.

This command demonstrates NumPy docstring format which is the
default for cyclopts.

::

    complex-cli numpy-style NAME [ARGS]

**Parameters:**

``NAME, --name``
    The name parameter. [**Required**]

``COUNT, --count``
    The count parameter, by default 1. [Default: ``1``]

.. _cyclopts-complex-cli-google-style:

google-style
------------

Command with Google-style docstring.

This command demonstrates Google docstring format.

::

    complex-cli google-style NAME [ARGS]

**Parameters:**

``NAME, --name``
    The name parameter. [**Required**]

``COUNT, --count``
    The count parameter. Defaults to 1. [Default: ``1``]

.. _cyclopts-complex-cli-sphinx-style:

sphinx-style
------------

Command with Sphinx-style docstring.

This command demonstrates Sphinx/reST docstring format.

::

    complex-cli sphinx-style NAME [ARGS]

**Parameters:**

``NAME, --name``
    The name parameter. [**Required**]

``COUNT, --count``
    The count parameter. [Default: ``1``]

.. _cyclopts-complex-cli-secret-feature:

secret-feature
--------------

Secret feature command.

This command has a hidden parameter.

::

    complex-cli secret-feature [ARGS]

**Parameters:**

``ENABLE, --enable, --no-enable``
    Enable the secret feature. [Default: ``False``]
