"""Result mode handling for CLI applications.

This module defines how command return values are processed when used in CLI contexts,
particularly when installed via console_scripts entry points.
"""

import sys
from typing import Any, Literal

ResultMode = Literal[
    "return_value",
    "print_non_int_return_exit_code",
    "print_str_return_exit_code",
    "print_str_return_zero",
    "print_non_none_return_exit_code",
    "print_non_none_return_zero",
    "return_exit_code",
    "print_non_int_call_sys_exit",
    "return_bool_as_exit_code",
]


def _handle_result_mode(result: Any, mode: str) -> Any:
    """Handle command result based on result_mode.

    Parameters
    ----------
    result : Any
        The command's return value.
    mode : str
        The result_mode to apply.

    Returns
    -------
    Any
        Processed result based on mode (may call sys.exit() and not return).
    """
    match mode:
        case "return_value":
            return result
        case "print_non_int_return_exit_code":
            if isinstance(result, int):
                return result
            elif result is not None:
                print(result)
                return 0
            else:
                return 0
        case "print_str_return_exit_code":
            if isinstance(result, str):
                print(result)
                return 0
            elif isinstance(result, int):
                return result
            else:
                return 0
        case "print_str_return_zero":
            if isinstance(result, str):
                print(result)
            return 0
        case "print_non_none_return_exit_code":
            if result is not None:
                print(result)
            if isinstance(result, int):
                return result
            return 0
        case "print_non_none_return_zero":
            if result is not None:
                print(result)
            return 0
        case "return_exit_code":
            if isinstance(result, int):
                return result
            else:
                return 0
        case "print_non_int_call_sys_exit":
            if isinstance(result, int):
                sys.exit(result)
            elif result is not None:
                print(result)
                sys.exit(0)
            else:
                sys.exit(0)
        case "return_bool_as_exit_code":
            if isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            elif result is None:
                return 0
            else:
                print(result)
                return 0
        case _:
            return result
