### complex-cli admin

Administrative commands for system management.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

#### complex-cli admin users

User management commands.

**Commands**:

* `permissions`: Permission management for users.

##### complex-cli admin users permissions

Permission management for users.

###### complex-cli admin users permissions grant

```console
complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION
```

Grant permissions to a user.

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to grant.  **[required]**  *[choices: none, read, write, execute, admin]*

**Parameters**:

* `--resource`: Specific resource to grant access to.
* `--expires`: Expiration date (ISO format).

###### complex-cli admin users permissions revoke

```console
complex-cli admin users permissions revoke USERNAME PERMISSION
```

Revoke permissions from a user.

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to revoke.  **[required]**  *[choices: none, read, write, execute, admin]*

###### complex-cli admin users permissions audit

```console
complex-cli admin users permissions audit [ARGS]
```

Audit permission changes.

**Parameters**:

* `USERNAME, --username`: Filter by username (all users if not specified).
* `DAYS, --days`: Number of days to look back.  *[default: 30]*
* `FORMAT, --format`: Output format for audit report.  *[choices: json, yaml, table, csv]*  *[default: table]*

###### complex-cli admin users permissions roles

Role template management.

**Commands**:

* `create-role`: Create a new role template.
* `list-roles`: List all role templates.

###### complex-cli admin users permissions roles list-roles

```console
complex-cli admin users permissions roles list-roles [ARGS]
```

List all role templates.

**Parameters**:

* `INCLUDE-SYSTEM, --include-system, --no-include-system`: Include built-in system roles.  *[default: False]*

###### complex-cli admin users permissions roles create-role

```console
complex-cli admin users permissions roles create-role [OPTIONS] NAME
```

Create a new role template.

**Arguments**:

* `NAME`: Role name.  **[required]**

**Parameters**:

* `--permissions.none, --permissions.no-none`: Default permissions for this role.  *[default: False]*
* `--permissions.read, --permissions.no-read`: Default permissions for this role.  *[default: False]*
* `--permissions.write, --permissions.no-write`: Default permissions for this role.  *[default: False]*
* `--permissions.execute, --permissions.no-execute`: Default permissions for this role.  *[default: False]*
* `--permissions.admin, --permissions.no-admin`: Default permissions for this role.  *[default: False]*
* `--description`: Role description.  *[default: ""]*
