"""Doc rule 5.5: test functions are named test_success[_...] or test_failure[_...]."""

import ast
import re
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT07'

_VALID_TEST_NAME = re.compile(r'^test_(success|failure)(_|$)')


def check(path: Path, tree: ast.Module) -> list[Violation]:
    if not path.name.startswith('test_'):
        return []

    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test_') or _VALID_TEST_NAME.match(node.name):
            continue
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code=CODE,
                message=f"test function '{node.name}' must be named test_success or test_success_..., or test_failure or test_failure_...",
            )
        )
    return violations
