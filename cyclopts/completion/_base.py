"""Shared shell completion infrastructure.

Provides data extraction, type analysis, and text processing utilities.
"""

import os
import re
import warnings
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args, get_origin

from cyclopts.annotations import is_union
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import CycloptsError
from cyclopts.group_extractors import groups_from_app
from cyclopts.utils import frozen, is_class_and_subclass

if TYPE_CHECKING:
    from cyclopts import App


class CompletionAction(Enum):
    """Shell-agnostic completion action types."""

    NONE = "none"
    FILES = "files"
    DIRECTORIES = "directories"


@frozen
class CompletionData:
    """Completion data for a command path."""

    arguments: "ArgumentCollection"
    commands: list["App"]


def extract_completion_data(app: "App") -> dict[tuple[str, ...], CompletionData]:
    """Recursively extract completion data for app and all subcommands.

    Parameters
    ----------
    app : App
        The Cyclopts application to extract completion data from.

    Returns
    -------
    dict[tuple[str, ...], CompletionData]
        Mapping from command path tuples to their completion data.
    """
    completion_data: dict[tuple[str, ...], CompletionData] = {}

    def _extract(command_path: tuple[str, ...] = ()):
        """Recursively extract completion data for command and subcommands."""
        try:
            _, execution_path, _ = app.parse_commands(list(command_path))
            command_app = execution_path[-1]
        except (CycloptsError, ValueError, TypeError, AttributeError) as e:
            if os.environ.get("CYCLOPTS_COMPLETION_DEBUG"):
                raise
            warnings.warn(f"Failed to extract completion data for command path {command_path!r}: {e}", stacklevel=2)
            completion_data[command_path] = CompletionData(arguments=ArgumentCollection(), commands=[])
            return

        arguments = ArgumentCollection()
        apps_for_params = app._get_resolution_context(execution_path)
        for subapp in apps_for_params:
            if subapp.default_command:
                app_arguments = subapp.assemble_argument_collection(parse_docstring=True)
                arguments.extend(app_arguments)

        commands = []
        for group, subapps in groups_from_app(command_app):
            if group.show:
                for subapp in subapps:
                    if subapp.show and subapp not in commands:
                        commands.append(subapp)

        completion_data[command_path] = CompletionData(arguments=arguments, commands=commands)

        for cmd_app in commands:
            for cmd_name in cmd_app.name:
                if not cmd_name.startswith("-"):
                    _extract(command_path + (cmd_name,))

    _extract()
    return completion_data


def get_completion_action(type_hint: Any) -> CompletionAction:
    """Get completion action from type hint.

    Parameters
    ----------
    type_hint : Any
        Type annotation.

    Returns
    -------
    CompletionAction
        Completion action for type.
    """
    if is_union(type_hint):
        for arg in get_args(type_hint):
            if arg is not type(None):
                action = get_completion_action(arg)
                if action != CompletionAction.NONE:
                    return action
        return CompletionAction.NONE

    target_type = get_origin(type_hint) or type_hint

    if target_type is Path or is_class_and_subclass(target_type, Path):
        return CompletionAction.FILES

    return CompletionAction.NONE


def clean_choice_text(text: str) -> str:
    """Clean choice text without shell-specific escaping.

    Parameters
    ----------
    text : str
        Raw choice text.

    Returns
    -------
    str
        Cleaned text (not shell-escaped).
    """
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_description_text(text: str, max_length: int = 80) -> str:
    """Clean and truncate description text without shell-specific escaping.

    Parameters
    ----------
    text : str
        Raw description text.
    max_length : int
        Maximum length before truncation (default: 80).

    Returns
    -------
    str
        Cleaned text (not shell-escaped).
    """
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_length:
        text = text[: max_length - 3] + "..."

    return text
