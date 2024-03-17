"""Test cases for the vectorgrep module."""

import argparse
import builtins
import io
import os
import shlex
import sys
from typing import Any
from typing import Callable

import pytest

from vectorgrep import multiscanner
from vectorgrep import utils


def _basic_callback(matches: list, count: int) -> None:
    """Callback for C library to send results."""
    for index in range(count):
        match = matches[index]
        line = match.line.decode(errors="ignore")
        print(f"{match.line_number}:{line.rstrip()}")


TEST_ROOT = os.path.dirname(__file__)
GREP_FILE_1 = os.path.join(TEST_ROOT, "greptest1.txt")
GREP_FILE_2 = os.path.join(TEST_ROOT, "greptest2.txt")
FAKE_FILES = {
    "regex.txt": "filepattern1\nfilepattern2",
}
TEST_FILE = os.path.join(TEST_ROOT, "samplefile.txt")
TEST_FILE_GZ = os.path.join(TEST_ROOT, f"{TEST_FILE}.gz")
TEST_FILE_ZST = os.path.join(TEST_ROOT, f"{TEST_FILE}.zst")
TEST_CASES = {
    "argparse_namespace_comparator": {
        "matched": {
            "args": [
                argparse.Namespace(
                    files=["f1", "f2", "f3"],
                    pattern="p1",
                ),
                argparse.Namespace(
                    files=["f1", "f2", "f3"],
                    pattern="p1",
                ),
            ],
            "returns": None,
        },
        "mismatched": {
            "args": [
                argparse.Namespace(
                    files=["f1", "f2", "f3"],
                    pattern="p1",
                ),
                argparse.Namespace(
                    files=["f1", "f2"],
                    pattern="p2",
                ),
            ],
            "raises": AssertionError,
        },
    },
    "check_vectorscan_compatibility": {
        "PCRE and Vectorscan compatible": {
            "args": [["foobar"]],
            "returns": 0,
        },
        "PCRE compatible but Vectorscan incompatible": {
            # Negative lookbehind example taken from: unit/hyperscan/bad_patterns.cpp
            "args": [["(?<!foo)bar"]],
            "returns": 4,
        },
    },
    "get_argparse_files": {
        "leading pattern positional and file positionals": {
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 file1 file2 file3")),
            ],
            "returns": ["file1", "file2", "file3"],
        },
        "Leading pattern positional and pattern optional": {
            # See multiscanner.get_argparse_files for explanation of why pattern1 is considered a file in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -e pattern2 file1")),
            ],
            "returns": ["pattern1", "file1"],
        },
        "Leading pattern positional and pattern file optional": {
            # See multiscanner.get_argparse_files for explanation of why pattern1 is considered a file in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -f regex.txt file1")),
            ],
            "returns": ["pattern1", "file1"],
        },
        "Leading pattern positional, pattern optional, and pattern file optional": {
            # See multiscanner.get_argparse_files for explanation of why pattern1 is considered a file in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -e pattern2 -f regex.txt file1")),
            ],
            "returns": ["pattern1", "file1"],
        },
        "intermixed pattern positional, trailing file positionals, and pattern optionals": {
            # See multiscanner.get_argparse_files for explanation of why pattern1 is considered a file in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("-e pattern2 pattern1 -e pattern3 file1 file2")),
            ],
            "returns": ["pattern1", "file1", "file2"],
        },
        "pattern positional, intermixed file positionals, and pattern optionals": {
            # See multiscanner.get_argparse_files for explanation of why pattern1 is considered a file in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 file1 -e pattern2 file2 -e pattern3 file3 f4")),
            ],
            "returns": ["pattern1", "file1", "file2", "file3", "f4"],
        },
    },
    "get_argparse_patterns": {
        "leading pattern positional and file positionals": {
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 file1 file2 file3")),
            ],
            "returns": ["pattern1"],
        },
        "Leading pattern positional and pattern optional": {
            # See multiscanner.get_argparse_patterns for explanation of why pattern1 is not considered a pattern in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -e pattern2 file1")),
            ],
            "returns": ["pattern2"],
        },
        "Leading pattern positional and pattern file optional": {
            # See multiscanner.get_argparse_patterns for explanation of why pattern1 is not considered a pattern in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -f regex.txt file1")),
            ],
            "returns": ["filepattern1", "filepattern2"],
        },
        "Leading pattern positional, pattern optional, and pattern file optional": {
            # See multiscanner.get_argparse_patterns for explanation of why pattern1 is not considered a pattern in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 -e pattern2 -f regex.txt file1")),
            ],
            "returns": ["pattern2", "filepattern1", "filepattern2"],
        },
        "intermixed pattern positional, trailing file positionals, and pattern optionals": {
            # See multiscanner.get_argparse_patterns for explanation of why pattern1 is not considered a pattern in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("-e pattern2 pattern1 -e pattern3 file1 file2")),
            ],
            "returns": ["pattern2", "pattern3"],
        },
        "pattern positional, intermixed file positionals, and pattern optionals": {
            # See multiscanner.get_argparse_patterns for explanation of why pattern1 is not considered a pattern in this scenario.
            "args": [
                multiscanner.parse_args(shlex.split("pattern1 file1 -e pattern2 file2 -e pattern3 file3 f4")),
            ],
            "returns": ["pattern2", "pattern3"],
        },
    },
    "scan": {
        "one pattern": {
            "args": [
                TEST_FILE,
                ["bar"],
                _basic_callback,
            ],
            "returns": [
                "1:foobar",
                "2:barfoo",
            ],
        },
        "one pattern, gz": {
            "args": [
                TEST_FILE_GZ,
                ["bar"],
                _basic_callback,
            ],
            "returns": [
                "1:foobar",
                "2:barfoo",
            ],
        },
        "one pattern, zst": {
            "args": [
                TEST_FILE_ZST,
                ["bar"],
                _basic_callback,
            ],
            "returns": [
                "1:foobar",
                "2:barfoo",
            ],
        },
        "two patterns": {
            "args": [
                TEST_FILE,
                [
                    "bar",
                    "food",
                ],
                _basic_callback,
            ],
            "returns": [
                "1:foobar",
                "2:barfoo",
                "3:food",
            ],
        },
    },
    "grep": {
        "one pattern, no index": {
            "args": [
                TEST_FILE,
                ["bar"],
            ],
            "returns": (
                [
                    (2, "foobar\n"),
                    (3, "barfoo\n"),
                ],
                0,
            ),
        },
        "one pattern, no index, gz": {
            "args": [
                TEST_FILE_GZ,
                ["bar"],
            ],
            "returns": (
                [
                    (2, "foobar\n"),
                    (3, "barfoo\n"),
                ],
                0,
            ),
        },
        "one pattern, no index, zst": {
            "args": [
                TEST_FILE_ZST,
                ["bar"],
            ],
            "returns": (
                [
                    (2, "foobar\n"),
                    (3, "barfoo\n"),
                ],
                0,
            ),
        },
        "invalid file": {
            "args": [
                TEST_FILE_ZST + "a",
                ["bar"],
            ],
            "raises": FileNotFoundError,
        },
        "invalid file, no messages": {
            "args": [
                TEST_FILE_ZST + "a",
                ["bar"],
            ],
            "kwargs": {
                "no_messages": True,
            },
            "returns": (
                [],
                101,
            ),
        },
        "invalid file, is directory": {
            "args": [
                os.path.dirname(TEST_FILE_ZST),
                ["bar"],
            ],
            "raises": ValueError,
        },
        "invalid file, is directory, no messages": {
            "args": [
                os.path.dirname(TEST_FILE_ZST),
                ["bar"],
            ],
            "kwargs": {
                "no_messages": True,
            },
            "returns": (
                [],
                101,
            ),
        },
    },
    "parallel_grep": {
        "single file, with file name": {
            "args": [
                [GREP_FILE_1],
                ["foobar"],
            ],
            "kwargs": {
                "with_file_name": True,
            },
            "returns": (
                [
                    "greptest1.txt:foobar",
                ],
                0,
            ),
        },
        "single file, with file name and line index": {
            "args": [
                [GREP_FILE_1],
                ["foobar"],
            ],
            "kwargs": {
                "with_file_name": True,
                "with_line_number": True,
            },
            "returns": (
                [
                    "greptest1.txt:3:foobar",
                ],
                0,
            ),
        },
        "single file, with file name and count": {
            "args": [
                [GREP_FILE_1],
                ["foo"],
            ],
            "kwargs": {
                "count_results": True,
                "with_file_name": True,
            },
            "returns": (
                [
                    "greptest1.txt:16",
                ],
                0,
            ),
        },
        "single file, with file name and total": {
            "args": [
                [GREP_FILE_1],
                ["foo"],
            ],
            "kwargs": {
                "total_results": True,
                "with_file_name": True,
            },
            "returns": (
                [
                    # It is expected for total to not show a file name, it is a total. This ensures expected behavior.
                    "16",
                ],
                0,
            ),
        },
        "single file, no file name, with line index": {
            "args": [
                [GREP_FILE_1],
                ["foobar"],
            ],
            "kwargs": {
                "with_line_number": True,
            },
            "returns": (
                [
                    "3:foobar",
                ],
                0,
            ),
        },
        "single file, no file name, with count": {
            "args": [
                [GREP_FILE_1],
                ["foo"],
            ],
            "kwargs": {
                "count_results": True,
            },
            "returns": (
                [
                    "16",
                ],
                0,
            ),
        },
        "single file, no file name, with total": {
            "args": [
                [GREP_FILE_1],
                ["foo"],
            ],
            "kwargs": {
                "total_results": True,
            },
            "returns": (
                [
                    "16",
                ],
                0,
            ),
        },
        "single file, stop on non-zero match count": {
            "args": [
                [GREP_FILE_1],
                ["foo"],
            ],
            "kwargs": {
                "max_match_count": 3,
            },
            "returns": (
                [
                    "foo",
                    "foobar",
                    "[foo]",
                ],
                0,
            ),
        },
        "multi file, with file name": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foobar"],
            ],
            "kwargs": {
                "with_file_name": True,
            },
            "returns": (
                [
                    "greptest1.txt:foobar",
                    "greptest2.txt:foobar",
                ],
                0,
            ),
        },
        "multi file, with file name and line index": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foobar"],
            ],
            "kwargs": {
                "with_file_name": True,
                "with_line_number": True,
            },
            "returns": (
                [
                    "greptest1.txt:3:foobar",
                    "greptest2.txt:3:foobar",
                ],
                0,
            ),
        },
        "multi file, with file name and count": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foo"],
            ],
            "kwargs": {
                "count_results": True,
                "with_file_name": True,
            },
            "returns": (
                [
                    "greptest1.txt:16",
                    "greptest2.txt:16",
                ],
                0,
            ),
        },
        "multi file, with file name and total": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foo"],
            ],
            "kwargs": {
                "total_results": True,
                "with_file_name": True,
            },
            "returns": (
                [
                    # It is expected for total to not show a file name, it is a total. This ensures expected behavior.
                    "32",
                ],
                0,
            ),
        },
        "multi file, no file name, with line index": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foobar"],
            ],
            "kwargs": {
                "with_line_number": True,
            },
            "returns": (
                [
                    "3:foobar",
                    "3:foobar",
                ],
                0,
            ),
        },
        "multi file, no file name, with count": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foo"],
            ],
            "kwargs": {
                "count_results": True,
            },
            "returns": (
                [
                    "16",
                    "16",
                ],
                0,
            ),
        },
        "multi file, no file name, with total": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foo"],
            ],
            "kwargs": {
                "total_results": True,
            },
            "returns": (
                [
                    "32",
                ],
                0,
            ),
        },
        "multi file, stop on non-zero match count": {
            "args": [
                [GREP_FILE_1, GREP_FILE_2],
                ["foo"],
            ],
            "kwargs": {
                "with_file_name": True,
                "with_line_number": True,
                "max_match_count": 2,
            },
            "returns": (
                [
                    "greptest1.txt:2:foo",
                    "greptest1.txt:3:foobar",
                    "greptest2.txt:2:foo",
                    "greptest2.txt:3:foobar",
                ],
                0,
            ),
        },
        "case sensitive": {
            "args": [
                [GREP_FILE_1],
                ["fOoBaR"],
            ],
            "returns": (
                [
                    # No match expected.
                ],
                1,
            ),
        },
        "case insensitive": {
            "args": [
                [GREP_FILE_1],
                ["fOoBaR"],
            ],
            "kwargs": {"ignore_case": True},
            "returns": (
                [
                    "foobar",
                ],
                0,
            ),
        },
        "special character exact": {
            "args": [
                [GREP_FILE_1],
                ["barfoo\\+"],
            ],
            "returns": (
                [
                    "barfoo+",
                ],
                0,
            ),
        },
        "special character regex": {
            "args": [
                [GREP_FILE_1],
                ["barfoo+"],
            ],
            "returns": (
                [
                    "barfoo",
                    "barfoo+",
                ],
                0,
            ),
        },
        "only matching with single level groups": {
            "args": [
                [GREP_FILE_1],
                ["grep file to test|sync with"],
            ],
            "kwargs": {"only_matching": True},
            "returns": (
                [
                    "grep file to test",
                    "sync with",
                    "grep file to test",
                    "sync with",
                ],
                0,
            ),
        },
        "only matching with redundant inner nested level group": {
            "args": [
                [GREP_FILE_1],
                ["grep file (to|to test)|sync with"],
            ],
            "kwargs": {"only_matching": True},
            "returns": (
                [
                    "grep file to",
                    "sync with",
                    "grep file to",
                    "sync with",
                ],
                0,
            ),
        },
        "only matching pattern without only matching enabled": {
            "args": [
                [GREP_FILE_1],
                ["grep file to test|sync with"],
            ],
            "returns": (
                [
                    "# Primary grep file to test patterns. Keep in sync with greptest2.txt.",
                    "# Primary grep file to test patterns. Keep in sync with greptest2.txt.",
                ],
                0,
            ),
        },
        "multiple unique patterns": {
            "args": [
                [GREP_FILE_1],
                [
                    "foobar",
                    "extra foo bar",
                ],
            ],
            "kwargs": {
                "with_file_name": True,
                "with_line_number": True,
            },
            "returns": (
                [
                    "greptest1.txt:3:foobar",
                    "greptest1.txt:16:extra foo bar",
                ],
                0,
            ),
        },
        "Multiple redundant patterns": {
            "args": [
                [GREP_FILE_1],
                [
                    "foobar",
                    "fo{2}bar",
                    "fo+bar",
                ],
            ],
            "kwargs": {
                "with_file_name": True,
                "with_line_number": True,
            },
            "returns": (
                [
                    "greptest1.txt:3:foobar",
                ],
                0,
            ),
        },
        "match and error": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_1 + "a",
                ],
                ["foobar"],
            ],
            "returns": (
                [
                    "foobar",
                    "vectorgrep: greptest1.txta: No such file or directory",
                ],
                2,
            ),
        },
        "match and error, no messages": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_1 + "a",
                ],
                ["foobar"],
            ],
            "kwargs": {
                "no_messages": True,
            },
            "returns": (
                [
                    "foobar",
                ],
                2,
            ),
        },
        "no match and error": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_1 + "a",
                ],
                ["foobarasdf"],
            ],
            "returns": (
                [
                    "vectorgrep: greptest1.txta: No such file or directory",
                ],
                2,
            ),
        },
        "no match and error, no messages": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_1 + "a",
                ],
                ["foobarasdf"],
            ],
            "kwargs": {
                "no_messages": True,
            },
            "returns": (
                [],
                2,
            ),
        },
        "match, quiet": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_2,
                ],
                ["foobar"],
            ],
            "kwargs": {
                "quiet": True,
            },
            "returns": (
                [],
                0,
            ),
        },
        "no match, quiet": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_2,
                ],
                ["foobarasdf"],
            ],
            "kwargs": {
                "quiet": True,
            },
            "returns": (
                [],
                1,
            ),
        },
        "match and error, quiet": {
            "args": [
                [
                    GREP_FILE_1,
                    GREP_FILE_2 + "a",
                ],
                ["foobarasdf"],
            ],
            "kwargs": {
                "quiet": True,
            },
            "returns": (
                ["vectorgrep: greptest2.txta: No such file or directory"],
                2,
            ),
        },
    },
    "parse_args": {
        "leading pattern positional and file positionals": {
            "args": [
                shlex.split("p1 f1 f2 f3"),
            ],
            "attributes": {
                "files": ["f1", "f2", "f3"],
                "pattern": "p1",
            },
        },
        "intermixed pattern positional, trailing file positionals, and pattern optionals": {
            "args": [
                shlex.split("-e p2 p1 -e p3 f1 f2"),
            ],
            "attributes": {
                "files": ["f1", "f2"],
                "pattern": "p1",
                "patterns": ["p2", "p3"],
            },
        },
        "pattern positional, intermixed file positionals, and pattern optionals": {
            "args": [
                shlex.split("p1 f1 -e p2 f2 -e p3 f3 f4"),
            ],
            "attributes": {
                "files": ["f1", "f2", "f3", "f4"],
                "pattern": "p1",
                "patterns": ["p2", "p3"],
            },
        },
    },
    "to_basic_regular_expressions": {
        "no changes, no special characters": {
            "args": [
                ["test"],
            ],
            "returns": ["test"],
        },
        "no changes, BRE compatible special characters": {
            "args": [
                ["^test.*[test]$"],
            ],
            "returns": ["^test.*[test]$"],
        },
        "BRE and PCRE special characters": {
            "args": [
                ["^test.*[test]+?(){}|$"],
            ],
            "returns": [r"^test.*[test]\+\?\(\)\{\}\|$"],
        },
        "BRE, PCRE, and escaped special characters": {
            "args": [
                [r"^test.*[test]+?(){}|\^\$\*\.\[\]\+\?\(\)\{\}\|$"],
            ],
            "returns": [r"^test.*[test]\+\?\(\)\{\}\|\^\$\*\.\[\]+?(){}|$"],
        },
        "Valid as PCRE, but not valid as BRE": {
            "args": [
                [r"data \((?P<v0>.*?) (?P<v1>.*?)"],
            ],
            "raises": ValueError,
        },
    },
    "to_gnu_regular_expressions": {
        "no changes, no escapes": {
            "args": [
                ["<foo>"],
            ],
            "returns": ["<foo>"],
        },
        "GNU word boundaries swapped": {
            "args": [
                [r"<foo>\<foo\>"],
            ],
            "returns": [r"<foo>\bfoo\b"],
        },
        "GNU word boundaries swapped, escaped boundaries skipped": {
            "args": [
                [r"<foo>\<foo\>\\<foo\\>"],
            ],
            "returns": [r"<foo>\bfoo\b\\<foo\\>"],
        },
    },
}


