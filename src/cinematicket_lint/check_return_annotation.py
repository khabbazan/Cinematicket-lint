"""Doc rule 3.4: annotate every function/method's return type.

Exempt:
  - test functions named test_success[_...] or test_failure[_...] — the
    test framework, not a caller, uses the return value (or ignores it).
  - dunder methods (__init__, __str__, ...) — their return type is
    dictated by the protocol they implement, not worth spelling out.
"""

import ast
import re
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT09'

_EXEMPT_TEST_NAME = re.compile(r'^test_(success|failure)(_|$)')
_DUNDER_NAME = re.compile(r'^__.+__$')


def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _is_exempt(node.name):
            continue
        if node.returns is not None:
            continue
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code=CODE,
                message=f"function '{node.name}' has no return type annotation",
            )
        )
    return violations


def _is_exempt(name: str) -> bool:
    return bool(_EXEMPT_TEST_NAME.match(name) or _DUNDER_NAME.match(name))
