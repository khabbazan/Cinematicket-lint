"""Doc rule 4.5: OpenAPI schema entries need an example and a
description ending with a period.

Scoped to this project's actual drf-yasg usage: openapi.Schema(...) and
openapi.Parameter(...) calls.
"""

import ast
from pathlib import Path

from cinematicket_linter.violations import Violation

CODE_MISSING_EXAMPLE = 'CT04'
CODE_MISSING_DESCRIPTION = 'CT05'
CODE_DESCRIPTION_NO_PERIOD = 'CT06'

_SCHEMA_CALL_NAMES = ('Schema', 'Parameter')


def check(path: Path, tree: ast.Module) -> list[Violation]:
    if not _imports_drf_yasg_openapi(tree):
        return []

    violations: list[Violation] = []
    for call_node in ast.walk(tree):
        if not isinstance(call_node, ast.Call) or not _is_openapi_schema_call(call_node):
            continue
        violations.extend(_check_call(path, call_node))
    return violations


def _imports_drf_yasg_openapi(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'drf_yasg':
            if any(alias.name == 'openapi' for alias in node.names):
                return True
    return False


def _is_openapi_schema_call(call_node: ast.Call) -> bool:
    callee = call_node.func
    if not isinstance(callee, ast.Attribute) or callee.attr not in _SCHEMA_CALL_NAMES:
        return False
    return isinstance(callee.value, ast.Name) and callee.value.id == 'openapi'


def _check_call(path: Path, call_node: ast.Call) -> list[Violation]:
    violations: list[Violation] = []
    description_keyword = _find_keyword(call_node, 'description')
    example_keyword = _find_keyword(call_node, 'example')

    if example_keyword is None:
        violations.append(
            Violation(path=str(path), line=call_node.lineno, code=CODE_MISSING_EXAMPLE, message='missing example=')
        )

    if description_keyword is None:
        violations.append(
            Violation(
                path=str(path), line=call_node.lineno, code=CODE_MISSING_DESCRIPTION, message='missing description='
            )
        )
    elif not _ends_with_period(description_keyword.value):
        violations.append(
            Violation(
                path=str(path),
                line=description_keyword.value.lineno,
                code=CODE_DESCRIPTION_NO_PERIOD,
                message='description must end with a period',
            )
        )
    return violations


def _find_keyword(call_node: ast.Call, name: str) -> ast.keyword | None:
    for keyword in call_node.keywords:
        if keyword.arg == name:
            return keyword
    return None


def _ends_with_period(value_node: ast.expr) -> bool:
    if not isinstance(value_node, ast.Constant) or not isinstance(value_node.value, str):
        return True
    return value_node.value.rstrip().endswith('.')
