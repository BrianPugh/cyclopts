"""Test YAML configuration with lists of dataclasses and TypedDict.

This addresses GitHub issue #507.
"""

from dataclasses import dataclass
from textwrap import dedent
from typing import Literal, TypedDict

from cyclopts.config import Yaml


@dataclass
class User:
    name: str
    age: int
    region: Literal["us", "ca"] = "us"


class Config(TypedDict):
    name: str
    value: int


def test_yaml_list_of_dataclasses(app, tmp_path, assert_parse_args):
    """Test the exact scenario from GitHub issue #507 with YAML config."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            users:
              - name: alice
                age: 22
                region: us
              - name: bob
                age: 33
                region: ca
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(users: list[User]):
        pass

    # Parse with empty args, config should provide the users
    assert_parse_args(main, "", [User("alice", 22, "us"), User("bob", 33, "ca")])


def test_yaml_list_of_dataclasses_with_cli_override(app, tmp_path, assert_parse_args):
    """Test that CLI arguments override YAML config for list of dataclasses."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            users:
              - name: alice
                age: 22
                region: us
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(users: list[User]):
        pass

    # CLI should override config
    assert_parse_args(
        main,
        '--users \'{"name": "charlie", "age": 40, "region": "ca"}\'',
        [User("charlie", 40, "ca")],
    )


def test_yaml_empty_list_of_dataclasses(app, tmp_path, assert_parse_args):
    """Test empty list of dataclasses from YAML."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            users: []
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(users: list[User] = None):  # pyright: ignore
        pass

    assert_parse_args(main, "", [])


def test_yaml_single_dataclass_in_list(app, tmp_path, assert_parse_args):
    """Test single dataclass item in YAML list."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            users:
              - name: alice
                age: 30
                region: us
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(users: list[User]):
        pass

    assert_parse_args(main, "", [User("alice", 30, "us")])


def test_yaml_list_of_typeddict(app, tmp_path, assert_parse_args):
    """Test list of TypedDict from YAML config."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            configs:
              - name: config1
                value: 10
              - name: config2
                value: 20
              - name: config3
                value: 30
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(configs: list[Config]):
        pass

    assert_parse_args(
        main,
        "",
        [
            {"name": "config1", "value": 10},
            {"name": "config2", "value": 20},
            {"name": "config3", "value": 30},
        ],
    )


def test_yaml_nested_dataclass_structure(app, tmp_path, assert_parse_args):
    """Test nested dataclass structure from YAML."""

    @dataclass
    class Address:
        street: str
        city: str
        country: str = "US"

    @dataclass
    class Person:
        name: str
        age: int
        address: Address

    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            people:
              - name: alice
                age: 25
                address:
                  street: 123 Main St
                  city: New York
                  country: US
              - name: bob
                age: 30
                address:
                  street: 456 Oak Ave
                  city: Toronto
                  country: CA
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(people: list[Person]):
        pass

    expected = [
        Person("alice", 25, Address("123 Main St", "New York", "US")),
        Person("bob", 30, Address("456 Oak Ave", "Toronto", "CA")),
    ]

    assert_parse_args(main, "", expected)


def test_yaml_mixed_config_and_cli(app, tmp_path, assert_parse_args):
    """Test mixing YAML config with additional CLI arguments."""
    config_fn = tmp_path / "config.yaml"

    config_fn.write_text(
        dedent(
            """\
            users:
              - name: alice
                age: 22
                region: us
            """
        )
    )

    app.config = Yaml(config_fn)

    @app.default
    def main(users: list[User], verbose: bool = False):
        pass

    # Config provides users, CLI provides verbose flag
    assert_parse_args(main, "--verbose", users=[User("alice", 22, "us")], verbose=True)
