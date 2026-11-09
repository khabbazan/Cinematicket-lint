"""Module-level assignments are constants and must be UPPER_CASE.

Only assignments of constant values (literals and arithmetic over literals) are checked, as pylint does;
set `only_constant_values = false` to check every module-level assignment.

Exempt: dunder names, class aliases / type variables (a PascalCase target bound to a non-literal),
and names listed in `allowed_names` (e.g. Django's `app_name`).
"""

import ast
import re
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.scopes import matches, module_level_statements, target_names
from cinematicket_lint.violations import Violation

CODE = 'CT12'
CONFIG_KEY = 'module_constant_naming'
DEFAULTS: dict = {'pattern': '^_*[A-Z][A-Z0-9_]*$', 'allowed_names': [], 'only_constant_values': True}

_DUNDER = re.compile(r'^__.+__$')
_PASCAL_CASE = re.compile(r'^_*[A-Z][a-z0-9]+[A-Za-z0-9]*$')


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    settings = resolve_options(DEFAULTS, options)
    violations: list[Violation] = []
    for statement in module_level_statements(tree):
        if isinstance(statement, ast.Assign):
            targets, value = statement.targets, statement.value
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            targets, value = [statement.target], statement.value
        else:
            continue
        if settings['only_constant_values'] and not _is_constant(value):
            continue
        for target in targets:
            for name in target_names(target):
                if _is_exempt(name.id, value, settings):
                    continue
                violations.append(
                    Violation(
                        path=str(path),
                        line=name.lineno,
                        code=CODE,
                        message=(
                            f"module-level constant '{name.id}' does not match "
                            f'the required pattern {settings["pattern"]}'
                        ),
                    )
                )
    return violations


def _is_constant(value: ast.expr) -> bool:
    """A literal, or arithmetic over literals: the values pylint treats as constants."""
    if isinstance(value, ast.Constant):
        return True
    if isinstance(value, ast.UnaryOp):
        return _is_constant(value.operand)
    if isinstance(value, ast.BinOp):
        return _is_constant(value.left) and _is_constant(value.right)
    return False


def _is_exempt(name: str, value: ast.expr, settings: dict) -> bool:
    """"""
    if name in settings['allowed_names'] or _DUNDER.match(name) or matches(settings['pattern'], name):
        return True
    return bool(_PASCAL_CASE.match(name)) and not isinstance(value, ast.Constant)
