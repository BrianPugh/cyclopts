"""Result handling for CLI applications.

This module defines how command return values are processed when used in CLI contexts,
particularly when installed via console_scripts entry points.
"""

import sys
from collections.abc import Callable
from typing import Any, Literal

ResultAction = (
    Literal[
        "return_value",
        "print_non_int_return_int_as_exit_code",
        "print_str_return_int_as_exit_code",
        "print_str_return_zero",
        "print_non_none_return_int_as_exit_code",
        "print_non_none_return_zero",
        "return_int_as_exit_code_else_zero",
        "print_non_int_sys_exit",
    ]
    | Callable[[Any], Any]
)


def handle_result_action(result: Any, action: ResultAction) -> Any:
    """Handle command result based on result_action.

    Parameters
    ----------
    result : Any
        The command's return value.
    action : ResultAction
        The result_action to apply. Can be a predefined literal string or a callable
        that takes the result and returns a processed value.

    Returns
    -------
    Any
        Processed result based on action (may call sys.exit() and not return).
    """
    if callable(action):
        return action(result)

    match action:
        case "return_value":
            return result
        case "print_non_int_return_int_as_exit_code":
            if isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            elif result is not None:
                print(result)
                return 0
            else:
                return 0
        case "print_str_return_int_as_exit_code":
            if isinstance(result, str):
                print(result)
                return 0
            elif isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            else:
                return 0
        case "print_str_return_zero":
            if isinstance(result, str):
                print(result)
            return 0
        case "print_non_none_return_int_as_exit_code":
            if result is not None:
                print(result)
            if isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            return 0
        case "print_non_none_return_zero":
            if result is not None:
                print(result)
            return 0
        case "return_int_as_exit_code_else_zero":
            if isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            else:
                return 0
        case "print_non_int_sys_exit":
            if isinstance(result, bool):
                sys.exit(0 if result else 1)
            elif isinstance(result, int):
                sys.exit(result)
            elif result is not None:
                print(result)
                sys.exit(0)
            else:
                sys.exit(0)
        case _:
            raise ValueError
