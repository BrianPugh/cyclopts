<div align="center">
  <img src="https://raw.githubusercontent.com/BrianPugh/Cyclopts/main/assets/logo_512w.png">
</div>

<div align="center">

![Python compat](https://img.shields.io/badge/>=python-3.8-blue.svg)
[![PyPI](https://img.shields.io/pypi/v/cyclopts.svg)](https://pypi.org/project/cyclopts/)
[![ReadTheDocs](https://readthedocs.org/projects/cyclopts/badge/?version=latest)](https://cyclopts.readthedocs.io/en/latest/?badge=latest)

</div>

---

Intuitive, easy CLIs based on python type hints.

# Installation


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


@app.register_default
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
