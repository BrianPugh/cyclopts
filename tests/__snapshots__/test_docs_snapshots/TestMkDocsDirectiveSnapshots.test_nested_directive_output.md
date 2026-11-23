# Permissions

### complex-cli admin

Administrative commands for system management.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

#### complex-cli admin users

User management commands.

**Commands**:

* [`permissions`](#complex-cli-admin-users-permissions): Permission management for users.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

##### complex-cli admin users permissions

Permission management for users.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level CHOICE`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

###### complex-cli admin users permissions roles

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
complex-cli admin users permissions roles list-roles [ARGS]
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
