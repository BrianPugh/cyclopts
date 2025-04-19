import subprocess
from textwrap import dedent
from typing import Literal

import shtab


class Bash:
    """Modified from shtab.

    https://github.com/iterative/shtab/blob/main/tests/test_shtab.py
    """

    def __init__(self, init_script=""):
        self.init = init_script

    def run(self, cmd):
        """Run a bash command and return stdout, stderr and return code."""
        init = self.init + "\n" if self.init else ""
        full_cmd = f"{init}{cmd}"
        proc = subprocess.Popen(["bash", "-c", full_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()
        return_code = proc.wait()
        return stdout.strip(), stderr.strip(), return_code

    def compgen(self, compgen_cmd, word, expected_completions, failure_message=""):
        """Test bash completion and compare results in Python."""
        # Run compgen command and get actual completions
        cmd = f'compgen {compgen_cmd} -- "{word}"'
        actual_completions, stderr, return_code = self.run(cmd)

        # Debug output
        print(f"\nTesting completion for '{word}':")
        print(f"Command: {cmd}")
        print(f"Actual completions: '{actual_completions}'")
        print(f"Expected completions: '{expected_completions}'")
        print(f"Return code: {return_code}")

        if stderr:
            print(f"Error: {stderr}")

        # Compare in Python
        assert actual_completions == expected_completions, dedent(
            f"""\
                {failure_message}
                Command: {cmd}
                Expected: '{expected_completions}'
                Actual: '{actual_completions}'
                === stderr ===
                {stderr or ""}
                """
        )


def test_completion_literal_choices(app):
    @app.default
    def main(color: Literal["red", "green"]):
        pass

    parser = app._to_argparse()
    completion = shtab.complete(parser, shell="bash")
    shell = Bash(completion)

    stdout, _, _ = shell.run("declare -p | grep _shtab_main_")
    print(f"Available shtab variables:\n{stdout}")
    # Positional
    shell.compgen('-W "${_shtab_main_pos_0_choices[*]}"', "r", "red")
    shell.compgen('-W "${_shtab_main_pos_0_choices[*]}"', "g", "green")

    # Keyword
    shell.compgen('-W "${_shtab_main_option_strings[*]}"', "--c", "--color")

    # Keyword Value
    shell.compgen('-W "${_shtab_main___color_choices[*]}"', "r", "red")
    shell.compgen('-W "${_shtab_main___color_choices[*]}"', "green", "green")
