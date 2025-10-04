# Cyclopts Demo - Shell Completion Test Application

This application is designed for testing shell completion features in Cyclopts.

## Purpose

Provides a comprehensive CLI application that exercises all major completion scenarios:

- **Boolean flags**: `--verbose`, `--dry-run`, `--reload`, `--ssl`
- **Literal choices**: `--environment {dev,staging,production}`, `--format {json,yaml,toml,xml}`
- **Path completion**: `--input-file`, `--output-file`, `--directory`, `--config`
- **Lists**: `--items`, `--tags`, `--exclude`, `--tables`
- **Numbers**: `--count`, `--port`, `--threshold`
- **Nested subcommands**: `database` and `server` groups with their own commands

## Usage

Install and run via Poetry:

```bash
# Install dependencies
poetry install

# Run the demo app
poetry run cyclopts-demo --help

# Test specific commands
poetry run cyclopts-demo files --help
poetry run cyclopts-demo database migrate --help
poetry run cyclopts-demo server start --help
```

## Commands

- **main** - Root command with verbose and config options
- **files** - File operations with path and format parameters
- **deploy** - Deployment with environment, region, and flags
- **process** - Item processing with lists and validation
- **database** - Database management group
  - `connect` - Database connection
  - `migrate` - Run migrations
  - `backup` - Create backups
- **server** - Server management group
  - `start` - Start the server
  - `stop` - Stop the server
  - `status` - Show server status

## Direct Invocation

The `cyclopts_demo.py` file can be invoked directly with Python 3.10+, but requires Cyclopts to be installed in the environment.
