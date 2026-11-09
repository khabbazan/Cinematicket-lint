"""Tests for the shared Violation type."""

from cinematicket_lint.violations import Violation


def test_violation_renders_as_path_line_code_and_message():
    """"""
    violation = Violation(path='app/file.py', line=12, code='CT01', message='bad thing')
    assert str(violation) == 'app/file.py:12: CT01 bad thing'


def test_violations_with_equal_fields_are_equal():
    """"""
    first = Violation(path='a.py', line=1, code='CT01', message='m')
    second = Violation(path='a.py', line=1, code='CT01', message='m')
    assert first == second
