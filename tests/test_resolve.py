import inspect
import sys

import pytest

from cyclopts import Group, Parameter
from cyclopts.exceptions import DocstringError
from cyclopts.resolve import ResolvedCommand

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


def test_resolve_docstring():
    def foo(bar):
        """
        Parameters
        ----------
        bar
            Bar Docstring.
        """
        pass

    res = ResolvedCommand(foo)
    iparam = inspect.signature(foo).parameters["bar"]
    cparam = res.iparam_to_cparam[iparam]
    assert cparam.help == "Bar Docstring."


def test_resolve_docstring_parameter_priority():
    def foo(bar: Annotated[str, Parameter(help="This has priority.")]):
        """
        Parameters
        ----------
        bar
            Bar Docstring.
        """
        pass

    res = ResolvedCommand(foo)
    iparam = inspect.signature(foo).parameters["bar"]
    cparam = res.iparam_to_cparam[iparam]
    assert cparam.help == "This has priority."


def test_resolve_docstring_bad_parameter():
    def foo(bar):
        """
        Parameters
        ----------
        fizz
            Fizz Docstring.
        """
        pass

    with pytest.raises(DocstringError):
        ResolvedCommand(foo)


def test_group_name_collision():
    def foo(
        fizz: Annotated[str, Parameter(group=Group("Bar", show=True))],
        buzz: Annotated[str, Parameter(group=Group("Bar", show=False))],
    ):
        pass

    with pytest.raises(ValueError):
        ResolvedCommand(foo)
