from typing import Tuple, Union

import pytest

from cyclopts.parameter import validate_command


def test_validate_command(default_function_groups):
    def f1():
        pass

    validate_command(f1, *default_function_groups)

    def f2(a, b, c):
        pass

    validate_command(f2, *default_function_groups)

    def f3(a: str, b: int, c: list):
        pass

    validate_command(f3, *default_function_groups)

    def f4(a: Tuple[int, int], b: str):
        pass

    validate_command(f4, *default_function_groups)

    # Python automatically deduplicates the double None.
    def f5(a: Union[None, None]):
        pass

    validate_command(f5, *default_function_groups)


def test_validate_command_exception_bare_tuple(default_function_groups):
    def f1(a: tuple):
        pass

    with pytest.raises(TypeError):
        validate_command(f1, *default_function_groups)


def test_validate_command_exception_ellipsis_tuple(default_function_groups):
    def f1(a: Tuple[int, ...]):
        pass

    with pytest.raises(ValueError):
        validate_command(f1, *default_function_groups)
