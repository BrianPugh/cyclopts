Server management commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

### complex-cli server start

```console
complex-cli server start [OPTIONS]
```

Start the server with configuration.

Demonstrates Pydantic model support for CLI parameters.

**Parameters**:

* `--server.host STR`: Server bind address. *[default: 0.0.0.0]*
* `--server.port INT`: Server port number. *[default: 8000]*
* `--server.workers INT`: Number of worker processes. *[default: 4]*
* `--server.timeout FLOAT`: Request timeout in seconds. *[default: 30.0]*
* `--server.debug, --server.no-debug`: Enable debug mode. *[default: False]*
* `--auth.provider`: Authentication provider type. *[choices: oauth2, jwt, basic, none]* *[default: jwt]*
* `--auth.token-expiry INT`: Token expiration time in seconds. *[default: 3600]*
* `--auth.refresh-enabled, --auth.no-refresh-enabled`: Enable token refresh. *[default: True]*
* `--auth.allowed-origins LIST[STR], --auth.empty-allowed-origins`: List of allowed CORS origins. *[default: ['*']]*

### complex-cli server stop

```console
complex-cli server stop [OPTIONS]
```

Stop the server.

**Parameters**:

* `--graceful, --no-graceful`: Perform graceful shutdown. *[default: True]*
* `--timeout INT`: Shutdown timeout in seconds. *[default: 30]*
* `--force, -f, --no-force`: Force immediate shutdown. *[default: False]*

### complex-cli server restart

```console
complex-cli server restart [ARGS]
```

Restart the server.

**Parameters**:

* `ROLLING, --rolling, --no-rolling`: Perform rolling restart (zero downtime). *[default: False]*
* `DELAY, --delay`: Delay between worker restarts in seconds. *[default: 5]*
