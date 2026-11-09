"""A parameter or local variable that shadows a module-level name."""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.scopes import (
    bound_names,
    declared_outer_names,
    iter_functions,
    module_level_statements,
    parameters,
    target_names,
)
from cinematicket_lint.violations import Violation

CODE = 'CT18'
CONFIG_KEY = 'redefined_outer_name'
DEFAULTS: dict = {'ignored_names': []}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    ignored = set(resolve_options(DEFAULTS, options)['ignored_names'])
    module_names = {name: line for name, line in _module_level_names(tree).items() if name not in ignored}
    violations: list[Violation] = []
    for function in iter_functions(tree):
        outer = declared_outer_names(function)
        candidates = {parameter.arg: parameter.lineno for parameter in parameters(function)}
        for name, line in bound_names(function).items():
            candidates.setdefault(name, line)
        for name, line in candidates.items():
            if name in module_names and name not in outer:
                violations.append(
                    Violation(
                        path=str(path),
                        line=line,
                        code=CODE,
                        message=f"'{name}' redefines a name from the outer scope (line {module_names[name]})",
                    )
                )
    return violations


def _module_level_names(tree: ast.Module) -> dict[str, int]:
    """"""
    names: dict[str, int] = {}
    for statement in module_level_statements(tree):
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.setdefault(statement.name, statement.lineno)
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            for alias in statement.names:
                names.setdefault((alias.asname or alias.name).split('.')[0], statement.lineno)
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for target in targets:
                for name in target_names(target):
                    names.setdefault(name.id, name.lineno)
    return names
