import inspect
from typing import Any, Optional, get_origin

from cyclopts.annotations import (
    NotRequired,
    Required,
    is_namedtuple,
    is_pydantic,
    is_typeddict,
    resolve,
    resolve_annotated,
    resolve_optional,
)


class FieldInfo(inspect.Parameter):
    def __init__(self, *args, required: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = required

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
            hint = str if self.default is inspect.Parameter.empty or self.default is None else type(self.default)
        hint = resolve_optional(hint)
        return hint


def _typed_dict_field_info(typeddict) -> dict[str, FieldInfo]:
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


def _generic_class_field_info(
    f,
    include_var_positional=False,
    include_var_keyword=False,
) -> dict[str, FieldInfo]:
    signature = inspect.signature(f.__init__)
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


def _pydantic_field_info(model) -> dict[str, FieldInfo]:
    out = {}
    for name, pydantic_field in model.model_fields.items():
        out[name] = FieldInfo(
            name=name,
            kind=inspect.Parameter.KEYWORD_ONLY if pydantic_field.kw_only else inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=pydantic_field.annotation,
            required=pydantic_field.is_required(),
        )
    return out


def _namedtuple_field_info(hint) -> dict[str, FieldInfo]:
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


def get_field_info(
    hint,
    *,
    include_var_positional=False,
    include_var_keyword=False,
) -> dict[str, FieldInfo]:
    if is_pydantic(hint):
        return _pydantic_field_info(hint)
    elif is_namedtuple(hint):
        return _namedtuple_field_info(hint)
    elif is_typeddict(hint):
        return _typed_dict_field_info(hint)
    else:
        return _generic_class_field_info(hint)
