from cyclopts import types as ct


def test_types_json(convert):
    assert {"foo": "bar"} == convert(ct.Json, ['{"foo": "bar"}'])
