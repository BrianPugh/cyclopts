from typing import Dict, List, Optional, Tuple

import pytest

from cyclopts.exceptions import MissingArgumentError


@pytest.mark.skip(reason="TODO")
def test_unannotated_typing_dict(app, assert_parse_args):
    @app.command
    def foo(d: Dict):
        pass

    assert_parse_args(foo, "foo --d.key1='val1' --d.key2='val2'", d={"key1": "val1", "key2": "val2"})
