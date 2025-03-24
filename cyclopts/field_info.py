import inspect
import sys
from typing import (  # noqa: F401
    Annotated,
    Any,
    ClassVar,
    Optional,
    Sequence,
    get_args,
    get_origin,
    get_type_hints,
)

import attrs
from attrs import field

from cyclopts.annotations import (
    NotRequired,
    Required,
    is_annotated,
    is_attrs,
    is_dataclass,
    is_namedtuple,
    is_pydantic,
    is_typeddict,
    resolve,
    resolve_annotated,
    resolve_optional,
)
from cyclopts.utils import UNSET

POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


def _replace_annotated_type(src_type, dst_type):
    if not is_annotated(src_type):
        return dst_type
    return Annotated[(dst_type,) + get_args(src_type)[1:]]  # pyright: ignore


@attrs.define
class FieldInfo:
    """Extension of :class:`inspect.Parameter`."""

    names: tuple[str, ...] = ()
    kind: inspect._ParameterKind = inspect.Parameter.POSITIONAL_OR_KEYWORD

    required: bool = field(kw_only=True, default=False)
    default: Any = field(default=inspect.Parameter.empty, kw_only=True)
    annotation: Any = field(default=inspect.Parameter.empty, kw_only=True)

    help: Optional[str] = field(default=None, kw_only=True)
    """Can be populated by additional metadata from another library; e.g. ``pydantic.FieldInfo.description``."""

    ###################
    # Class Variables #
    ###################
    empty: ClassVar = inspect.Parameter.empty
    POSITIONAL_OR_KEYWORD: ClassVar = inspect.Parameter.POSITIONAL_OR_KEYWORD
    POSITIONAL_ONLY: ClassVar = inspect.Parameter.POSITIONAL_ONLY
    KEYWORD_ONLY: ClassVar = inspect.Parameter.KEYWORD_ONLY
    VAR_POSITIONAL: ClassVar = inspect.Parameter.VAR_POSITIONAL
    VAR_KEYWORD: ClassVar = inspect.Parameter.VAR_KEYWORD
    POSITIONAL: ClassVar[frozenset[inspect._ParameterKind]] = frozenset(
        {POSITIONAL_OR_KEYWORD, POSITIONAL_ONLY, VAR_POSITIONAL}
    )
    KEYWORD: ClassVar[frozenset[inspect._ParameterKind]] = frozenset({POSITIONAL_OR_KEYWORD, KEYWORD_ONLY, VAR_KEYWORD})

    @classmethod
    def from_iparam(cls, iparam: inspect.Parameter, *, annotation: Any = UNSET, required: Optional[bool] = None):
        if required is None:
            required = (
                iparam.default is iparam.empty
                and iparam.kind != iparam.VAR_KEYWORD
                and iparam.kind != iparam.VAR_POSITIONAL
            )

        return cls(
            names=(iparam.name,),
            annotation=iparam.annotation if annotation is UNSET else annotation,
            kind=iparam.kind,
            default=iparam.default,
            required=required,
        )

    @property
    def hint(self):
        """Annotation with Optional-removed and cyclopts type-inferring."""
        hint = self.annotation
        if hint is inspect.Parameter.empty or resolve(hint) is Any:
            hint = _replace_annotated_type(
                hint, str if self.default is inspect.Parameter.empty or self.default is None else type(self.default)
            )
        hint = resolve_optional(hint)
        return hint

    @property
    def name(self):
        """The **first** provided name."""
        return self.names[0]

    @property
    def is_positional(self) -> bool:
        return self.kind in self.POSITIONAL

    @property
    def is_positional_only(self) -> bool:
        return self.kind in (POSITIONAL_ONLY, VAR_POSITIONAL)

    @property
    def is_keyword(self) -> bool:
        return self.kind in self.KEYWORD

    @property
    def is_keyword_only(self) -> bool:
        return self.kind in (KEYWORD_ONLY, VAR_KEYWORD)

    def evolve(self, **kwargs):
        return attrs.evolve(self, **kwargs)


def _typed_dict_field_infos(typeddict) -> dict[str, FieldInfo]:
    # The ``__required_keys__`` and ``__optional_keys__`` attributes of TypedDict are kind of broken in <cp3.11.
    out = {}
    for name, annotation in get_type_hints(typeddict, include_extras=True).items():
        origin = get_origin(resolve_annotated(annotation))
        if origin is Required:
            required = True
        elif origin is NotRequired:
            required = False
        elif typeddict.__total__:  # Fields are REQUIRED by default.
            required = True
        else:  # Fields are OPTIONAL by default
            required = False
        out[name] = FieldInfo((name,), FieldInfo.KEYWORD_ONLY, annotation=annotation, required=required)
    return out


