"""Completion generation must skip arguments that are never parsed (``Parameter(parse=False)``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import pytest

from cyclopts import App, Parameter

if TYPE_CHECKING:
    from collections import OrderedDict as Client


class _Injected:
    """Stands in for a dependency a launcher injects; its hint names a type imported only for type checking."""

    def __init__(self, client: Client) -> None:
        self.client = client


def _app() -> App:
    app = App(name="prog")

    @app.command
    def serve(port: int = 8000, *, service: Annotated[_Injected, Parameter(parse=False)]) -> None:
        """Serve.

        Parameters
        ----------
        port: int
            Port.
        """

    return app


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish", "powershell"])
def test_completion_skips_unparsed_arguments(shell):
    script = _app().generate_completion(prog_name="prog", shell=shell)
    assert "--port" in script
    assert "--service" not in script
