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
