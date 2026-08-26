"""Doc rule 3.2: annotate variables when not using a class constructor.

Exempt right-hand sides, either of which makes the variable's type
self-evident from syntax alone:
  1. a call whose target name starts with an uppercase letter
     (PascalCase), matching the project's class-naming-style=PascalCase
     convention already enforced by pylint.
  2. a literal data-type initialization: (), [], '', "", {}, a set
     literal, an f-string, or a number/bool/None constant.
"""

import ast
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT02'

_LITERAL_NODE_TYPES = (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.JoinedStr)


def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for function_node in ast.walk(tree):
        if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for statement in function_node.body:
            violation = _check_assignment(path, statement)
            if violation is not None:
                violations.append(violation)
    return violations


def _check_assignment(path: Path, statement: ast.stmt) -> Violation | None:
    if not isinstance(statement, ast.Assign):
        return None
    if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
        return None
    if _is_exempt(statement.value):
        return None
    target_name = statement.targets[0].id
    return Violation(
        path=str(path),
        line=statement.lineno,
        code=CODE,
        message=(
            f"variable '{target_name}' has no type annotation and its value is "
            'neither a class constructor call nor a literal data-type initialization'
        ),
    )


def _is_exempt(value: ast.expr) -> bool:
    return _looks_like_constructor_call(value) or isinstance(value, _LITERAL_NODE_TYPES)


def _looks_like_constructor_call(value: ast.expr) -> bool:
    if not isinstance(value, ast.Call):
        return False
    callee = value.func
    if isinstance(callee, ast.Name):
        return callee.id[:1].isupper()
    if isinstance(callee, ast.Attribute):
        return callee.attr[:1].isupper()
    return False
