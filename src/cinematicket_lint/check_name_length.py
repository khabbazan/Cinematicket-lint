"""Naming pattern for local variables and parameters (rejects single-character names by default).

Module-level names are covered by CT12. Comprehension variables and attributes are not checked.
"""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.scopes import bound_names, iter_functions, matches, parameters
from cinematicket_lint.violations import Violation

CODE = 'CT10'
CONFIG_KEY = 'name_length'
DEFAULTS: dict = {
    'variable_pattern': '^[a-z_][a-z0-9_]+$',
    'argument_pattern': '^[a-z_][a-z0-9_]+$',
    'good_names': ['ex', 'Run', '_', 'pk'],
}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    settings = resolve_options(DEFAULTS, options)
    violations: list[Violation] = []
    for function in iter_functions(tree):
        for parameter in parameters(function):
            if _is_invalid(parameter.arg, settings['argument_pattern'], settings['good_names']):
                violations.append(
                    _violation(path, parameter.lineno, parameter.arg, 'parameter', settings['argument_pattern'])
                )
        for name, line in bound_names(function).items():
            if _is_invalid(name, settings['variable_pattern'], settings['good_names']):
                violations.append(_violation(path, line, name, 'variable', settings['variable_pattern']))
    return violations


def _is_invalid(name: str, pattern: str, good_names: list[str]) -> bool:
    """"""
    return name not in good_names and not matches(pattern, name)


def _violation(path: Path, line: int, name: str, kind: str, pattern: str) -> Violation:
    """"""
    return Violation(
        path=str(path),
        line=line,
        code=CODE,
        message=f"{kind} name '{name}' does not match the required pattern {pattern}",
    )