@pytest.fixture(autouse=True)
def no_file_load(request: pytest.FixtureRequest, monkeypatch: Any) -> None:
    """Prevent tests from loading external files, and instead mock the lines."""
    disable = False
    if "no_file_load" in request.keywords:
        disable = request.node.get_closest_marker("no_file_load").kwargs.get("disable", False)

    if not disable:

        def mock_opener(file: str, *args: Any, **kwargs: Any) -> io.StringIO:
            return io.StringIO(FAKE_FILES.get(file, ""))

        monkeypatch.setattr(builtins, "open", mock_opener)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["check_vectorscan_compatibility"])
def test_check_vectorscan_compatibility(test_case: dict, function_tester: Callable) -> None:
    """Unit tests for verifying Vectorscan pattern compatibility."""
    function_tester(test_case, utils.check_compatibility)


@pytest.mark.no_file_load(disable=True)
def test_greptest_file_sync() -> None:
    """Verify the "greptest" files are kept in sync."""
    with open(GREP_FILE_1, encoding="utf-8") as file_in:
        file1_contents = file_in.readlines()
        file1_contents = [line for line in file1_contents if not line.startswith("#")]
    assert file1_contents, f"Failed to read test file: {GREP_FILE_1}"

    with open(GREP_FILE_2, encoding="utf-8") as file_in:
        file2_contents = file_in.readlines()
        file2_contents = [line for line in file2_contents if not line.startswith("#")]
    assert file2_contents, f"Failed to read test file: {GREP_FILE_2}"

    assert (
        file1_contents == file2_contents
    ), f"{GREP_FILE_1} contents differ from {GREP_FILE_2}. Please ensure all content lines match."


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["get_argparse_files"])
def test_get_argparse_files(test_case: dict, function_tester: Callable) -> None:
    """Tests for get_argparse_files function."""
    function_tester(test_case, multiscanner.get_argparse_files)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["get_argparse_patterns"])
