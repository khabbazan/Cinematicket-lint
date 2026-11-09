"""Module longer than the configured number of lines."""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.violations import Violation

CODE = 'CT17'
CONFIG_KEY = 'module_line_count'
DEFAULTS: dict = {'max': 1000}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    maximum = resolve_options(DEFAULTS, options)['max']
    line_count = len(path.read_text(encoding='utf-8').splitlines())
    if line_count <= maximum:
        return []
    return [Violation(path=str(path), line=1, code=CODE, message=f'module has {line_count} lines (max {maximum})')]
