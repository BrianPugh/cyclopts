import inspect
from typing import Annotated, Any, Optional, get_args, get_origin  # noqa: F401

import attrs

import cyclopts.utils
from cyclopts.annotations import (
    NotRequired,
    Required,
    is_annotated,
    is_attrs,
    is_namedtuple,
    is_pydantic,
    is_typeddict,
    resolve,
    resolve_annotated,
    resolve_optional,
)

POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


def _replace_annotated_type(src_type, dst_type):
    if not is_annotated(src_type):
        return dst_type
    return Annotated[(dst_type,) + get_args(src_type)[1:]]  # pyright: ignore


class FieldInfo(inspect.Parameter):
    """Extension of :class:`inspect.Parameter`."""

    POSITIONAL = frozenset({POSITIONAL_OR_KEYWORD, POSITIONAL_ONLY, VAR_POSITIONAL})
    KEYWORD = frozenset({POSITIONAL_OR_KEYWORD, KEYWORD_ONLY, VAR_KEYWORD})

    def __init__(self, *args, required: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = required
        self._mutable_kind = super().kind

    @property
    def kind(self):
        return self._mutable_kind

    @kind.setter
    def kind(self, value):
        if not isinstance(value, inspect._ParameterKind):
            raise TypeError("'kind' must be an instance of _ParameterKind")
        self._mutable_kind = value

    @classmethod
    def from_iparam(cls, iparam, *, required: Optional[bool] = None):
        if required is None:
            required = (
                iparam.default is iparam.empty
                and iparam.kind != iparam.VAR_KEYWORD
                and iparam.kind != iparam.VAR_POSITIONAL
            )

        return cls(
            name=iparam.name,
            annotation=iparam.annotation,
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


def _typed_dict_field_infos(typeddict) -> dict[str, FieldInfo]:
    # The ``__required_keys__`` and ``__optional_keys__`` attributes of TypedDict are kind of broken in <cp3.11.
    out = {}
    # Don't use get_type_hints because it resolves Annotated automatically.
    for name, annotation in typeddict.__annotations__.items():
        origin = get_origin(resolve_annotated(annotation))
        if origin is Required:
            required = True
        elif origin is NotRequired:
            required = False
        elif typeddict.__total__:  # Fields are REQUIRED by default.
            required = True
        else:  # Fields are OPTIONAL by default
            required = False
        out[name] = FieldInfo(name, FieldInfo.KEYWORD_ONLY, annotation=annotation, required=required)
    return out


def _generic_class_field_infos(
    f,
    include_var_positional=False,
    include_var_keyword=False,
) -> dict[str, FieldInfo]:
    signature = cyclopts.utils.signature(f.__init__)
    out = {}
    for name, iparam in signature.parameters.items():
        if iparam.name == "self":
            continue
        if not include_var_positional and iparam.kind is iparam.VAR_POSITIONAL:
            continue
        if not include_var_keyword and iparam.kind is iparam.VAR_KEYWORD:
            continue
        out[name] = FieldInfo.from_iparam(iparam)
    return out


def _pydantic_field_infos(model) -> dict[str, FieldInfo]:
    from pydantic_core import PydanticUndefined

    out = {}
    for name, pydantic_field in model.model_fields.items():
        out[name] = FieldInfo(
            name=name,
            kind=inspect.Parameter.KEYWORD_ONLY if pydantic_field.kw_only else inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=pydantic_field.annotation,
            default=FieldInfo.empty if pydantic_field.default is PydanticUndefined else pydantic_field.default,
            required=pydantic_field.is_required(),
        )
    return out


def _namedtuple_field_infos(hint) -> dict[str, FieldInfo]:
    out = {}
    for name in hint._fields:
        out[name] = FieldInfo(
            name=name,
            kind=FieldInfo.POSITIONAL_OR_KEYWORD,
            annotation=hint.__annotations__.get(name, str),
            default=hint._field_defaults.get(name, FieldInfo.empty),
            required=name not in hint._field_defaults,
        )
    return out


def _attrs_field_infos(hint) -> dict[str, FieldInfo]:
    out = {}
    signature = cyclopts.utils.signature(hint.__init__)
    iparams = signature.parameters
    for attribute in hint.__attrs_attrs__:
        iparam = iparams[attribute.name]

        if isinstance(attribute.default, attrs.Factory):  # pyright: ignore
            required = False
            default = None  # Not strictly True, but we don't want to invoke factory
        elif attribute.default is attrs.NOTHING:
            required = True
            default = FieldInfo.empty
        else:
            required = False
            default = attribute.default

        out[iparam.name] = FieldInfo(
            name=attribute.alias,
            annotation=attribute.type,
            kind=iparam.kind,
            default=default,
            required=required,
        )
    return out


def get_field_infos(
    hint,
    *,
    include_var_positional=False,
    include_var_keyword=False,
) -> dict[str, FieldInfo]:
    if is_pydantic(hint):
        return _pydantic_field_infos(hint)
    elif is_namedtuple(hint):
        return _namedtuple_field_infos(hint)
    elif is_typeddict(hint):
        return _typed_dict_field_infos(hint)
    elif is_attrs(hint):
        return _attrs_field_infos(hint)
    else:
        return _generic_class_field_infos(hint)