def test_get_argparse_patterns(test_case: dict, function_tester: Callable) -> None:
    """Tests for get_argparse_patterns function."""
    function_tester(test_case, multiscanner.get_argparse_patterns)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["grep"])
@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Vectorscan libraries only support Linux",
)
def test_grep(test_case: dict, function_tester: Callable) -> None:
    """Tests for grep function."""
    function_tester(test_case, utils.grep)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["parallel_grep"])
@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Vectorscan libraries only support Linux",
)
def test_parallel_grep(test_case: dict, capsys: Any, function_tester: Callable) -> None:
    """Tests for parallel_grep function."""

    def parallel_grep_helper(*args: Any, **kwargs: Any) -> tuple[list[str], int]:
        """Helper to run parallel_grep and capture output for comparisons."""
        return_code = multiscanner.parallel_grep(*args, **kwargs)
        capture = capsys.readouterr()
        stdout = capture.out.splitlines()
        # Strip off the leading file name in output to keep the tests portable across systems.
        cleaned = [line.replace(f"{TEST_ROOT}/", "") for line in stdout]
        return cleaned, return_code

    function_tester(test_case, parallel_grep_helper)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["parse_args"])
def test_parse_args(test_case: dict, function_tester: Callable) -> None:
    """Tests for parse_args function."""
    function_tester(test_case, multiscanner.parse_args)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["to_basic_regular_expressions"])
def test_to_basic_regular_expressions(test_case: dict, function_tester: Callable) -> None:
    """Tests for to_basic_regular_expressions function."""
    function_tester(test_case, multiscanner.to_basic_regular_expressions)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["to_gnu_regular_expressions"])
def test_to_gnu_regular_expressions(test_case: dict, function_tester: Callable) -> None:
    """Tests for to_gnu_regular_expressions function."""
    function_tester(test_case, multiscanner.to_gnu_regular_expressions)


@pytest.mark.parametrize_test_case("test_case", TEST_CASES["scan"])
@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Vectorscan libraries only support Linux",
)
def test_vectorscan(test_case: dict, capsys: Any, function_tester: Callable) -> None:
    """Tests for vectorscan function."""

    def _scan_helper(*args: Any, **kwargs: Any) -> list:
        """Helper to run vectorscan and capture output for comparisons."""
        utils.scan(*args, **kwargs)
        capture = capsys.readouterr()
        stdout = capture.out.splitlines()
        return stdout

    function_tester(test_case, _scan_helper)
