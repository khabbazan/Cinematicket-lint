"""Suppression handling for custom_lint violations.

A violation is suppressed by a trailing ``# CTXX`` comment on its own
line, or file-wide by a ``# CTXX`` comment on the file's first line.
"""

import re
import tokenize
from pathlib import Path

from cinematicket_linter.violations import Violation

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
            codes = set(_CODE_PATTERN.findall(token.string))
            if codes:
                line_codes.setdefault(token.start[0], set()).update(codes)
    file_wide_codes = line_codes.get(1, set())
    return file_wide_codes, line_codes
