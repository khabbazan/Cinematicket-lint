"""Tests for CT17: module too long."""

import ast
from pathlib import Path

from cinematicket_lint import check_module_line_count


def _check(tmp_path: Path, line_count: int, options: dict | None = None) -> list[tuple[int, str]]:
    """"""
    path = tmp_path / 'module.py'
    path.write_text('x = 1\n' * line_count, encoding='utf-8')
    violations = check_module_line_count.check(path, ast.parse(path.read_text()), options)
    return [(violation.line, violation.code) for violation in violations]


def test_flags_a_module_above_the_default_maximum(tmp_path):
    """"""
    assert _check(tmp_path, 1001) == [(1, 'CT17')]


def test_exempts_a_module_at_the_default_maximum(tmp_path):
    """"""
    assert _check(tmp_path, 1000) == []


def test_honours_a_custom_maximum(tmp_path):
    """"""
    assert _check(tmp_path, 11, {'max': 10}) == [(1, 'CT17')]
    assert _check(tmp_path, 10, {'max': 10}) == []


def test_reports_the_line_count_in_the_message(tmp_path):
    """"""
    path = tmp_path / 'module.py'
    path.write_text('x = 1\n' * 12, encoding='utf-8')
    violations = check_module_line_count.check(path, ast.parse(path.read_text()), {'max': 10})
    assert '12' in violations[0].message
    assert '10' in violations[0].message
