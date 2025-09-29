from pathlib import Path
from typing import Annotated

from cyclopts import Parameter


def test_bind_negative_none(app, assert_parse_args):
    @app.default
    def default(path: Annotated[Path | None, Parameter(negative_none="default-")]):
        pass

    assert_parse_args(default, "--default-path", None)
