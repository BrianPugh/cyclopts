"""Bash completion script generator.

This module will generate static bash completion scripts for Cyclopts applications.
The completion generator will follow a similar pattern to zsh.py:

1. **Extract** completion data using shared infrastructure from _base.py
2. **Transform** the data into bash completion primitives:
   - Commands → compgen -W "command list"
   - Parameters → COMPREPLY array
   - Literal/Enum choices → compgen -W "choice list"
   - Path types → compgen -f
3. **Generate** a static bash completion script using complete -F

Key differences from zsh:
- Uses COMPREPLY array instead of _arguments
- Uses compgen instead of _describe/_files
- 0-indexed word arrays instead of 1-indexed
- Different escaping rules
"""

import re
from typing import TYPE_CHECKING

from cyclopts.completion._base import (
    CompletionAction,
)

if TYPE_CHECKING:
    from cyclopts import App


def generate_completion_script(app: "App", prog_name: str) -> str:
    """Generate bash completion script.

    TODO: Implement bash completion script generation. This should:
    1. Validate prog_name (similar to zsh)
    2. Extract completion data using extract_completion_data(app)
    3. Generate bash completion function structure:
       - Use complete -F _<prog_name> <prog_name>
       - Access COMP_WORDS and COMP_CWORD variables
       - Build COMPREPLY array with completion suggestions
    4. Handle subcommands using case statements
    5. Support option completion with compgen -W
    6. Support file completion with compgen -f
    7. Support choice completion with compgen -W
    8. Handle negative flags (--empty-*, --no-*) separately from positive names:
       - Iterate argument.parameter.name for positive flags (use normal logic)
       - Iterate argument.negatives for negative flags (always treat as flags)
       - See zsh.py:_generate_keyword_specs() for reference implementation

    Parameters
    ----------
    app : App
        The Cyclopts application to generate completion for.
    prog_name : str
        Program name for completion function naming.
        Must be a valid shell identifier (alphanumeric and underscore).

    Returns
    -------
    str
        Complete bash completion script ready to source.

    Raises
    ------
    NotImplementedError
        This function is not yet implemented.
    ValueError
        If prog_name contains invalid characters.
    """
    if not prog_name or not re.match(r"^[a-zA-Z0-9_-]+$", prog_name):
        raise ValueError(f"Invalid prog_name: {prog_name!r}. Must be alphanumeric with hyphens/underscores.")

    raise NotImplementedError(
        "Bash completion support is not yet implemented. See cyclopts/completion/bash.py for implementation TODOs."
    )


def _escape_bash_choice(choice: str) -> str:
    """Escape special characters in a completion choice value for bash.

    TODO: Implement bash-specific escaping. Bash has different escaping rules than zsh:
    - In COMPREPLY array, single quotes are typically used
    - Spaces need to be handled differently
    - May need to use $'...' quoting for special characters

    Parameters
    ----------
    choice : str
        Raw choice value.

    Returns
    -------
    str
        Escaped choice value safe for bash completion.
    """
    raise NotImplementedError("Bash choice escaping not yet implemented")


def _escape_bash_description(text: str) -> str:
    """Escape special characters in description text for bash.

    TODO: Implement bash-specific description escaping.
    Note: Bash completion doesn't natively support descriptions like zsh does.
    This may be used for comments or help output, but basic bash completion
    typically doesn't show descriptions inline.

    Parameters
    ----------
    text : str
        Cleaned description text.

    Returns
    -------
    str
        Escaped description safe for bash completion.
    """
    raise NotImplementedError("Bash description escaping not yet implemented")


def _map_completion_action_to_bash(action: CompletionAction) -> str:
    """Map shell-agnostic completion action to bash-specific compgen flags.

    TODO: Implement mapping to bash compgen flags:
    - CompletionAction.FILES -> "-f" (compgen -f)
    - CompletionAction.DIRECTORIES -> "-d" (compgen -d)
    - CompletionAction.NONE -> ""

    Parameters
    ----------
    action : CompletionAction
        Shell-agnostic completion action.

    Returns
    -------
    str
        Bash compgen flags (e.g., "-f", "-d", or "").
    """
    raise NotImplementedError("Bash action mapping not yet implemented")
