"""Disallowed placeholder names (foo, bar, ...) for variables, parameters, functions and classes."""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.violations import Violation

CODE = 'CT11'
CONFIG_KEY = 'bad_names'
DEFAULTS: dict = {'names': ['foo', 'bar', 'baz', 'toto', 'tutu', 'tata']}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    bad_names = set(resolve_options(DEFAULTS, options)['names'])
    violations: list[Violation] = []
    for node in ast.walk(tree):
        for name, line in _declared_names(node):
            if name in bad_names:
                violations.append(
                    Violation(path=str(path), line=line, code=CODE, message=f"name '{name}' is not allowed")
                )
    return violations


def _declared_names(node: ast.AST) -> list[tuple[str, int]]:
    """"""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return [(node.id, node.lineno)]
    if isinstance(node, ast.arg):
        return [(node.arg, node.lineno)]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [(node.name, node.lineno)]
    if isinstance(node, ast.ExceptHandler) and node.name:
        return [(node.name, node.lineno)]
    return []
