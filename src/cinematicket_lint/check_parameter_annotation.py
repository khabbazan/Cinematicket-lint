"""Doc rule 3.3: annotate every function/method parameter.

`self` and `cls` are exempt (their type is the enclosing class, which
adds nothing when spelled out). `*args` and `**kwargs` are exempt too
(their element type isn't expressible without generics that add more
noise than value at call sites). Every other parameter — positional,
keyword-only — must carry a type annotation.
"""

import ast
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT08'

_EXEMPT_PARAMETER_NAMES = ('self', 'cls')


def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        violations.extend(_check_function(path, node))
    return violations


def _check_function(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Violation]:
    violations: list[Violation] = []

    all_params = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]

    for parameter in all_params:
        if parameter.arg in _EXEMPT_PARAMETER_NAMES:
            continue
        if parameter.annotation is not None:
            continue
        violations.append(
            Violation(
                path=str(path),
                line=parameter.lineno,
                code=CODE,
                message=f"parameter '{parameter.arg}' of function '{node.name}' has no type annotation",
            )
        )

    return violations
