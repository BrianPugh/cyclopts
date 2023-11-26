<div align="center">
  <img src="https://raw.githubusercontent.com/BrianPugh/Cyclopts/main/assets/logo_512w.png">
</div>

<div align="center">

![Python compat](https://img.shields.io/badge/>=python-3.8-blue.svg)
[![PyPI](https://img.shields.io/pypi/v/cyclopts.svg)](https://pypi.org/project/cyclopts/)
[![ReadTheDocs](https://readthedocs.org/projects/cyclopts/badge/?version=latest)](https://cyclopts.readthedocs.io)
[![codecov](https://codecov.io/gh/BrianPugh/cyclopts/graph/badge.svg?token=HA393WIYUK)](https://codecov.io/gh/BrianPugh/cyclopts)


</div>

---

**Documentation:** https://cyclopts.readthedocs.io

**Source Code:** https://github.com/BrianPugh/cyclopts

---

Cyclopts is a modern, easy-to-use command-line interface (CLI) framework.
It offers a streamlined approach for building CLI applications with an emphasis on simplicity, extensibility, and robustness.
Cyclopts aims to provide an intuitive and efficient developer experience, making python CLI development more accessible and enjoyable.


# Why Cyclopts?

- **Intuitive API**: Cyclopts features a straightforward and intuitive API, making it easy for developers to create complex CLI applications with minimal code.

- **Advanced Type Hinting**: Cyclopts offers advanced type hinting features, allowing for more accurate and informative command-line interfaces.

- **Rich Help Generation**: Automatically generates beautiful, user-friendly help messages, ensuring that users can easily understand and utilize your CLI application.

- **Extensible and Customizable**: Designed with extensibility in mind, Cyclopts allows developers to easily add custom behaviors and integrate with other systems.


# Installation
Cyclopts requires Python >=3.8; to install Cyclopts, run:

```console
pip install cyclopts
```

# Quick Start
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

Consider the following short Cyclopts application:

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
Usage: my-script deploy [ARGS] [OPTIONS]

Deploy code to an environment.

╭─ Parameters ────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  ENV,--env            Environment to deploy to. [choices: dev,staging,prod] [required]                │
│    REPLICAS,--replicas  Number of workers to spin up. [choices: default,performance] [default: default] │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script deploy staging
Deploying to staging with 10 replicas.

$ my-script deploy staging 7
Deploying to staging with 7 replicas.

$ my-script deploy staging performance
Deploying to staging with 20 replicas.

$ my-script deploy nonexistant-env
╭─ Error ────────────────────────────────────────────────────────────────────────────────────────────╮
│ Error converting value "nonexistant-env" to typing.Literal['dev', 'staging', 'prod'] for "--env".  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

In its current state, this application would be impossible to implement in Typer.
However, lets see how close we can get with Typer:

```python
from typer import Typer, Argument
from typing import Annotated, Literal
from enum import Enum

app = Typer()


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


@app.callback()
def dummy_callback():
    pass


@app.command(help="Deploy code to an environment.")
def deploy(
    env: Annotated[Environment, Argument(help="Environment to deploy to.")],
    replicas: Annotated[
        int,
        Argument(
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
Usage: my-script [OPTIONS] ENV:{dev|staging|prod} [REPLICAS]

 Deploy code to an environment.

╭─ Arguments ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    env           ENV:{dev|staging|prod}  Environment to deploy to. [default: None] [required]                                       │
│      replicas      [REPLICAS]              Number of workers to spin up. [default: 10]                                                │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion        [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]              │
│ --show-completion           [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the     │
│                                                              installation.                                                            │
│                                                              [default: None]                                                          │
│ --help                                                       Show this message and exit.                                              │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

$ my-script deploy staging
Deploying to staging with 10 replicas.

$ my-script deploy staging 7
Deploying to staging with 7 replicas.

$ my-script deploy staging performance
Deploying to staging with 20 replicas.

$ my-script deploy nonexistant-env
Usage: my-script deploy [OPTIONS] ENV:{dev|staging|prod} [REPLICAS]
Try 'my-script deploy --help' for help.
╭─ Error ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Invalid value for 'ENV:{dev|staging|prod}': 'nonexistant-env' is not one of 'dev', 'staging', 'prod'.                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

The Typer implementation is 43 lines long, while the Cyclopts implementation is just 30, all while including a proper docstring.
Since Typer doesn't support Unions, the choices for ``replica`` could not be displayed on the help page.
We also had to include a dummy callback since our application currently only has a single command.
Cyclopts is much more terse, more more readable, and much more intuitive to use.
