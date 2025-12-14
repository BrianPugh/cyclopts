## complex-cli admin

Administrative commands for system management.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli admin users

User management commands.

**Commands**:

* `create`: Create a new user.
* `delete`: Delete a user.
* `list-users`: List all users.
* `permissions`: Permission management for users.

## complex-cli admin users list-users

List all users.

```console
complex-cli admin users list-users [ARGS]
```

**Parameters**:

* `ACTIVE-ONLY, --active-only, --no-active-only`: Show only active users.  *[default: False]*
* `ROLE, --role`: Filter by user role.  *[choices: admin, user, guest]*
* `LIMIT, --limit`: Maximum number of users to display.  *[default: 100]*
* `FORMAT, --format`: Output format.  *[choices: json, yaml, table, csv]*  *[default: table]*

## complex-cli admin users create

Create a new user.

```console
complex-cli admin users create [OPTIONS] USERNAME EMAIL
```

**Arguments**:

* `USERNAME`: Unique username for the new user.  **[required]**
* `EMAIL`: Email address for the new user.  **[required]**

**Parameters**:

* `--role`: User role assignment.  *[choices: admin, user, guest]*  *[default: user]*
* `--permissions.none, --permissions.no-none`: Initial permission flags.  *[default: False]*
* `--permissions.read, --permissions.no-read`: Initial permission flags.  *[default: False]*
* `--permissions.write, --permissions.no-write`: Initial permission flags.  *[default: False]*
* `--permissions.execute, --permissions.no-execute`: Initial permission flags.  *[default: False]*
* `--permissions.admin, --permissions.no-admin`: Initial permission flags.  *[default: False]*
* `--send-welcome, --no-send-welcome`: Send welcome email after creation.  *[default: True]*

## complex-cli admin users delete

Delete a user.

```console
complex-cli admin users delete [OPTIONS] USERNAME
```

**Arguments**:

* `USERNAME`: Username to delete.  **[required]**

**Parameters**:

* `--force, --no-force, -f`: Skip confirmation prompt.  *[default: False]*
* `--backup, --no-backup`: Create backup before deletion.  *[default: True]*

## complex-cli admin users permissions

Permission management for users.

## complex-cli admin users permissions grant

Grant permissions to a user.

```console
complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION
```

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to grant.  **[required]**  *[choices: none, read, write, execute, admin]*

**Parameters**:

* `--resource`: Specific resource to grant access to.
* `--expires`: Expiration date (ISO format).

## complex-cli admin users permissions revoke

Revoke permissions from a user.

```console
complex-cli admin users permissions revoke USERNAME PERMISSION
```

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to revoke.  **[required]**  *[choices: none, read, write, execute, admin]*

## complex-cli admin users permissions audit

Audit permission changes.

```console
complex-cli admin users permissions audit [ARGS]
```

**Parameters**:

* `USERNAME, --username`: Filter by username (all users if not specified).
* `DAYS, --days`: Number of days to look back.  *[default: 30]*
* `FORMAT, --format`: Output format for audit report.  *[choices: json, yaml, table, csv]*  *[default: table]*

## complex-cli admin users permissions roles

Role template management.

**Commands**:

* `create-role`: Create a new role template.
* `list-roles`: List all role templates.

## complex-cli admin users permissions roles list-roles

List all role templates.

```console
complex-cli admin users permissions roles list-roles [ARGS]
```

**Parameters**:

* `INCLUDE-SYSTEM, --include-system, --no-include-system`: Include built-in system roles.  *[default: False]*

## complex-cli admin users permissions roles create-role

Create a new role template.

```console
complex-cli admin users permissions roles create-role [OPTIONS] NAME
```

**Arguments**:

* `NAME`: Role name.  **[required]**

**Parameters**:

* `--permissions.none, --permissions.no-none`: Default permissions for this role.  *[default: False]*
* `--permissions.read, --permissions.no-read`: Default permissions for this role.  *[default: False]*
* `--permissions.write, --permissions.no-write`: Default permissions for this role.  *[default: False]*
* `--permissions.execute, --permissions.no-execute`: Default permissions for this role.  *[default: False]*
* `--permissions.admin, --permissions.no-admin`: Default permissions for this role.  *[default: False]*
* `--description`: Role description.  *[default: ""]*
