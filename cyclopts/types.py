from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Sequence

from cyclopts import validators
from cyclopts.parameter import Parameter

if TYPE_CHECKING:
    from cyclopts.token import Token

__all__ = [
    # Path
    "ExistingPath",
    "ExistingFile",
    "ExistingDirectory",
    "Directory",
    "File",
    "ResolvedExistingPath",
    "ResolvedExistingFile",
    "ResolvedExistingDirectory",
    "ResolvedDirectory",
    "ResolvedFile",
    "ResolvedPath",
    # Path with extensions
    "BinPath",
    "ExistingBinPath",
    "CsvPath",
    "ExistingCsvPath",
    "ImagePath",
    "ExistingImagePath",
    "JsonPath",
    "ExistingJsonPath",
    "Mp4Path",
    "ExistingMp4Path",
    "TomlPath",
    "ExistingTomlPath",
    "TxtPath",
    "ExistingTxtPath",
    "YamlPath",
    "ExistingYamlPath",
    # Number
    "PositiveFloat",
    "NonNegativeFloat",
    "NegativeFloat",
    "NonPositiveFloat",
    "PositiveInt",
    "NonNegativeInt",
    "NegativeInt",
    "NonPositiveInt",
    "UInt8",
    "Int8",
    "UInt16",
    "Int16",
    "UInt32",
    "Int32",
    # Json,
    "Json",
]


########
# Path #
########
def _path_resolve_converter(type_, tokens: Sequence["Token"]):
    assert len(tokens) == 1
    return type_(tokens[0].value).resolve()


ExistingPath = Annotated[Path, Parameter(validator=validators.Path(exists=True))]
"A :class:`~pathlib.Path` file or directory that **must** exist."

