# Admin Commands

## complex-cli admin

Administrative commands for system management.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

### complex-cli admin users

User management commands.

**Commands**:

* [`create`](#complex-cli-admin-users-create): Create a new user.
* [`delete`](#complex-cli-admin-users-delete): Delete a user.
* [`list-users`](#complex-cli-admin-users-list-users): List all users.
* [`permissions`](#complex-cli-admin-users-permissions): Permission management for users.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

#### complex-cli admin users list-users

```console
complex-cli admin users list-users [OPTIONS] [ARGS]
```

List all users.

**Parameters**:

* `ACTIVE-ONLY, --active-only`: Show only active users. *[default: False]*
* `ROLE, --role`: Filter by user role. *[choices: admin, user, guest]*
* `LIMIT, --limit`: Maximum number of users to display. *[default: 100]*
* `FORMAT, --format`: Output format. *[choices: json, yaml, table, csv]* *[default: table]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

#### complex-cli admin users create

```console
complex-cli admin users create [OPTIONS] USERNAME EMAIL
```

Create a new user.

**Arguments**:

* `USERNAME`: Unique username for the new user. **[required]**
* `EMAIL`: Email address for the new user. **[required]**

**Parameters**:

* `--role CHOICE`: User role assignment. *[choices: admin, user, guest]* *[default: user]*
* `--permissions.none`: Initial permission flags. *[default: False]*
* `--permissions.read`: Initial permission flags. *[default: False]*
* `--permissions.write`: Initial permission flags. *[default: False]*
* `--permissions.execute`: Initial permission flags. *[default: False]*
* `--permissions.admin`: Initial permission flags. *[default: False]*
* `--send-welcome`: Send welcome email after creation. *[default: True]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

#### complex-cli admin users delete

```console
complex-cli admin users delete [OPTIONS] USERNAME
```

Delete a user.

**Arguments**:

* `USERNAME`: Username to delete. **[required]**

**Parameters**:

* `--force, -f`: Skip confirmation prompt. *[default: False]*
* `--backup`: Create backup before deletion. *[default: True]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

#### complex-cli admin users permissions

Permission management for users.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

##### complex-cli admin users permissions grant

```console
complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION
```

Grant permissions to a user.

**Arguments**:

* `USERNAME`: Target username. **[required]**
* `PERMISSION`: Permission flags to grant. **[required]** *[choices: none, read, write, execute, admin]*

**Parameters**:

* `--resource STR`: Specific resource to grant access to.
* `--expires STR`: Expiration date (ISO format).

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

##### complex-cli admin users permissions revoke

```console
complex-cli admin users permissions revoke [OPTIONS] USERNAME PERMISSION
```

Revoke permissions from a user.

**Arguments**:

* `USERNAME`: Target username. **[required]**
* `PERMISSION`: Permission flags to revoke. **[required]** *[choices: none, read, write, execute, admin]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

##### complex-cli admin users permissions audit

```console
complex-cli admin users permissions audit [OPTIONS] [ARGS]
```

Audit permission changes.

**Parameters**:

* `USERNAME, --username`: Filter by username (all users if not specified).
* `DAYS, --days`: Number of days to look back. *[default: 30]*
* `FORMAT, --format`: Output format for audit report. *[choices: json, yaml, table, csv]* *[default: table]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

##### complex-cli admin users permissions roles

Role template management.

**Commands**:

* [`create-role`](#complex-cli-admin-users-permissions-roles-create-role): Create a new role template.
* [`list-roles`](#complex-cli-admin-users-permissions-roles-list-roles): List all role templates.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

###### complex-cli admin users permissions roles list-roles

```console
complex-cli admin users permissions roles list-roles [OPTIONS] [ARGS]
```

List all role templates.

**Parameters**:

* `INCLUDE-SYSTEM, --include-system`: Include built-in system roles. *[default: False]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

###### complex-cli admin users permissions roles create-role

```console
complex-cli admin users permissions roles create-role [OPTIONS] NAME
```

Create a new role template.

**Arguments**:

* `NAME`: Role name. **[required]**

**Parameters**:

* `--permissions.none`: Default permissions for this role. *[default: False]*
* `--permissions.read`: Default permissions for this role. *[default: False]*
* `--permissions.write`: Default permissions for this role. *[default: False]*
* `--permissions.execute`: Default permissions for this role. *[default: False]*
* `--permissions.admin`: Default permissions for this role. *[default: False]*
* `--description STR`: Role description. *[default: ""]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*
