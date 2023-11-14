<div align="center">
  <img src="https://raw.githubusercontent.com/BrianPugh/Cyclopts/main/assets/logo_512w.png">
</div>

<div align="center">

![Python compat](https://img.shields.io/badge/>=python-3.8-blue.svg)
[![PyPI](https://img.shields.io/pypi/v/cyclopts.svg)](https://pypi.org/project/cyclopts/)
[![ReadTheDocs](https://readthedocs.org/projects/cyclopts/badge/?version=latest)](https://cyclopts.readthedocs.io/en/latest/?badge=latest)

</div>

---

Cyclopts is a modern, easy-to-use command-line interface (CLI) framework.
It offers a streamlined approach for building CLI applications with an emphasis on simplicity, extensibility, and robustness.
Cyclopts aims to provide an intuitive and efficient developer experience, making python CLI development more accessible and enjoyable.


# Why Cyclopts?

- *Intuitive API*: Cyclopts features a straightforward and intuitive API, making it easy for developers to create complex CLI applications with minimal code.

- *Advanced Type Hinting*: Cyclopts offers advanced type hinting features, allowing for more accurate and informative command-line interfaces.

- *Rich Help Generation*: Automatically generates beautiful, user-friendly help messages, ensuring that users can easily understand and utilize your CLI application.

- *Extensible and Customizable*: Designed with extensibility in mind, Cyclopts allows developers to easily add custom behaviors and integrate with other systems.


# Installation
Cyclopts requires Python >=3.8; to install Cyclopts, run:

```bash
pip install cyclopts
```

# Quick Start
Create an application using `cyclopts.App`, and then register commands using the `register` decorator.

```python
from cyclopts import App

app = App()


@app.register
def foo(loops: int):
    for i in range(loops):
        print(f"Looping! {i}")


@app.default
def default_action():
    print("Hello world! This runs when no command is specified.")


app()
```

Executing the script from the command line:

```bash
$ python demo.py
Hello world! This runs when no command is specified.

$ python demo.py foo 3
Looping! 0
Looping! 1
Looping! 2
```

With just a few additional lines of code, we have a full-featured CLI app.
