"""Tests for CT07: test function naming check."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_test_prefix


def _check(source: str, path: str = 'test_something.py') -> list[str]:
    tree = ast.parse(textwrap.dedent(source))
    violations = check_test_prefix.check(Path(path), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_accepts_bare_test_success():
    assert _check('def test_success():\n    """"""\n') == []


def test_accepts_bare_test_failure():
    assert _check('def test_failure():\n    """"""\n') == []


def test_accepts_test_success_with_suffix():
    assert _check('def test_success_with_pagination():\n    """"""\n') == []


def test_accepts_test_failure_with_suffix():
    assert _check('def test_failure_when_not_found():\n    """"""\n') == []


def test_flags_a_bad_test_name():
    assert _check('def test_something_else():\n    """"""\n') == ['test_something_else']


def test_only_checks_files_named_test_star():
    flagged = _check('def test_something_else():\n    """"""\n', path='pytest_something.py')
    assert flagged == []
