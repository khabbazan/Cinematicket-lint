"""Suppression handling for custom_lint violations.

A violation is suppressed by a trailing ``# ctlint: CTXX`` comment on
its own line, or file-wide by a ``# ctlint: CTXX`` comment on the
file's first line. Multiple codes may be comma-separated.
"""

import re
import tokenize
from pathlib import Path

from cinematicket_lint.violations import Violation

_DIRECTIVE_PATTERN = re.compile(r'ctlint:\s*(CT\d+(?:\s*,\s*CT\d+)*)')
_CODE_PATTERN = re.compile(r'CT\d+')


def filter_suppressed(path: Path, violations: list[Violation]) -> list[Violation]:
    if not violations:
        return violations
    file_wide_codes, line_codes = _collect_suppression_codes(path)
    return [
        violation
        for violation in violations
        if violation.code not in file_wide_codes and violation.code not in line_codes.get(violation.line, set())
    ]


def _collect_suppression_codes(path: Path) -> tuple[set[str], dict[int, set[str]]]:
    line_codes: dict[int, set[str]] = {}
    with path.open('rb') as source_file:
        for token in tokenize.tokenize(source_file.readline):
            if token.type != tokenize.COMMENT:
                continue
            directive_match = _DIRECTIVE_PATTERN.search(token.string)
            if directive_match is None:
                continue
            codes = set(_CODE_PATTERN.findall(directive_match.group(1)))
            line_codes.setdefault(token.start[0], set()).update(codes)
    file_wide_codes = line_codes.get(1, set())
    return file_wide_codes, line_codes
