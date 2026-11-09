"""A parameter with a default value placed before `*args`."""

import ast
from pathlib import Path

from cinematicket_lint.scopes import iter_functions
from cinematicket_lint.violations import Violation

CODE = 'CT13'
CONFIG_KEY = 'keyword_before_vararg'


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    violations: list[Violation] = []
    for function in iter_functions(tree):
        if function.args.vararg is None or not function.args.defaults:
            continue
        violations.append(
            Violation(
                path=str(path),
                line=function.lineno,
                code=CODE,
                message=(
                    f"function '{function.name}' has a parameter with a default value "
                    f'before *{function.args.vararg.arg}'
                ),
            )
        )
    return violations
