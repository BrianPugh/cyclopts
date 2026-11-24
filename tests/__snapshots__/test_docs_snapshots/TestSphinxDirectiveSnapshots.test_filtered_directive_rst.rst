Complex CLI application for comprehensive documentation testing.

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin:


Administrative commands for system management.

**Commands:**

``users``
    User management commands.

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

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

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-list-users:

list-users
""""""""""

::

    complex-cli admin users list-users [OPTIONS] [ARGS]

List all users.

**Parameters:**

``ACTIVE-ONLY, --active-only``
    Show only active users. [Default: ``False``]

``ROLE, --role``
    Filter by user role. [Choices: ``admin``, ``user``, ``guest``]

``LIMIT, --limit``
    Maximum number of users to display. [Default: ``100``]

``FORMAT, --format``
    Output format. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-create:

create
""""""

::

    complex-cli admin users create [OPTIONS] USERNAME EMAIL

Create a new user.

**Arguments:**

``USERNAME``
    Unique username for the new user. [**Required**]

``EMAIL``
    Email address for the new user. [**Required**]

**Parameters:**

``--role CHOICE``
    User role assignment. [Choices: ``admin``, ``user``, ``guest``, Default: ``user``]

``--permissions.none``
    Initial permission flags. [Default: ``False``]

``--permissions.read``
    Initial permission flags. [Default: ``False``]

``--permissions.write``
    Initial permission flags. [Default: ``False``]

``--permissions.execute``
    Initial permission flags. [Default: ``False``]

``--permissions.admin``
    Initial permission flags. [Default: ``False``]

``--send-welcome``
    Send welcome email after creation. [Default: ``True``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-delete:

delete
""""""

::

    complex-cli admin users delete [OPTIONS] USERNAME

Delete a user.

**Arguments:**

``USERNAME``
    Username to delete. [**Required**]

**Parameters:**

``--force, -f``
    Skip confirmation prompt. [Default: ``False``]

``--backup``
    Create backup before deletion. [Default: ``True``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

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

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-grant:

grant
'''''

::

    complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION

Grant permissions to a user.

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to grant. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

**Parameters:**

``--resource STR``
    Specific resource to grant access to.

``--expires STR``
    Expiration date (ISO format).

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-revoke:

revoke
''''''

::

    complex-cli admin users permissions revoke [OPTIONS] USERNAME PERMISSION

Revoke permissions from a user.

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to revoke. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-audit:

audit
'''''

::

    complex-cli admin users permissions audit [OPTIONS] [ARGS]

Audit permission changes.

**Parameters:**

``USERNAME, --username``
    Filter by username (all users if not specified).

``DAYS, --days``
    Number of days to look back. [Default: ``30``]

``FORMAT, --format``
    Output format for audit report. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-roles:

roles
'''''

Role template management.

**Commands:**

``create-role``
    Create a new role template.

``list-roles``
    List all role templates.

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-roles-list-roles:

list-roles
~~~~~~~~~~

::

    complex-cli admin users permissions roles list-roles [OPTIONS] [ARGS]

List all role templates.

**Parameters:**

``INCLUDE-SYSTEM, --include-system``
    Include built-in system roles. [Default: ``False``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-roles-create-role:

create-role
~~~~~~~~~~~

::

    complex-cli admin users permissions roles create-role [OPTIONS] NAME

Create a new role template.

**Arguments:**

``NAME``
    Role name. [**Required**]

**Parameters:**

``--permissions.none``
    Default permissions for this role. [Default: ``False``]

``--permissions.read``
    Default permissions for this role. [Default: ``False``]

``--permissions.write``
    Default permissions for this role. [Default: ``False``]

``--permissions.execute``
    Default permissions for this role. [Default: ``False``]

``--permissions.admin``
    Default permissions for this role. [Default: ``False``]

``--description STR``
    Role description. [Default: ``""``]

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, -q, --no-quiet``
    Suppress non-essential output. [Default: ``False``]

``--log-level CHOICE``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]