ResolvedPath = Annotated[Path, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` file or directory. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."
ResolvedExistingPath = Annotated[ExistingPath, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` file or directory that **must** exist. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."

Directory = Annotated[Path, Parameter(validator=validators.Path(file_okay=False))]
"A :class:`~pathlib.Path` that **must** be a directory (or not exist)."
ExistingDirectory = Annotated[Path, Parameter(validator=validators.Path(exists=True, file_okay=False))]
"A :class:`~pathlib.Path` directory that **must** exist."
ResolvedDirectory = Annotated[Directory, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` directory. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."
ResolvedExistingDirectory = Annotated[ExistingDirectory, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` directory that **must** exist. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."

File = Annotated[Path, Parameter(validator=validators.Path(dir_okay=False))]
"A :class:`~pathlib.File` that **must** be a file (or not exist)."
ExistingFile = Annotated[Path, Parameter(validator=validators.Path(exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` file that **must** exist."
ResolvedFile = Annotated[File, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` file. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."
ResolvedExistingFile = Annotated[ExistingFile, Parameter(converter=_path_resolve_converter)]
"A :class:`~pathlib.Path` file that **must** exist. :meth:`~pathlib.Path.resolve` is invoked prior to returning the path."

# Common path extensions
BinPath = Annotated[Path, Parameter(validator=validators.Path(ext="bin", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``bin``."
ExistingBinPath = Annotated[Path, Parameter(validator=validators.Path(ext="bin", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``bin``."

CsvPath = Annotated[Path, Parameter(validator=validators.Path(ext="csv", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``csv``."
ExistingCsvPath = Annotated[Path, Parameter(validator=validators.Path(ext="csv", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``csv``."

TxtPath = Annotated[Path, Parameter(validator=validators.Path(ext="txt", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``txt``."
ExistingTxtPath = Annotated[Path, Parameter(validator=validators.Path(ext="txt", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``txt``."

ImagePath = Annotated[Path, Parameter(validator=validators.Path(ext=("png", "jpg", "jpeg"), dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension in {``png``, ``jpg``, ``jpeg``}."
ExistingImagePath = Annotated[
    Path, Parameter(validator=validators.Path(ext=("png", "jpg", "jpeg"), exists=True, dir_okay=False))
]
"A :class:`~pathlib.Path` that **must** exist and have extension in {``png``, ``jpg``, ``jpeg``}."

Mp4Path = Annotated[Path, Parameter(validator=validators.Path(ext="mp4", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``mp4``."
ExistingMp4Path = Annotated[Path, Parameter(validator=validators.Path(ext="mp4", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``mp4``."

JsonPath = Annotated[Path, Parameter(validator=validators.Path(ext="json", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``json``."
ExistingJsonPath = Annotated[Path, Parameter(validator=validators.Path(ext="json", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``json``."

TomlPath = Annotated[Path, Parameter(validator=validators.Path(ext="toml", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``toml``."
ExistingTomlPath = Annotated[Path, Parameter(validator=validators.Path(ext="toml", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``toml``."

YamlPath = Annotated[Path, Parameter(validator=validators.Path(ext="yaml", dir_okay=False))]
"A :class:`~pathlib.Path` that **must** have extension ``yaml``."
ExistingYamlPath = Annotated[Path, Parameter(validator=validators.Path(ext="yaml", exists=True, dir_okay=False))]
"A :class:`~pathlib.Path` that **must** exist and have extension ``yaml``."


##########
# Number #
##########
# foo
PositiveFloat = Annotated[float, Parameter(validator=validators.Number(gt=0))]
"A float that **must** be ``>0``."
NonNegativeFloat = Annotated[float, Parameter(validator=validators.Number(gte=0))]
"A float that **must** be ``>=0``."
NegativeFloat = Annotated[float, Parameter(validator=validators.Number(lt=0))]
"A float that **must** be ``<0``."
NonPositiveFloat = Annotated[float, Parameter(validator=validators.Number(lte=0))]
"A float that **must** be ``<=0``."

PositiveInt = Annotated[int, Parameter(validator=validators.Number(gt=0))]
"An int that **must** be ``>0``."
NonNegativeInt = Annotated[int, Parameter(validator=validators.Number(gte=0))]
"An int that **must** be ``>=0``."
NegativeInt = Annotated[int, Parameter(validator=validators.Number(lt=0))]
"An int that **must** be ``<0``."
NonPositiveInt = Annotated[int, Parameter(validator=validators.Number(lte=0))]
"An int that **must** be ``<=0``."

UInt8 = Annotated[int, Parameter(validator=validators.Number(gte=0, lte=255))]
"An unsigned 8-bit integer."
Int8 = Annotated[int, Parameter(validator=validators.Number(gte=-128, lte=127))]
"A signed 8-bit integer."

UInt16 = Annotated[int, Parameter(validator=validators.Number(gte=0, lte=65535))]
"An unsigned 16-bit integer."
Int16 = Annotated[int, Parameter(validator=validators.Number(gte=-32768, lte=32767))]
"A signed 16-bit integer."

UInt32 = Annotated[int, Parameter(validator=validators.Number(gte=0, lte=4294967295))]
"An unsigned 32-bit integer."
Int32 = Annotated[int, Parameter(validator=validators.Number(gte=-2147483648, lte=2147483647))]
"A signed 32-bit integer."


########
# Json #
########
def _json_converter(type_, tokens: Sequence["Token"]):
    import json

    assert len(tokens) == 1
    out = json.loads(tokens[0].value)
    return out


Json = Annotated[Any, Parameter(converter=_json_converter)]
"""
Parse a json-string from the CLI.

Note: Since Cyclopts v3.6.0, all dataclass-like classes now natively attempt
to parse json-strings, so practical use-case of this annotation is limited.

Usage example:

.. code-block:: python

    from cyclopts import App, types

    app = App()

    @app.default
    def main(json: types.Json):
        print(json)

    app()

.. code-block:: console

    $ my-script '{"foo": 1, "bar": 2}'
    {'foo': 1, 'bar': 2}
"""
