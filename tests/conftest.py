import pytest
from rich.console import Console

import cyclopts


@pytest.fixture
def app():
    return cyclopts.App()


@pytest.fixture
def console():
    return Console(width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)
