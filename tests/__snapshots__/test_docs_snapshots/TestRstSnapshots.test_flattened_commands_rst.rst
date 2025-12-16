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

``--quiet, --no-quiet, -q``
    Suppress non-essential output. [Default: ``False``]

``--log-level``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

**Subcommands:**

``admin``
    Administrative commands for system management.

.. _cyclopts-complex-cli-admin:

complex-cli admin
-----------------

Administrative commands for system management.

**Commands:**

``users``
    User management commands.

.. _cyclopts-complex-cli-admin-users:

complex-cli admin users
-----------------------

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

complex-cli admin users list-users
----------------------------------

::

    complex-cli admin users list-users [ARGS]

List all users.

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

complex-cli admin users create
------------------------------

::

    complex-cli admin users create [OPTIONS] USERNAME EMAIL

Create a new user.

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

complex-cli admin users delete
------------------------------

::

    complex-cli admin users delete [OPTIONS] USERNAME

Delete a user.

**Arguments:**

``USERNAME``
    Username to delete. [**Required**]

**Parameters:**

``--force, --no-force, -f``
    Skip confirmation prompt. [Default: ``False``]

``--backup, --no-backup``
    Create backup before deletion. [Default: ``True``]

.. _cyclopts-complex-cli-admin-users-permissions:

complex-cli admin users permissions
-----------------------------------

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

complex-cli admin users permissions grant
-----------------------------------------

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

complex-cli admin users permissions revoke
------------------------------------------

::

    complex-cli admin users permissions revoke USERNAME PERMISSION

Revoke permissions from a user.

**Arguments:**

``USERNAME``
    Target username. [**Required**]

``PERMISSION``
    Permission flags to revoke. [**Required**, Choices: ``none``, ``read``, ``write``, ``execute``, ``admin``]

.. _cyclopts-complex-cli-admin-users-permissions-audit:

complex-cli admin users permissions audit
-----------------------------------------

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

complex-cli admin users permissions roles
-----------------------------------------

Role template management.

**Commands:**

``create-role``
    Create a new role template.

``list-roles``
    List all role templates.

.. _cyclopts-complex-cli-admin-users-permissions-roles-list-roles:

complex-cli admin users permissions roles list-roles
----------------------------------------------------

::

    complex-cli admin users permissions roles list-roles [ARGS]

List all role templates.

**Parameters:**

``INCLUDE-SYSTEM, --include-system, --no-include-system``
    Include built-in system roles. [Default: ``False``]

.. _cyclopts-complex-cli-admin-users-permissions-roles-create-role:

complex-cli admin users permissions roles create-role
-----------------------------------------------------

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
