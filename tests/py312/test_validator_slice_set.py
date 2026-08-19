"""Slice validator over ``set`` elements.

Lives under ``tests/py312`` because ``slice`` objects only became hashable in
Python 3.12; on earlier versions ``{slice(...)}`` cannot even be constructed
(and pyright flags it as unhashable). The ``dict`` mapping case, which does not
require hashable slices, stays in ``tests/validators/test_validator_slice.py``.
"""

import pytest

from cyclopts.validators import Slice


def test_validator_slice_set():
    """Sets are validated element-wise, just like sequences."""
    validator = Slice(allow_empty=False)
    validator(set[slice], {slice(0, 3)})

    with pytest.raises(ValueError):
        validator(set[slice], {slice(3, 1)})
