import json
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from typing import Annotated, Literal

import pydantic
import pytest
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, SecretBytes, SecretStr, model_validator, validate_call
from pydantic import ValidationError as PydanticValidationError
from pydantic.alias_generators import to_camel

from cyclopts import MissingArgumentError, Parameter, ValidationError


# Modified from https://docs.pydantic.dev/latest/#pydantic-examples
class Outfit(BaseModel):
    body: str
    head: str
    has_socks: bool


class User(BaseModel):
    id: PositiveInt
    name: str = Field(default="John Doe")
    signup_ts: datetime | None
    tastes: dict[str, PositiveInt]
    outfit: Outfit | None = None


def test_pydantic_error_msg(app, console):
    @app.command
    @validate_call
    def foo(value: PositiveInt):
        print(value)

    assert app["foo"].default_command == foo

    # foo(1)
    with pytest.raises(PydanticValidationError):
        foo(-1)

    with console.capture() as capture, pytest.raises(ValidationError):
        app(["foo", "-1"], error_console=console, exit_on_error=False, print_error=True)

    actual = capture.get()

    expected_prefix = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value "-1" for "VALUE". 1 validation error for             │
        │ constrained-int                                                    │
        │   Input should be greater than 0 [type=greater_than,               │
        │ input_value=-1, input_type=int]                                    │
        │     For further information visit                                  │
        """
    )

    assert actual.startswith(expected_prefix)


def test_pydantic_validator_called_once(app):
    class M(BaseModel):
        x: list = Field(default_factory=list)

        @model_validator(mode="after")
        def fill(self):
            self.x.append("validator called")
            return self

    @app.default
    def default(
        m: Annotated[M, Field(default_factory=M)],
    ):
        assert m.x == ["foo", "validator called"]

    app(["foo"])


def test_pydantic_error_from_function_body(app):
    @app.command
    def foo(value: int):
        # id=-1 is not a valid PositiveError
        User(id=-1, signup_ts=None, tastes={})

    with pytest.raises(PydanticValidationError):
        app(["foo", "-1"])


def test_bind_pydantic_basemodel(app, assert_parse_args):
    @app.command
    def foo(user: User):
        pass

    external_data = {
        "id": 123,
        "signup_ts": "2019-06-01 12:22",
        "tastes": {
            "wine": 9,
            b"cheese": 7,
            "cabbage": "1",
        },
        "outfit": {
            "body": "t-shirt",
            "head": "baseball-cap",
            "has_socks": True,
        },
    }

    assert_parse_args(
        foo,
        'foo --user.id=123 --user.signup-ts="2019-06-01 12:22" --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap --user.outfit.has-socks',
        User(**external_data),
    )


def test_bind_pydantic_basemodel_from_json(app, assert_parse_args, monkeypatch):
    @app.command
    def foo(user: Annotated[User, Parameter(env_var="USER")]):
        pass

    external_data = {
        "id": 123,
        "signup_ts": "2019-06-01 12:22",
        "tastes": {
            "wine": 9,
            "cheese": 7,
            "cabbage": "1",
        },
        "outfit": {
            "body": "t-shirt",
            "head": "baseball-cap",
            "has_socks": True,
        },
    }

    monkeypatch.setenv("USER", json.dumps(external_data))

    assert_parse_args(
        foo,
        'foo --user.id=123 --user.signup-ts="2019-06-01 12:22" --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap --user.outfit.has-socks',
        User(**external_data),
    )


def test_bind_pydantic_basemodel_help(app, console):
    @app.default
    def foo(user: User):
        pass

    with console.capture() as capture:
        app("--help", console=console)
    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_pydantic USER.ID USER.SIGNUP-TS USER.TASTES [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.ID --user.id          [required]                           │
        │    USER.NAME --user.name      [default: John Doe]                  │
        │ *  USER.SIGNUP-TS             [required]                           │
        │      --user.signup-ts                                              │
        │ *  --user.tastes              [required]                           │
        │    --user.outfit.body                                              │
        │    --user.outfit.head                                              │
        │    --user.outfit.has-socks -                                       │
        │      -user.outfit.no-has-soc                                       │
        │      ks                                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_bind_pydantic_basemodel_missing_arg(app, console):
    """Partially defining an Outfit should raise a MissingArgumentError."""

    @app.command
    def foo(user: User):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app.parse_args(
            'foo --user.id=123 --user.signup-ts="2019-06-01 12:22" --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt',
            error_console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--user.outfit.head" requires an argument. │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_pydantic_alias_1(app, console, assert_parse_args):
    class User(BaseModel):
        model_config = ConfigDict(
            # A callable that takes a field name and returns an alias for it.
            alias_generator=to_camel,
            # Whether an aliased field may be populated by its name as given by the model attribute, as well as the alias.
            # e.g. for this model, both "user_name=" and "userName=" should work.
            populate_by_name=True,
            # Whether to build models and look up discriminators of tagged unions using python object attributes.
            from_attributes=True,
        )

        user_name: str
        "Name of user."

        age_in_years: int
        "Age of user in years."

    @app.command
    def foo(user: User):
        pass

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_pydantic foo USER.USER-NAME USER.AGE-IN-YEARS

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.USER-NAME         Name of user. [required]                 │
        │      --user.user-name                                              │
        │      --user.user-name                                              │
        │      --user.username                                               │
        │ *  USER.AGE-IN-YEARS      Age of user in years. [required]         │
        │      --user.age-in-years                                           │
        │      --user.age-in-years                                           │
        │      --user.ageinyears                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected

    # Test both the new canonical form and legacy form work
    assert_parse_args(
        foo,
        "foo --user.user-name='Bob Smith' --user.age-in-years=100",
        user=User(user_name="Bob Smith", age_in_years=100),
    )

    assert_parse_args(
        foo,
        "foo --user.username='Alice Jones' --user.ageinyears=50",
        user=User(user_name="Alice Jones", age_in_years=50),
    )


@pytest.mark.parametrize(
    "env_var",
    [
        '{"storage_class": "longhorn"}',
        '{"storageclass": "longhorn"}',  # Legacy form of camelCase alias
        # check for incorrectly parsing "null" as a string
        '{"storage_class": "longhorn", "limit": null}',
        # Test the actual Pydantic camelCase alias
        '{"storageClass": "longhorn"}',
    ],
)
def test_pydantic_alias_env_var_json(app, assert_parse_args, monkeypatch, env_var):
    """
    https://github.com/BrianPugh/cyclopts/issues/332
    """
    monkeypatch.setenv("SPEC", env_var)

    class BaseK8sModel(BaseModel):
        model_config = ConfigDict(
            alias_generator=to_camel,
            populate_by_name=True,
            from_attributes=True,
        )

    class Spec(BaseK8sModel):
        storage_class: str
        limit: int | None = None

    @app.default
    def run(spec: Annotated[Spec, Parameter(env_var="SPEC")]) -> None:
        pass

    assert_parse_args(run, "", Spec(storage_class="longhorn"))


def test_parameter_decorator_pydantic_nested_1(app, console):
    """
    https://github.com/BrianPugh/cyclopts/issues/320

    See Also
    --------
        test_parameter_decorator_dataclass_nested_1
    """

    class S3Path(BaseModel):
        bucket: Annotated[str, Parameter()]
        key: str

    @Parameter(name="*")  # Flatten namespace.
    class S3CliParams(BaseModel):
        path: Annotated[S3Path, Parameter(name="*")]
        region: Annotated[str, Parameter(name="area")]

    @app.command
    def action(*, s3_path: S3CliParams):
        pass

    with console.capture() as capture:
        app("action --help", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_pydantic action --bucket STR --key STR --area STR

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --bucket  [required]                                            │
        │ *  --key     [required]                                            │
        │ *  --area    [required]                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_pydantic_field_description(app, console):
    """Test that pydantic Field.description is used for help text."""

    class UserModel(BaseModel):
        # Simple case - Field.description should be used
        name: str = Field(description="User name.")

        # Parameter(help=...) takes precedence over Field
        name_with_param: Annotated[
            str,
            Parameter(help="User name with Parameter help."),
        ] = "Jane Doe"

        # Field description in Annotated should be used
        name_with_field_in_annotated: Annotated[
            str,
            Field(description="Description from Field in Annotated."),
        ] = "John Doe"

        # Another simple case
        age: int = Field(description="User age in years.")

    @app.default
    def main(user: UserModel):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()
    # Debugging output removed to avoid cluttering test outputs
    # If needed, use: logging.debug(f"Actual help content: {actual}")

    # Verify that Field.description is used for help text
    assert "User name." in actual

    # Verify that Parameter(help=...) takes precedence
    assert "User name with Parameter help." in actual

    # Verify that Field.description is used from Annotated as well
    assert "Description from Field in Annotated." in actual

    # Verify the other description is present
    assert "User age in years." in actual


def test_pydantic_annotated_field_discriminator(app, assert_parse_args, console):
    """From https://github.com/BrianPugh/cyclopts/issues/377"""

    class DatasetImage(pydantic.BaseModel):
        type: Literal["image"] = "image"
        path: str
        resolution: tuple[int, int]

    class DatasetVideo(pydantic.BaseModel):
        type: Literal["video"] = "video"
        path: str
        resolution: tuple[int, int]
        fps: int

    Dataset = Annotated[DatasetImage | DatasetVideo, pydantic.Field(discriminator="type")]

    @dataclass
    class Config:
        dataset: Dataset  # pyright: ignore[reportInvalidTypeForm]

    @app.default
    def main(
        config: Annotated[Config | None, Parameter(name="*")] = None,
    ):
        pass

    assert_parse_args(
        main,
        "--dataset.type=image --dataset.path foo.png --dataset.resolution 640 480",
        Config(DatasetImage(path="foo.png", resolution=(640, 480))),
    )
    assert_parse_args(
        main,
        "--dataset.type=video --dataset.path foo.mp4 --dataset.resolution 640 480 --dataset.fps 30",
        Config(DatasetVideo(path="foo.mp4", resolution=(640, 480), fps=30)),
    )

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_pydantic [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ DATASET.TYPE               [choices: image, video]                 │
        │   --dataset.type                                                   │
        │ DATASET.PATH                                                       │
        │   --dataset.path                                                   │
        │ DATASET.RESOLUTION                                                 │
        │   --dataset.resolution --                                          │
        │   dataset.empty-resolutio                                          │
        │   n                                                                │
        │ DATASET.FPS --dataset.fps                                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_pydantic_roundtrip_json_with_aliases(app, assert_parse_args, monkeypatch):
    """
    Test that Pydantic's own JSON serialization (which uses aliases by default)
    can be round-tripped through cyclopts environment variable loading.

    This ensures that if a user saves a Pydantic model to JSON and then loads it
    back through cyclopts, it works correctly.
    """
    import json

    class BaseK8sModel(BaseModel):
        model_config = ConfigDict(
            alias_generator=to_camel,
            populate_by_name=True,
            from_attributes=True,
        )

    class DatabaseConfig(BaseK8sModel):
        host: str = "localhost"
        port: int = 5432
        connection_timeout: int = 30
        max_pool_size: int = 10

    class Spec(BaseK8sModel):
        storage_class: str
        enable_caching: bool = True
        database_config: DatabaseConfig | None = None
        api_key: str | None = None

    # Create a Pydantic model instance with data
    original_spec = Spec(
        storage_class="fast-ssd",
        enable_caching=False,
        database_config=DatabaseConfig(host="db.example.com", port=3306, connection_timeout=60, max_pool_size=50),
        api_key="secret123",
    )

    # Serialize to JSON using Pydantic's model_dump_json with by_alias=True
    # This will use the camelCase aliases
    json_str = original_spec.model_dump_json(by_alias=True)

    # Verify the JSON has the expected camelCase structure
    json_data = json.loads(json_str)
    expected_json = {
        "storageClass": "fast-ssd",
        "enableCaching": False,
        "databaseConfig": {"host": "db.example.com", "port": 3306, "connectionTimeout": 60, "maxPoolSize": 50},
        "apiKey": "secret123",
    }
    assert json_data == expected_json

    # Now set this as environment variable and parse with cyclopts
    monkeypatch.setenv("SPEC", json_str)

    @app.default
    def run(spec: Annotated[Spec, Parameter(env_var="SPEC")]) -> None:
        pass

    # Should parse back to the exact same object
    assert_parse_args(run, "", original_spec)


@pytest.mark.parametrize(
    "dataclass_decorator",
    [
        dataclass,
        pydantic.dataclasses.dataclass,
    ],
)
def test_pydantic_annotated_field_discriminator_dataclass(app, assert_parse_args, dataclass_decorator):
    """Pydantic discriminator should work, even if the union'd types are not pydantic.BaseModel."""

    @dataclass_decorator
    class DatasetImage:
        type: Literal["image"]
        path: str
        resolution: tuple[int, int]

    @dataclass_decorator
    class DatasetVideo:
        type: Literal["video"]
        path: str
        resolution: tuple[int, int]
        fps: int

    Dataset = Annotated[DatasetImage | DatasetVideo, pydantic.Field(discriminator="type")]

    @dataclass_decorator
    class Config:
        dataset: Dataset  # pyright: ignore[reportInvalidTypeForm]

    @app.default
    def main(
        config: Annotated[Config | None, Parameter(name="*")] = None,
    ):
        pass

    assert_parse_args(
        main,
        "--dataset.type=image --dataset.path foo.png --dataset.resolution 640 480",
        Config(DatasetImage(type="image", path="foo.png", resolution=(640, 480))),  # pyright: ignore
    )
    assert_parse_args(
        main,
        "--dataset.type=video --dataset.path foo.mp4 --dataset.resolution 640 480 --dataset.fps 30",
        Config(DatasetVideo(type="video", path="foo.mp4", resolution=(640, 480), fps=30)),  # pyright: ignore
    )


def test_pydantic_list_empty_flag(app, assert_parse_args):
    """Regression test for https://github.com/BrianPugh/cyclopts/issues/572"""

    @Parameter(name="*")
    class Config(BaseModel):
        urls: Annotated[
            list[str] | None,
            Field(default=None, description="Optional list of URLs"),
            Parameter(
                consume_multiple=True,
            ),
        ]

    @app.default
    def command(config: Config | None = None):
        pass

    assert_parse_args(command, "--empty-urls", Config(urls=[]))


def test_pydantic_list_with_value(app, assert_parse_args):
    @Parameter(name="*")
    class Config(BaseModel):
        urls: Annotated[
            list[str] | None,
            Field(default=None, description="Optional list of URLs"),
            Parameter(
                consume_multiple=True,
            ),
        ]

    @app.default
    def command(config: Config | None = None):
        pass

    assert_parse_args(
        command,
        "--urls http://example.com http://example2.com",
        Config(
            urls=["http://example.com", "http://example2.com"],
        ),
    )


def test_pydantic_list_omitted(app, assert_parse_args):
    @Parameter(name="*")
    class Config(BaseModel):
        urls: Annotated[
            list[str] | None,
            Field(default=None, description="Optional list of URLs"),
            Parameter(
                consume_multiple=True,
            ),
        ]

    @app.default
    def command(config: Config | None = None):
        pass

    assert_parse_args(command, "")


def test_pydantic_nested_list_json(app):
    """Test that nested lists with JSON-serialized dicts are correctly parsed.

    Regression test for issue where JSON dict strings in lists were not being
    deserialized, causing Pydantic validation errors.
    Related to https://github.com/BrianPugh/cyclopts/issues/507
    """

    class SimpleConfig(BaseModel):
        bar: str

    class NestedConfig(BaseModel):
        foo: str
        simple_list: list[SimpleConfig]

    @app.command
    def nested_cmd(config: NestedConfig) -> NestedConfig:
        return config

    result = app(
        [
            "nested-cmd",
            "--config",
            '{"foo": "test", "simple_list": [{"bar": "simple1"}]}',
        ],
        exit_on_error=False,
    )

    assert result == NestedConfig(
        foo="test",
        simple_list=[SimpleConfig(bar="simple1")],
    )


def test_pydantic_secretstr_from_env(app, assert_parse_args, monkeypatch):
    """Test that Pydantic SecretStr works with environment variables.

    Regression test for https://github.com/BrianPugh/cyclopts/issues/619
    """
    monkeypatch.setenv("SOME_SECRET", "cycloptsIsAmazing")

    class ScriptSettings(BaseModel):
        some_secret: Annotated[SecretStr, Parameter(env_var="SOME_SECRET")]

    @app.command
    def test_cmd(s: Annotated[ScriptSettings, Parameter(name="*")]):
        pass

    assert_parse_args(
        test_cmd,
        "test-cmd",
        ScriptSettings(some_secret=SecretStr("cycloptsIsAmazing")),
    )


@pytest.mark.parametrize(
    "secret_type,value,expected_value",
    [
        (SecretStr, "mySecretValue", SecretStr("mySecretValue")),
        (SecretBytes, "mySecretBytes", SecretBytes(b"mySecretBytes")),
    ],
)
def test_pydantic_secret_explicit_value(app, assert_parse_args, secret_type, value, expected_value):
    """Test that Pydantic secret types work with explicit CLI values.

    Regression test for https://github.com/BrianPugh/cyclopts/issues/619
    """

    class ScriptSettings(BaseModel):
        some_secret: secret_type  # pyright: ignore[reportInvalidTypeForm]

    @app.command
    def test_cmd(s: Annotated[ScriptSettings, Parameter(name="*")]):
        pass

    assert_parse_args(
        test_cmd,
        f"test-cmd --some-secret {value}",
        ScriptSettings(some_secret=expected_value),
    )
