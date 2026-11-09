"""Tests for `# ctlint: CTxx` suppression handling."""

import textwrap
from pathlib import Path

from cinematicket_lint.suppressions import filter_suppressed
from cinematicket_lint.violations import Violation


def _filter(tmp_path: Path, source: str, violations: list[Violation]) -> list[tuple[str, int]]:
    """"""
    path = tmp_path / 'module.py'
    path.write_text(textwrap.dedent(source), encoding='utf-8')
    return [(violation.code, violation.line) for violation in filter_suppressed(path, violations)]


def _violation(code: str, line: int) -> Violation:
    """"""
    return Violation(path='module.py', line=line, code=code, message='message')


def test_returns_violations_untouched_when_there_are_none(tmp_path):
    """"""
    assert _filter(tmp_path, 'x = 1\n', []) == []


def test_keeps_a_violation_without_any_directive(tmp_path):
    """"""
    assert _filter(tmp_path, 'x = 1\ny = 2\n', [_violation('CT01', 2)]) == [('CT01', 2)]


def test_a_trailing_directive_suppresses_its_own_line(tmp_path):
    """"""
    source = 'x = 1\ny = 2  # ctlint: CT02\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2)]) == []


def test_a_trailing_directive_does_not_suppress_other_lines(tmp_path):
    """"""
    source = 'w = 0\nx = 1  # ctlint: CT02\ny = 2\n'
    assert _filter(tmp_path, source, [_violation('CT02', 3)]) == [('CT02', 3)]


def test_a_trailing_directive_on_the_first_line_applies_to_the_whole_file(tmp_path):
    """"""
    source = 'x = 1  # ctlint: CT02\ny = 2\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2)]) == []


def test_a_directive_only_suppresses_the_named_code(tmp_path):
    """"""
    source = 'x = 1\ny = 2  # ctlint: CT02\n'
    assert _filter(tmp_path, source, [_violation('CT03', 2)]) == [('CT03', 2)]


def test_a_directive_may_list_several_codes(tmp_path):
    """"""
    source = 'x = 1\ny = 2  # ctlint: CT02, CT08,CT09\n'
    violations = [_violation('CT02', 2), _violation('CT08', 2), _violation('CT09', 2), _violation('CT10', 2)]
    assert _filter(tmp_path, source, violations) == [('CT10', 2)]


def test_a_directive_may_follow_another_comment(tmp_path):
    """"""
    source = 'x = 1\ny = 2  # noqa: E501  # ctlint: CT02\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2)]) == []


def test_a_directive_without_a_space_after_the_colon_works(tmp_path):
    """"""
    source = 'x = 1\ny = 2  # ctlint:CT02\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2)]) == []


def test_a_first_line_directive_suppresses_the_code_for_the_whole_file(tmp_path):
    """"""
    source = '# ctlint: CT02\nx = 1\ny = 2\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2), _violation('CT02', 3)]) == []


def test_a_first_line_directive_keeps_other_codes(tmp_path):
    """"""
    source = '# ctlint: CT02\nx = 1\n'
    assert _filter(tmp_path, source, [_violation('CT03', 2)]) == [('CT03', 2)]


def test_a_first_line_directive_may_list_several_codes(tmp_path):
    """"""
    source = '# ctlint: CT02, CT03\nx = 1\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2), _violation('CT03', 2)]) == []


def test_a_second_line_directive_is_not_file_wide(tmp_path):
    """"""
    source = 'x = 1\n# ctlint: CT02\ny = 2\n'
    assert _filter(tmp_path, source, [_violation('CT02', 3)]) == [('CT02', 3)]


def test_a_directive_inside_a_string_is_ignored(tmp_path):
    """"""
    source = 'x = 1\ny = "# ctlint: CT02"\n'
    assert _filter(tmp_path, source, [_violation('CT02', 2)]) == [('CT02', 2)]


def test_a_directive_inside_a_docstring_is_ignored(tmp_path):
    """"""
    source = 'def foo():\n    """# ctlint: CT02"""\n'
    assert _filter(tmp_path, source, [_violation('CT02', 1)]) == [('CT02', 1)]


def test_suppressions_apply_per_violation_not_per_file_for_line_directives(tmp_path):
    """"""
    source = 'z = 0\na = 1  # ctlint: CT02\nb = 2\nc = 3  # ctlint: CT02\n'
    violations = [_violation('CT02', 2), _violation('CT02', 3), _violation('CT02', 4)]
    assert _filter(tmp_path, source, violations) == [('CT02', 3)]
