import sys

import pytest

from cyclopts.exceptions import ValidationError

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter


def test_allow_leading_hyphen(app):
    @app.default
    def foo(bar: Annotated[str, Parameter()]):
        pass

    with pytest.raises(ValidationError):
        app("--buzz", exit_on_error=False, print_error=True)
