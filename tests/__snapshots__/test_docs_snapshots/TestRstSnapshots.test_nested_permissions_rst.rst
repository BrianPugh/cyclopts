.. _cyclopts-complex-cli:

complex-cli
-----------

::

    complex-cli COMMAND

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

``admin``
    Administrative commands for system management.

.. _cyclopts-complex-cli-admin:

admin
^^^^^

Administrative commands for system management.

**Commands:**

``users``
    User management commands.

.. _cyclopts-complex-cli-admin-users:

users
"""""

User management commands.

**Commands:**

``permissions``
    Permission management for users.

.. _cyclopts-complex-cli-admin-users-permissions:

permissions
'''''''''''

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
~~~~~

::

    complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION

Grant permissions to a user.

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
~~~~~~

::

    complex-cli admin users permissions revoke USERNAME PERMISSION

Revoke permissions from a user.

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to revoke. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

.. _cyclopts-complex-cli-admin-users-permissions-audit:

audit
~~~~~

::

    complex-cli admin users permissions audit [ARGS]

Audit permission changes.

**Parameters:**

``USERNAME, --username``
    Filter by username (all users if not specified).

``DAYS, --days``
    Number of days to look back. [Default: ``30``]

``FORMAT, --format``
    Output format for audit report. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``table``]

.. _cyclopts-complex-cli-admin-users-permissions-roles:

roles
~~~~~

Role template management.

**Commands:**

``create-role``
    Create a new role template.

``list-roles``
    List all role templates.

.. _cyclopts-complex-cli-admin-users-permissions-roles-list-roles:

list-roles
~~~~~~~~~~

::

    complex-cli admin users permissions roles list-roles [ARGS]

List all role templates.

**Parameters:**

``INCLUDE-SYSTEM, --include-system, --no-include-system``
    Include built-in system roles. [Default: ``False``]

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
