import sys

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Group, Parameter
from cyclopts.resolve import ResolvedCommand


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
    cparam = res.iparam_to_cparam[res.name_to_iparam["bar"]]
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
    cparam = res.iparam_to_cparam[res.name_to_iparam["bar"]]
    assert cparam.help == "This has priority."
