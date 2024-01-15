import sys
from pathlib import Path

from cyclopts import validators
from cyclopts._convert import convert
from cyclopts.parameter import Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated  # pragma: no cover
else:
    from typing import Annotated  # pragma: no cover

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
    # Number
    "PositiveFloat",
    "NonNegativeFloat",
    "NegativeFloat",
    "NonPositiveFloat",
    "PositiveInt",
    "NonNegativeInt",
    "NegativeInt",
    "NonPositiveInt",
]


########
# Path #
########
def _path_resolve_converter(type_, *args):
    return convert(type_, *args, converter=lambda _, x: Path(x).resolve())


Directory = Annotated[Path, Parameter(validator=validators.Path(file_okay=False))]
File = Annotated[Path, Parameter(validator=validators.Path(dir_okay=False))]
ExistingPath = Annotated[Path, Parameter(validator=validators.Path(exists=True))]
ExistingDirectory = Annotated[Path, Parameter(validator=validators.Path(exists=True, file_okay=False))]
ExistingFile = Annotated[Path, Parameter(validator=validators.Path(exists=True, dir_okay=False))]

ResolvedDirectory = Annotated[Directory, Parameter(converter=_path_resolve_converter)]
ResolvedFile = Annotated[File, Parameter(converter=_path_resolve_converter)]
ResolvedExistingPath = Annotated[ExistingPath, Parameter(converter=_path_resolve_converter)]
ResolvedExistingDirectory = Annotated[ExistingDirectory, Parameter(converter=_path_resolve_converter)]
ResolvedExistingFile = Annotated[ExistingFile, Parameter(converter=_path_resolve_converter)]


##########
# Number #
##########
# foo
PositiveFloat = Annotated[float, Parameter(validator=validators.Number(gt=0))]
NonNegativeFloat = Annotated[float, Parameter(validator=validators.Number(gte=0))]
NegativeFloat = Annotated[float, Parameter(validator=validators.Number(lt=0))]
NonPositiveFloat = Annotated[float, Parameter(validator=validators.Number(lte=0))]

PositiveInt = Annotated[int, Parameter(validator=validators.Number(gt=0))]
NonNegativeInt = Annotated[int, Parameter(validator=validators.Number(gte=0))]
NegativeInt = Annotated[int, Parameter(validator=validators.Number(lt=0))]
NonPositiveInt = Annotated[int, Parameter(validator=validators.Number(lte=0))]
