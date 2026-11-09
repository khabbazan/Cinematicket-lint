"""An instance attribute first defined outside the defining methods (`__init__`, `setUp`, ...).

Conservative by design: a class is skipped when any base class cannot be resolved to a class
defined in the same file, because the attribute may be defined in that base.
"""

import ast
from pathlib import Path

from cinematicket_lint.check_instance_attribute_count import instance_attributes
from cinematicket_lint.config import resolve_options
from cinematicket_lint.violations import Violation

CODE = 'CT15'
CONFIG_KEY = 'attribute_outside_init'
DEFAULTS: dict = {'defining_methods': ['__init__', '__new__', 'setUp', '__post_init__']}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    defining_methods = set(resolve_options(DEFAULTS, options)['defining_methods'])
    local_classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        defined = _defined_names(node, local_classes, defining_methods)
        if defined is None:
            continue
        for attribute, assignments in instance_attributes(node).items():
            if attribute in defined:
                continue
            violations.append(
                Violation(
                    path=str(path),
                    line=assignments[0][1],
                    code=CODE,
                    message=(
                        f"attribute '{attribute}' of class '{node.name}' "
                        f'is defined outside {_describe(defining_methods)}'
                    ),
                )
            )
    return violations


def _describe(defining_methods: set[str]) -> str:
    """"""
    return ' / '.join(sorted(defining_methods))


def _defined_names(
    class_node: ast.ClassDef,
    local_classes: dict[str, ast.ClassDef],
    defining_methods: set[str],
    seen: frozenset[str] = frozenset(),
) -> set[str] | None:
    """Names defined by the class and its same-file ancestors; None when an ancestor cannot be resolved."""
    defined = _class_level_names(class_node)
    for attribute, assignments in instance_attributes(class_node).items():
        if any(method in defining_methods for method, _ in assignments):
            defined.add(attribute)
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == 'object':
            continue
        if not isinstance(base, ast.Name) or base.id not in local_classes or base.id in seen:
            return None
        inherited = _defined_names(local_classes[base.id], local_classes, defining_methods, seen | {class_node.name})
        if inherited is None:
            return None
        defined |= inherited
    return defined


def _class_level_names(class_node: ast.ClassDef) -> set[str]:
    """"""
    names: set[str] = set()
    for statement in class_node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            names.add(statement.target.id)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(statement.name)
    return names
