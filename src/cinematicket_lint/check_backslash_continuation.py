"""Doc rule 2.2: never use backslash line continuation.

Ruff's E502 only flags a *redundant* backslash inside an already-open
bracket. A bare backslash continuation outside any bracket (e.g.
``total = 1 + \\`` or ``if a and \\``) is not covered by any ruff or
pylint check, so this fills that gap.
"""

import tokenize
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT01'


def check(path: Path) -> list[Violation]:
    source_lines = path.read_text(encoding='utf-8').splitlines()
    string_line_spans = _multiline_string_spans(path)
    bracket_depth_by_line = _bracket_depth_by_line(path)

    violations: list[Violation] = []
    for line_number, raw_line in enumerate(source_lines, start=1):
        stripped = raw_line.rstrip()
        if not stripped.endswith('\\'):
            continue
        if _inside_multiline_string(line_number, string_line_spans):
            continue
        if bracket_depth_by_line.get(line_number, 0) > 0:
            continue
        violations.append(
            Violation(
                path=str(path),
                line=line_number,
                code=CODE,
                message='backslash line continuation is not allowed, use parentheses instead',
            )
        )
    return violations


def _multiline_string_spans(path: Path) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    with path.open('rb') as source_file:
        for token in tokenize.tokenize(source_file.readline):
            if token.type == tokenize.STRING and token.start[0] != token.end[0]:
                spans.append((token.start[0], token.end[0]))
    return spans


def _inside_multiline_string(line_number: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= line_number <= end for start, end in spans)


def _bracket_depth_by_line(path: Path) -> dict[int, int]:
    depth = 0
    depth_by_line: dict[int, int] = {}
    with path.open('rb') as source_file:
        for token in tokenize.tokenize(source_file.readline):
            if token.type == tokenize.OP and token.string in '([{':
                depth += 1
            elif token.type == tokenize.OP and token.string in ')]}':
                depth -= 1
            depth_by_line[token.start[0]] = depth
    return depth_by_line
