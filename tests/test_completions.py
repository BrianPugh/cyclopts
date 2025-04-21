import subprocess
from textwrap import dedent
from typing import Literal

import pytest
import shtab


@pytest.fixture
def bash_completion_tester(tmp_path):
    def inner(app, partial_command):
        script_path = tmp_path / "completion_script"
        parser = app._to_argparse()
        completion = shtab.complete(parser, shell="bash")
        script_path.write_text(completion)

        # Find the function name from the script
        find_func_cmd = f"source {script_path} && complete | grep {app.name[0]} | cut -d' ' -f5"
        func_result = subprocess.run(["bash", "-c", find_func_cmd], capture_output=True, text=True)
        completion_func = func_result.stdout.strip()

        # If we can't find the specific function, try with a default
        if not completion_func:
            completion_func = f"_shtab_{app.name[0]}"

        print(f"{completion_func=}")

        # Set up COMP variables to simulate bash completion environment
        command_parts = partial_command.split()
        comp_cword = len(command_parts)

        # Build the command to source the script and test completion
        cmd = dedent(f"""\
        source {script_path}
        COMP_WORDS=({app.name[0]} {partial_command})
        COMP_CWORD={comp_cword}
        COMP_LINE="{app.name[0]} {partial_command}"
        COMP_POINT={len(f"{app.name[0]} {partial_command}")}
        {completion_func}  # Use the detected function name
        echo "${{COMPREPLY[*]}}"  # Print the completion results
        """)

        result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        result.check_returncode()

        stdout = result.stdout.strip()
        if not stdout:
            stderr = result.stderr.strip()
            raise ValueError(f"No completion results:\n{stderr or 'EMPTY STDERR'}")

        options = set(stdout.split(" "))
        return options

    return inner


def test_completion_subcommands(app, bash_completion_tester):
    @app.default
    def main():
        pass

    @app.command
    def foo(*, fizz: bool):
        pass

    @app.command
    def bar(*, buzz: bool):
        pass

    assert {"foo"} == bash_completion_tester(app, "f")
    assert {"bar"} == bash_completion_tester(app, "b")


def test_completion_literal_choices(app, bash_completion_tester):
    @app.default
    def main(color: Literal["red", "green"]):
        pass

    assert {"red"} == bash_completion_tester(app, "r")
    assert {"green"} == bash_completion_tester(app, "g")
    assert {"--color"} == bash_completion_tester(app, "--c")
    assert {"red"} == bash_completion_tester(app, "--color r")
    assert {"green"} == bash_completion_tester(app, "--color g")
