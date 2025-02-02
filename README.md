<div align="center">
  <img src="https://raw.githubusercontent.com/BrianPugh/Cyclopts/main/assets/logo_512w.png">
</div>

<div align="center">

![Python compat](https://img.shields.io/badge/>=python-3.9-blue.svg)
[![PyPI](https://img.shields.io/pypi/v/cyclopts.svg)](https://pypi.org/project/cyclopts/)
[![ReadTheDocs](https://readthedocs.org/projects/cyclopts/badge/?version=latest)](https://cyclopts.readthedocs.io)
[![codecov](https://codecov.io/gh/BrianPugh/cyclopts/graph/badge.svg?token=HA393WIYUK)](https://codecov.io/gh/BrianPugh/cyclopts)


</div>

---

**Documentation:** https://cyclopts.readthedocs.io

**Source Code:** https://github.com/BrianPugh/cyclopts

---

Cyclopts is a modern, easy-to-use command-line interface (CLI) framework that aims to provide an intuitive & efficient developer experience.

# Why Cyclopts?

- **Intuitive API**: Quickly write CLI applications using a terse, intuitive syntax.

- **Advanced Type Hinting**: Full support of all builtin types and even user-specified (yes, including [Pydantic](https://docs.pydantic.dev/latest/), [Dataclasses](https://docs.python.org/3/library/dataclasses.html), and [Attrs](https://www.attrs.org/en/stable/api.html)).

- **Rich Help Generation**: Automatically generates beautiful help pages from **docstrings** and other contextual data.

- **Extendable**: Easily customize converters, validators, token parsing, and application launching.

# Installation
Cyclopts requires Python >=3.9; to install Cyclopts, run:

```console
pip install cyclopts
```

# Quick Start
- Import `cyclopts.run()` and give it a function to run.

```python
from cyclopts import run

def foo(loops: int):
    for i in range(loops):
        print(f"Looping! {i}")

run(foo)
```

Execute the script from the command line:

```console
$ python start.py 3
Looping! 0
Looping! 1
Looping! 2
```

When you need more control:

- Create an application using `cyclopts.App`.
- Register commands with the `command` decorator.
- Register a default function with the `default` decorator.

```python
from cyclopts import App

app = App()

@app.command
def foo(loops: int):
    for i in range(loops):
        print(f"Looping! {i}")

@app.default
def default_action():
    print("Hello world! This runs when no command is specified.")

app()
```

Execute the script from the command line:

```console
$ python demo.py
Hello world! This runs when no command is specified.

$ python demo.py foo 3
Looping! 0
Looping! 1
Looping! 2
```
With just a few additional lines of code, we have a full-featured CLI app.
See [the docs](https://cyclopts.readthedocs.io) for more advanced usage.

# Compared to Typer
Cyclopts is what you thought Typer was.
Cyclopts's includes information from docstrings, support more complex types (even Unions and Literals!), and include proper validation support.
See [the documentation for a complete Typer comparison](https://cyclopts.readthedocs.io/en/latest/vs_typer/README.html).

Consider the following short 29-line Cyclopts application:

```python
import cyclopts
from typing import Literal

app = cyclopts.App()

@app.command
def deploy(
    env: Literal["dev", "staging", "prod"],
    replicas: int | Literal["default", "performance"] = "default",
):
    """Deploy code to an environment.

    Parameters
    ----------
    env
        Environment to deploy to.
    replicas
        Number of workers to spin up.
    """
    if replicas == "default":
        replicas = 10
    elif replicas == "performance":
        replicas = 20

    print(f"Deploying to {env} with {replicas} replicas.")


if __name__ == "__main__":
    app()
```

```console
$ my-script deploy --help
Usage: my-script.py deploy [ARGS] [OPTIONS]

Deploy code to an environment.

╭─ Parameters ────────────────────────────────────────────────────────────────────────────────────╮
│ *  ENV --env            Environment to deploy to. [choices: dev, staging, prod] [required]      │
│    REPLICAS --replicas  Number of workers to spin up. [choices: default, performance] [default: │
│                         default]                                                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script deploy staging
Deploying to staging with 10 replicas.

$ my-script deploy staging 7
Deploying to staging with 7 replicas.

$ my-script deploy staging performance
Deploying to staging with 20 replicas.

$ my-script deploy nonexistent-env
╭─ Error ────────────────────────────────────────────────────────────────────────────────────────────╮
│ Error converting value "nonexistent-env" to typing.Literal['dev', 'staging', 'prod'] for "--env".  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script --version
0.0.0
```

In its current state, this application would be impossible to implement in Typer.
However, lets see how close we can get with Typer (47-lines):

```python
import typer
from typing import Annotated, Literal
from enum import Enum

app = typer.Typer()

class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    prod = "prod"

def replica_parser(value: str):
    if value == "default":
        return 10
    elif value == "performance":
        return 20
    else:
        return int(value)

def _version_callback(value: bool):
    if value:
        print("0.0.0")
        raise typer.Exit()

@app.callback()
def callback(
    version: Annotated[
        bool | None, typer.Option("--version", callback=_version_callback)
    ] = None,
):
    pass

@app.command(help="Deploy code to an environment.")
def deploy(
    env: Annotated[Environment, typer.Argument(help="Environment to deploy to.")],
    replicas: Annotated[
        int,
        typer.Argument(
            parser=replica_parser,
            help="Number of workers to spin up.",
        ),
    ] = replica_parser("default"),
):
    print(f"Deploying to {env.name} with {replicas} replicas.")

if __name__ == "__main__":
    app()
```

```console
$ my-script deploy --help

Usage: my-script deploy [OPTIONS] ENV:{dev|staging|prod} [REPLICAS]

 Deploy code to an environment.

╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────╮
│ *    env           ENV:{dev|staging|prod}  Environment to deploy to. [default: None] [required] │
│      replicas      [REPLICAS]              Number of workers to spin up. [default: 10]          │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                     │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script deploy staging
Deploying to staging with 10 replicas.

$ my-script deploy staging 7
Deploying to staging with 7 replicas.

$ my-script deploy staging performance
Deploying to staging with 20 replicas.

$ my-script deploy nonexistent-env
Usage: my-script.py deploy [OPTIONS] ENV:{dev|staging|prod} [REPLICAS]
Try 'my-script.py deploy --help' for help.
╭─ Error ─────────────────────────────────────────────────────────────────────────────────────────╮
│ Invalid value for '[REPLICAS]': nonexistent-env                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script --version
0.0.0
```

The Typer implementation is 47 lines long, while the Cyclopts implementation is just 29 (38% shorter!).
Not only is the Cyclopts implementation significantly shorter, but the code is easier to read.
Since Typer does not support Unions, the choices for ``replica`` could not be displayed on the help page.
Cyclopts is much more terse, much more readable, and much more intuitive to use.
