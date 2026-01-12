"""AST-based Argument classes for help generation without importing modules."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Iterator
from typing import Any

from attrs import Factory, define

from cyclopts.ast_utils import (
    ASTSignature,
    ResolvedAlias,
    classify_type_for_negatives,
    extract_signature_from_import_path,
)
from cyclopts.field_info import FieldInfo
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.utils import default_name_transform

# Mapping from AST type classification to representative Python types.
# Used by ASTArgument.negatives to call Parameter.get_negatives with a real type.
# "other" maps to None, meaning no negatives should be generated.
_TYPE_CLASS_TO_REPRESENTATIVE: dict[str, type | None] = {
    "bool": bool,
    "iterable": list,
    "other": None,
}


@define
class ASTArgument:
    """Minimal Argument-like structure for AST-based help generation.

    Provides the same interface as Argument for help generation,
    but built from AST extraction rather than runtime introspection.
    """

    field_info: FieldInfo
    """Field info extracted from AST (annotation stored as string)."""

    parameter: Parameter
    """Actual Parameter object (instantiated from AST or default)."""

    resolved_alias: ResolvedAlias | None = None
    """Resolved type alias info, if available."""

    index: int | None = None
    """Positional index, or None for keyword-only arguments."""

    keys: tuple[str, ...] = ()
    """Python keys that lead to this leaf (for nested types)."""

    children: list[ASTArgument] = Factory(list)
    """Child arguments (for complex types - usually empty for AST-based)."""

    @property
    def type_str(self) -> str:
        """The type annotation as a string for classification purposes."""
        if self.resolved_alias:
            return self.resolved_alias.base_type_str
        if self.field_info.annotation is not inspect.Parameter.empty:
            return self.field_info.annotation
        return ""

    @property
    def hint(self) -> Any:
        """The type hint as a string (for AST, we don't have runtime types)."""
        return self.type_str or "str"

    @property
    def name(self) -> str:
        """The first provided name this argument goes by."""
        return self.names[0] if self.names else ""

    @property
    def names(self) -> tuple[str, ...]:
        """Names the argument goes by (both positive and negative)."""
        assert isinstance(self.parameter.name, tuple)
        return self.parameter.name + self.negatives

    @property
    def negatives(self) -> tuple[str, ...]:
        """Negative flags computed from AST-based type classification."""
        type_class = classify_type_for_negatives(self.type_str)
        # Map type_class to a representative type for get_negatives.
        # This avoids polluting Parameter.get_negatives with AST-specific logic.
        representative_type = _TYPE_CLASS_TO_REPRESENTATIVE.get(type_class)
        if representative_type is None:
            return ()
        return self.parameter.get_negatives(representative_type)

    @property
    def show(self) -> bool:
        """Show this argument on the help page."""
        if self.children:
            return False
        if self.parameter.show is not None:
            return self.parameter.show
        return self.parse

    @property
    def parse(self) -> bool:
        """Whether this argument should be parsed from CLI tokens."""
        if self.parameter.parse is None:
            return True
        if isinstance(self.parameter.parse, re.Pattern):
            return bool(self.parameter.parse.search(self.field_info.name))
        return bool(self.parameter.parse)

    @property
    def required(self) -> bool:
        """Whether this argument requires a user-provided value."""
        if self.parameter.required is None:
            return self.field_info.required
        return self.parameter.required

    @property
    def show_default(self) -> bool | Callable[[Any], str]:
        """Show the default value on the help page."""
        if self.required:
            return False
        if self.parameter.show_default is None:
            return True
        return self.parameter.show_default

    def get_choices(self, force: bool = False) -> tuple[str, ...] | None:
        """Extract completion choices from type hint.

        For AST-based arguments, we can only extract choices from
        Literal types that are visible in the annotation string.
        """
        if not force and self.parameter.show_choices is False:
            return None

        if "Literal[" in self.type_str:
            return _extract_literal_choices(self.type_str, self.parameter.name_transform)

        return None

    def is_flag(self) -> bool:
        """Check if this argument is a flag (bool type)."""
        return classify_type_for_negatives(self.type_str) == "bool"


def _extract_literal_choices(type_str: str, name_transform: Callable[[str], str] | None) -> tuple[str, ...] | None:
    """Extract choices from a Literal type string.

    Parameters
    ----------
    type_str
        Type annotation string potentially containing Literal[...].
    name_transform
        Name transform function to apply to choices.

    Returns
    -------
    tuple[str, ...] | None
        Extracted choices, or None if not a Literal.
    """
    import ast

    # Find Literal[...] in the string
    start = type_str.find("Literal[")
    if start == -1:
        return None

    # Find matching bracket
    depth = 0
    end = start + 8  # len("Literal[")
    for i, char in enumerate(type_str[start + 8 :], start=start + 8):
        if char == "[":
            depth += 1
        elif char == "]":
            if depth == 0:
                end = i
                break
            depth -= 1

    literal_content = type_str[start + 8 : end]

    # Parse the literal content
    try:
        # Try to evaluate as Python literal
        choices = []
        for part in _split_literal_args(literal_content):
            part = part.strip()
            try:
                # Try to parse as Python literal
                value = ast.literal_eval(part)
                if name_transform:
                    choices.append(name_transform(str(value)))
                else:
                    choices.append(str(value))
            except (ValueError, SyntaxError):
                # Not a literal, skip
                pass
        return tuple(choices) if choices else None
    except Exception:
        return None


def _split_literal_args(content: str) -> list[str]:
    """Split Literal arguments, respecting nested brackets and quotes."""
    parts = []
    current = []
    depth = 0
    in_string = False
    string_char = None

    for char in content:
        if char in ('"', "'") and not in_string:
            in_string = True
            string_char = char
            current.append(char)
        elif char == string_char and in_string:
            in_string = False
            string_char = None
            current.append(char)
        elif char == "[" and not in_string:
            depth += 1
            current.append(char)
        elif char == "]" and not in_string:
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0 and not in_string:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        parts.append("".join(current).strip())

    return parts


class ASTArgumentCollection(list):
    """Collection of ASTArgument for help generation.

    Provides the same filtering interface as ArgumentCollection.
    """

    @classmethod
    def from_import_path(
        cls,
        import_path: str,
        default_parameter: Parameter | None = None,
    ) -> ASTArgumentCollection:
        """Build collection from import path using AST extraction.

        Parameters
        ----------
        import_path
            Import path in format "module.path:function_name".
        default_parameter
            Default parameter to combine with extracted parameters.

        Returns
        -------
        ASTArgumentCollection
            Collection of ASTArgument objects for help generation.
        """
        signature = extract_signature_from_import_path(import_path)
        return cls.from_signature(signature, default_parameter)

    @classmethod
    def from_signature(
        cls,
        signature: ASTSignature,
        default_parameter: Parameter | None = None,
    ) -> ASTArgumentCollection:
        """Build collection from an ASTSignature.

        Parameters
        ----------
        signature
            Extracted signature information.
        default_parameter
            Default parameter to combine with extracted parameters.

        Returns
        -------
        ASTArgumentCollection
            Collection of ASTArgument objects.
        """
        collection = cls()
        positional_index = 0

        # Create default groups (matches ArgumentCollection behavior)
        group_arguments = Group.create_default_arguments()
        group_parameters = Group.create_default_parameters()

        for param_name, field_info in signature.fields.items():
            # Get the extracted Parameter (if any) and combine with default
            extracted_param = signature.parameters.get(param_name)

            # Determine the default group based on whether it's positional or keyword
            default_group = group_arguments if field_info.is_positional else group_parameters

            # Build combined parameter with proper group assignment
            # Group priority: extracted_param.group > default_parameter.group > default_group
            combined_param = Parameter.combine(
                Parameter(group=default_group),
                default_parameter,
                extracted_param,
            )

            # Set up the parameter name if not already set
            if combined_param.name is None or combined_param.name == ():
                # Derive name from field name
                name_transform = combined_param.name_transform or default_name_transform
                if field_info.is_positional:
                    # Positional arguments get just the name
                    combined_param = Parameter.combine(combined_param, Parameter(name=param_name))
                else:
                    # Keyword arguments get --name
                    transformed = name_transform(param_name)
                    combined_param = Parameter.combine(combined_param, Parameter(name=f"--{transformed}"))

            # Get resolved alias info
            resolved_alias = signature.resolved_aliases.get(param_name)

            # Determine positional index
            index = None
            if field_info.is_positional and field_info.kind != inspect.Parameter.VAR_POSITIONAL:
                index = positional_index
                positional_index += 1

            # Set help from docstring if not in Parameter
            if combined_param.help is None and field_info.help:
                combined_param = Parameter.combine(combined_param, Parameter(help=field_info.help))

            argument = ASTArgument(
                field_info=field_info,
                parameter=combined_param,
                resolved_alias=resolved_alias,
                index=index,
                keys=(param_name,),
            )
            collection.append(argument)

        return collection

    @property
    def groups(self) -> list[Group]:
        """Get unique groups from all arguments in collection order.

        Matches the behavior of ArgumentCollection.groups.
        """
        groups = []
        for argument in self:
            assert isinstance(argument.parameter.group, tuple)
            for group in argument.parameter.group:
                if group not in groups:
                    groups.append(group)
        return groups

    def filter_by(
        self,
        *,
        group: Group | None = None,
        show: bool | None = None,
        parse: bool | None = None,
        required: bool | None = None,
    ) -> ASTArgumentCollection:
        """Filter arguments by various criteria.

        Parameters
        ----------
        group
            Filter by group.
        show
            Filter by show property.
        parse
            Filter by parse property.
        required
            Filter by required property.

        Returns
        -------
        ASTArgumentCollection
            Filtered collection.
        """
        result = ASTArgumentCollection()
        for arg in self:
            if group is not None and group not in arg.parameter.group:  # pyright: ignore
                continue
            if show is not None and arg.show != show:
                continue
            if parse is not None and arg.parse != parse:
                continue
            if required is not None and arg.required != required:
                continue
            result.append(arg)
        return result

    def __iter__(self) -> Iterator[ASTArgument]:
        return super().__iter__()
