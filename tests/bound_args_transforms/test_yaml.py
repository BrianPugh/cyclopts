from textwrap import dedent

from cyclopts.bound_args_transforms._yaml import Yaml


def test_bound_args_transform_yaml(tmp_path):
    fn = tmp_path / "test.yaml"
    fn.write_text(
        dedent(
            """\
            foo:
                key1: foo1
                key2: foo2

                function1:
                    key1: bar1
                    key2: bar2
            """
        )
    )
    config = Yaml(fn)
    assert config.config == {
        "foo": {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
        }
    }
