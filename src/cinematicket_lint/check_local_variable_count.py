"""Too many local variables, counted the way pylint does: parameters plus every name bound in the function."""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.scopes import bound_names, declared_outer_names, iter_functions, matches, parameters
from cinematicket_lint.violations import Violation

CODE = 'CT16'
CONFIG_KEY = 'local_variable_count'
DEFAULTS: dict = {'max': 15, 'ignored_argument_pattern': '_.*|^ignored_|^unused_'}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    settings = resolve_options(DEFAULTS, options)
    violations: list[Violation] = []
    for function in iter_functions(tree):
        outer = declared_outer_names(function)
        parameter_names = {parameter.arg for parameter in parameters(function)} - outer
        names = parameter_names | set(bound_names(function))
        ignored = {name for name in parameter_names if matches(settings['ignored_argument_pattern'], name)}
        count = len(names) - len(ignored)
        if count > settings['max']:
            violations.append(
                Violation(
                    path=str(path),
                    line=function.lineno,
                    code=CODE,
                    message=f"function '{function.name}' has {count} local variables (max {settings['max']})",
                )
            )
    return violations
