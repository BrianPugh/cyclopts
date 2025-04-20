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

        # Set up COMP variables to simulate bash completion environment
        command_parts = partial_command.split()

        # Build the command to source the script and test completion
        cmd = dedent(f"""\
        source {script_path}
        COMP_WORDS=({app.name[0]} {partial_command})
        COMP_CWORD={len(command_parts)}
        COMP_LINE="{app.name[0]} {partial_command}"
        COMP_POINT={len(f"{app.name[0]} {partial_command}")}
        _shtab_main  # Call the actual completion function
        echo "${{COMPREPLY[*]}}"  # Print the completion results
        """)

        result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

        result.check_returncode()

        stdout = result.stdout.strip()
        if not stdout:
            stderr = result.stderr.strip()
            print(stderr)
            raise ValueError
        options = set(stdout.split(" "))
        return options

    return inner


def test_completion_literal_choices(app, bash_completion_tester):
    @app.default
    def main(color: Literal["red", "green"]):
        pass

    assert {"red"} == bash_completion_tester(app, "r")
    assert {"green"} == bash_completion_tester(app, "g")
    assert {"--color"} == bash_completion_tester(app, "--c")
    assert {"red"} == bash_completion_tester(app, "--color r")
    assert {"green"} == bash_completion_tester(app, "--color g")
