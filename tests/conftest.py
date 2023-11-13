import pytest

import cyclopts


@pytest.fixture
def app():
    return cyclopts.App()
