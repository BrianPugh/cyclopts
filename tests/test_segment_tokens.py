from cyclopts.bind import segment_tokens_by_command


def test_empty_tokens():
    assert segment_tokens_by_command([], []) == [[]]


def test_no_commands():
    assert segment_tokens_by_command(["--flag", "arg"], []) == [["--flag", "arg"]]


def test_command_at_start():
    assert segment_tokens_by_command(["foo", "--flag"], [0]) == [[], ["--flag"]]


def test_command_at_end():
    assert segment_tokens_by_command(["--flag", "foo"], [1]) == [["--flag"], []]


def test_command_in_middle():
    # --verbose foo --debug myname
    tokens = ["--verbose", "foo", "--debug", "myname"]
    assert segment_tokens_by_command(tokens, [1]) == [["--verbose"], ["--debug", "myname"]]


def test_multiple_commands():
    # -v cmd1 --flag1 cmd2 --flag2 arg
    tokens = ["-v", "cmd1", "--flag1", "cmd2", "--flag2", "arg"]
    assert segment_tokens_by_command(tokens, [1, 3]) == [["-v"], ["--flag1"], ["--flag2", "arg"]]


def test_adjacent_commands():
    # cmd1 cmd2 --flag
    tokens = ["cmd1", "cmd2", "--flag"]
    assert segment_tokens_by_command(tokens, [0, 1]) == [[], [], ["--flag"]]


def test_only_command():
    assert segment_tokens_by_command(["foo"], [0]) == [[], []]


def test_three_commands():
    tokens = ["a", "b", "c", "--flag"]
    assert segment_tokens_by_command(tokens, [0, 1, 2]) == [[], [], [], ["--flag"]]


def test_flags_around_command():
    tokens = ["--x", "1", "cmd", "--y", "2"]
    assert segment_tokens_by_command(tokens, [2]) == [["--x", "1"], ["--y", "2"]]
