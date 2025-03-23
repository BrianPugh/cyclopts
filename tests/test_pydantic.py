import json
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from typing import Annotated, Dict, Literal, Optional, Union

import pydantic
import pytest
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, validate_call
from pydantic import ValidationError as PydanticValidationError
from pydantic.alias_generators import to_camel

from cyclopts import MissingArgumentError, Parameter


def test_pydantic_error_msg(app, console):
    @app.command
    @validate_call
    def foo(value: PositiveInt):
        print(value)

    assert app["foo"].default_command == foo

    foo(1)
    with pytest.raises(PydanticValidationError):
        foo(-1)

    with console.capture() as capture, pytest.raises(PydanticValidationError):
        app(["foo", "-1"], console=console, exit_on_error=False, print_error=True)

    actual = capture.get()

    expected_prefix = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ 1 validation error for test_pydantic_error_msg.<locals>.foo        │
        │ 0                                                                  │
        │   Input should be greater than 0 [type=greater_than,               │
        │ input_value=-1, input_type=int]                                    │
        │     For further information visit                                  │
        """
    )

    assert actual.startswith(expected_prefix)


# Modified from https://docs.pydantic.dev/latest/#pydantic-examples
class Outfit(BaseModel):
    body: str
    head: str
    has_socks: bool


class User(BaseModel):
    id: int
    name: str = Field(default="John Doe")
    signup_ts: Union[datetime, None]
    tastes: Dict[str, PositiveInt]
    outfit: Optional[Outfit] = None


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
        Usage: foo COMMAND [ARGS] [OPTIONS]

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
            console=console,
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
        Usage: test_pydantic foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.USER-NAME         Name of user. [required]                 │
        │      --user.user-name                                              │
        │      --user.username                                               │
        │ *  USER.AGE-IN-YEARS      Age of user in years. [required]         │
        │      --user.age-in-years                                           │
        │      --user.ageinyears                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected

    assert_parse_args(
        foo,
        "foo --user.username='Bob Smith' --user.age_in_years=100",
        user=User(user_name="Bob Smith", age_in_years=100),
    )


@pytest.mark.parametrize(
    "env_var",
    [
        '{"storage_class": "longhorn"}',
        '{"storageclass": "longhorn"}',
        # check for incorrectly parsing "null" as a string
        '{"storage_class": "longhorn", "limit": null}',
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
        limit: Optional[int] = None

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
        Usage: test_pydantic action [OPTIONS]

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

    Dataset = Annotated[Union[DatasetImage, DatasetVideo], pydantic.Field(discriminator="type")]

    @dataclass
    class Config:
        dataset: Dataset  # pyright: ignore[reportInvalidTypeForm]

    @app.default
    def main(
        config: Annotated[Optional[Config], Parameter(name="*")] = None,
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
        Usage: main COMMAND [ARGS] [OPTIONS]

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


@pytest.mark.parametrize(
    "dataclass_decorator",
    [
        dataclass,
        # pydantic.dataclasses.dataclass,  # Currently it seems like pydantic loses the "Annotated" portion of the type hint.
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

    Dataset = Annotated[Union[DatasetImage, DatasetVideo], pydantic.Field(discriminator="type")]

    @dataclass_decorator
    class Config:
        dataset: Dataset  # pyright: ignore[reportInvalidTypeForm]

    @app.default
    def main(
        config: Annotated[Optional[Config], Parameter(name="*")] = None,
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