def _generic_class_field_infos(
    f,
    include_var_positional=False,
    include_var_keyword=False,
) -> dict[str, FieldInfo]:
    out = {}
    for name, field_info in signature_parameters(f.__init__).items():
        if field_info.name == "self":
            continue
        if not include_var_positional and field_info.kind is field_info.VAR_POSITIONAL:
            continue
        if not include_var_keyword and field_info.kind is field_info.VAR_KEYWORD:
            continue
        out[name] = field_info
    return out


def _pydantic_field_infos(model) -> dict[str, FieldInfo]:
    from pydantic_core import PydanticUndefined

    out = {}
    for python_name, pydantic_field in model.model_fields.items():
        names = []
        if pydantic_field.alias:
            if model.model_config.get("populate_by_name", False):
                names.append(python_name)
            names.append(pydantic_field.alias)
        else:
            names.append(python_name)

        # Extract Field with description from metadata
        help = pydantic_field.description or None
        for meta in pydantic_field.metadata:
            if hasattr(meta, "description") and meta.description:
                help = meta.description

        # Pydantic places ``Annotated`` data into pydantic.FieldInfo.metadata, while
        # pydantic.FieldInfo.annotation contains the "real" resolved type-hint.
        # We have to re-combine them into a single Annotated hint.
        if pydantic_field.metadata:
            annotation = Annotated[(pydantic_field.annotation,) + tuple(pydantic_field.metadata)]  # pyright: ignore
        else:
            annotation = pydantic_field.annotation

        out[python_name] = FieldInfo(
            names=tuple(names),
            kind=inspect.Parameter.KEYWORD_ONLY if pydantic_field.kw_only else inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=annotation,
            default=FieldInfo.empty if pydantic_field.default is PydanticUndefined else pydantic_field.default,
            required=pydantic_field.is_required(),
            help=help,
        )
    return out


def _namedtuple_field_infos(hint) -> dict[str, FieldInfo]:
    out = {}
    type_hints = get_type_hints(hint)
    for name in hint._fields:
        out[name] = FieldInfo(
            names=(name,),
            kind=FieldInfo.POSITIONAL_OR_KEYWORD,
            annotation=type_hints.get(name, str),
            default=hint._field_defaults.get(name, FieldInfo.empty),
            required=name not in hint._field_defaults,
        )
    return out


def _attrs_field_infos(hint) -> dict[str, FieldInfo]:
    out = {}
    field_infos = signature_parameters(hint.__init__)
    for attribute in hint.__attrs_attrs__:
        if not attribute.init:
            continue

        field_info = field_infos[attribute.alias]

        if isinstance(attribute.default, attrs.Factory):  # pyright: ignore
            required = False
            default = None  # Not strictly True, but we don't want to invoke factory
        elif attribute.default is attrs.NOTHING:
            required = True
            default = FieldInfo.empty
        else:
            required = False
            default = attribute.default

        out[field_info.name] = field_info.evolve(names=(attribute.alias,), required=required, default=default)
    return out


def _dataclass_field_infos(hint) -> dict[str, FieldInfo]:
    import dataclasses

    out = {}
    fields = dataclasses.fields(hint)
    type_hints = get_type_hints(hint, include_extras=True)  # resolves stringified type hints
    for f in fields:
        if f.default_factory is not dataclasses.MISSING:
            default = f.default_factory()
            required = False
        elif f.default is not dataclasses.MISSING:
            default = f.default
            required = False
        else:
            default = FieldInfo.empty
            required = True

        annotation = type_hints.get(f.name, FieldInfo.empty)

        if sys.version_info < (3, 10):  # pragma: no cover
            # Python3.9 does not have Field.kw_only attribute.
            kind = FieldInfo.POSITIONAL_OR_KEYWORD
        else:
            kind = FieldInfo.KEYWORD_ONLY if f.kw_only else FieldInfo.POSITIONAL_OR_KEYWORD

        out[f.name] = FieldInfo(
            names=(f.name,),
            kind=kind,
            required=required,
            annotation=annotation,
            default=default,
        )
    return out


def get_field_infos(hint) -> dict[str, FieldInfo]:
    if is_dataclass(hint):
        # This must be before ``is_pydantic`` check so that we
        # can handle pydantic dataclasses as vanilla dataclasses.
        return _dataclass_field_infos(hint)
    elif is_pydantic(hint):
        return _pydantic_field_infos(hint)
    elif is_namedtuple(hint):
        return _namedtuple_field_infos(hint)
    elif is_typeddict(hint):
        return _typed_dict_field_infos(hint)
    elif is_attrs(hint):
        return _attrs_field_infos(hint)
    else:
        return _generic_class_field_infos(hint)


def signature_parameters(f: Any) -> dict[str, FieldInfo]:
    type_hints = get_type_hints(f, include_extras=True)
    out = {}
    for name, iparam in inspect.signature(f).parameters.items():
        annotation = type_hints.get(name, iparam.annotation)
        out[name] = FieldInfo.from_iparam(iparam, annotation=annotation)
    return out
