# Admin Commands

Administrative commands for system management. This page demonstrates:

- **Nested command documentation** (4 levels deep)
- **Command filtering** using the `commands` option
- **Dataclass parameter flattening** in the `config` command

## admin

::: cyclopts
    module: complex_app:app
    heading_level: 3
    recursive: true
    commands: [admin]
    generate_toc: false

## User Management Deep Dive

The user management system supports 4 levels of command nesting:

1. `admin` - Top-level administrative commands
2. `admin users` - User management
3. `admin users permissions` - Permission management
4. `admin users permissions roles` - Role templates

### Just the Permissions Commands

This section shows only the permissions subcommand and its children:

::: cyclopts
    module: complex_app:app
    heading_level: 4
    recursive: true
    commands: [admin.users.permissions]
    generate_toc: false
