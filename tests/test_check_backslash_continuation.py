"""Tests for CT01: backslash line continuation outside brackets."""

import textwrap
from pathlib import Path

from cinematicket_lint import check_backslash_continuation


def _check(tmp_path: Path, source: str) -> list[int]:
    """"""
    path = tmp_path / 'module.py'
    path.write_text(textwrap.dedent(source), encoding='utf-8')
    return [violation.line for violation in check_backslash_continuation.check(path)]


def test_flags_a_backslash_continuation_in_an_assignment(tmp_path):
    """"""
    assert _check(tmp_path, 'total = 1 + \\\n    2\n') == [1]


def test_flags_a_backslash_continuation_in_a_condition(tmp_path):
    """"""
    assert _check(tmp_path, 'if first and \\\n        second:\n    pass\n') == [1]


def test_flags_each_continued_line(tmp_path):
    """"""
    assert _check(tmp_path, 'total = 1 + \\\n    2 + \\\n    3\n') == [1, 2]


def test_flags_a_backslash_in_a_with_statement(tmp_path):
    """"""
    assert _check(tmp_path, 'with open("a") as first, \\\n        open("b") as second:\n    pass\n') == [1]


def test_exempts_a_backslash_inside_parentheses(tmp_path):
    """"""
    assert _check(tmp_path, 'total = (1 + \\\n    2)\n') == []


def test_exempts_a_backslash_inside_brackets_and_braces(tmp_path):
    """"""
    assert _check(tmp_path, 'items = [1, \\\n    2]\nmapping = {1: \\\n    2}\n') == []


def test_flags_a_backslash_after_the_brackets_are_closed(tmp_path):
    """"""
    assert _check(tmp_path, 'total = (1) + \\\n    2\n') == [1]


def test_exempts_a_backslash_inside_a_multiline_string(tmp_path):
    """"""
    source = 'text = """first \\\nsecond"""\n'
    assert _check(tmp_path, source) == []


def test_exempts_a_backslash_inside_a_multiline_docstring(tmp_path):
    """"""
    source = 'def foo() -> None:\n    """Doc \\\n    more."""\n'
    assert _check(tmp_path, source) == []


def test_ignores_lines_without_a_trailing_backslash(tmp_path):
    """"""
    assert _check(tmp_path, 'value = "a\\\\b"\nother = 1\n') == []


def test_ignores_an_escaped_backslash_that_ends_a_string_line(tmp_path):
    """"""
    assert _check(tmp_path, 'value = "a\\\\"\n') == []


def test_reports_the_line_number_of_the_backslash(tmp_path):
    """"""
    assert _check(tmp_path, 'first = 1\nsecond = 2\ntotal = 1 + \\\n    2\n') == [3]


def test_returns_nothing_for_an_empty_file(tmp_path):
    """"""
    assert _check(tmp_path, '') == []
