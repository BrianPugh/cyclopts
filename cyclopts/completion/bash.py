r"""Bash completion script generator.

This module generates static bash completion scripts for Cyclopts applications.
The completion generator follows a similar pattern to zsh.py:

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
- 0-indexed word arrays instead of 1-indexed (COMP_WORDS[0] is the command)
- Different escaping rules

Bash-Specific Design Decisions
-------------------------------

**Escaping Strategy:**
Bash completion requires careful escaping to prevent shell injection. This module uses:
- Single quotes with '\'' for embedded single quotes (e.g., "don't" → "don'\''t")
- Backslash escaping for: $ ` \\ " and space
- No need for printf %q since we control the output format
- Special characters in choices are escaped before inclusion in compgen -W lists

**Description Handling:**
Unlike zsh's _describe which shows inline descriptions, bash completion does NOT natively
support showing help text during completion. Therefore:
- Descriptions are OMITTED from completion output (not shown to users)
- Help text is preserved in comments for documentation purposes only
- Future enhancement: Could use compopt -o nosort with special formatting, but this is
  not widely supported across bash versions (requires bash 4.4+)

**COMPREPLY Array:**
The completion function populates the COMPREPLY array with suggestions:
- COMPREPLY=( $(compgen -W "option1 option2" -- "$current_word") )
- Bash handles filtering based on the current partial word automatically
- Each element in COMPREPLY is a completion candidate

**compgen Flags:**
- compgen -W "word list" → Generate completions from word list
- compgen -f → Generate file completions
- compgen -d → Generate directory completions
- compgen -A file → Alternative file completion syntax

**Compatibility:**
- Targets bash 3.2+ (macOS default) through bash 5.x
- Avoids bash 4+ specific features for maximum portability
- Uses COMP_WORDS, COMP_CWORD standard completion variables
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
    r"""Escape special characters in a completion choice value for bash.

    Uses single-quote escaping with '\'' for embedded quotes, plus backslash escaping
    for special shell characters. The escaped string is safe for inclusion in
    compgen -W "..." word lists.

    TODO: Implement the following escaping rules:
    1. Wrap in single quotes (safest for most characters)
    2. Escape embedded single quotes using '\'' pattern (close quote, escaped quote, open quote)
    3. Backslash-escape: $ ` \\ (even within single quotes for safety)
    4. Handle empty strings and whitespace-only strings

    Example transformations:
    - "hello" → "hello"
    - "don't" → "don'\''t"
    - "with space" → "with\\ space" or "'with space'"
    - "with$var" → "'with\\$var'"

    Parameters
    ----------
    choice : str
        Raw choice value (should already be cleaned via clean_choice_text).

    Returns
    -------
    str
        Escaped choice value safe for bash completion compgen -W lists.
    """
    raise NotImplementedError("Bash choice escaping not yet implemented")


def _escape_bash_description(text: str) -> str:
    r"""Escape special characters in description text for bash comments.

    NOTE: Bash completion does NOT natively support inline descriptions like zsh.
    This function is provided for potential future use in comments or alternative
    completion methods, but descriptions will NOT be shown to users during completion.

    For now, this function can return the text escaped for use in bash comments (after #).

    TODO: Implement comment-safe escaping:
    1. Remove or escape newlines (use \n or convert to space)
    2. Escape any characters that could break comments
    3. May simply return clean text since it's only used in comments

    Alternative future approach: Could implement custom completion display using
    compopt -o nosort with formatted strings, but this requires bash 4.4+ and
    is not portable to macOS default bash 3.2.

    Parameters
    ----------
    text : str
        Cleaned description text (should already be cleaned via clean_description_text).

    Returns
    -------
    str
        Text safe for bash script comments. Currently not used in completion output.
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
