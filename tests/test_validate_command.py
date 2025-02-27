from typing import Tuple, Union

from cyclopts.parameter import validate_command


def test_validate_command():
    def f1():
        pass

    validate_command(f1)

    def f2(a, b, c):
        pass

    validate_command(f2)

    def f3(a: str, b: int, c: list):
        pass

    validate_command(f3)

    def f4(a: Tuple[int, int], b: str):
        pass

    validate_command(f4)

    # Python automatically deduplicates the double None.
    def f5(a: Union[None, None]):
        pass

    validate_command(f5)
