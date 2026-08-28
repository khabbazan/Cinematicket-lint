"""Doc rule 3.2: annotate variables when not using a class constructor.

Exempt right-hand sides, either of which makes the variable's type
self-evident from syntax alone:
  1. a call whose target name starts with an uppercase letter
     (PascalCase), matching the project's class-naming-style=PascalCase
     convention already enforced by pylint.
  2. a literal data-type initialization: (), [], '', "", {}, a set
     literal, an f-string, or a number/bool/None constant.

Also exempt: a name already annotated earlier in the same function scope
(as a parameter, or via a prior `name: T = ...` assignment anywhere in
that function, including inside if/for/while/try/with blocks) — a later
plain reassignment of that name doesn't need to repeat the annotation.
"""

import ast
from pathlib import Path

from cinematicket_lint.violations import Violation

CODE = 'CT02'

_LITERAL_NODE_TYPES = (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.JoinedStr)

_SCOPE_BOUNDARY_NODE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for function_node in ast.walk(tree):
        if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        annotated_names = _collect_annotated_names(function_node)
        for statement in _walk_scope_statements(function_node.body):
            violation = _check_assignment(path, statement, annotated_names)
            if violation is not None:
                violations.append(violation)
    return violations


def _walk_scope_statements(statements: list[ast.stmt]):
    """Yields every statement reachable from `statements` without crossing into a nested scope."""
    for statement in statements:
        yield statement
        for child_block in _child_blocks(statement):
            yield from _walk_scope_statements(child_block)


def _child_blocks(statement: ast.stmt) -> list[list[ast.stmt]]:
    if isinstance(statement, _SCOPE_BOUNDARY_NODE_TYPES):
        return []
    blocks = []
    for field_name in ('body', 'orelse', 'finalbody'):
        block = getattr(statement, field_name, None)
        if isinstance(block, list):
            blocks.append(block)
    for handler in getattr(statement, 'handlers', []):
        blocks.append(handler.body)
    return blocks


def _collect_annotated_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()

    all_args = [
        *function_node.args.posonlyargs,
        *function_node.args.args,
        *function_node.args.kwonlyargs,
    ]
    if function_node.args.vararg is not None:
        all_args.append(function_node.args.vararg)
    if function_node.args.kwarg is not None:
        all_args.append(function_node.args.kwarg)
    for arg in all_args:
        if arg.annotation is not None:
            names.add(arg.arg)

    for statement in _walk_scope_statements(function_node.body):
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            names.add(statement.target.id)

    return names


def _check_assignment(path: Path, statement: ast.stmt, annotated_names: set[str]) -> Violation | None:
    if not isinstance(statement, ast.Assign):
        return None
    if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
        return None
    target_name = statement.targets[0].id
    if target_name in annotated_names:
        return None
    if _is_exempt(statement.value):
        return None
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
