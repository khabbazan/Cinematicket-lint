"""Too many instance attributes (`self.x = ...` across all methods of a class)."""

import ast
from pathlib import Path

from cinematicket_lint.config import resolve_options
from cinematicket_lint.violations import Violation

CODE = 'CT14'
CONFIG_KEY = 'instance_attribute_count'
DEFAULTS: dict = {'max': 7}


def check(path: Path, tree: ast.Module, options: dict | None = None) -> list[Violation]:
    """"""
    maximum = resolve_options(DEFAULTS, options)['max']
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        count = len(instance_attributes(node))
        if count > maximum:
            violations.append(
                Violation(
                    path=str(path),
                    line=node.lineno,
                    code=CODE,
                    message=f"class '{node.name}' has {count} instance attributes (max {maximum})",
                )
            )
    return violations


def instance_attributes(class_node: ast.ClassDef) -> dict[str, list[tuple[str, int]]]:
    """Attributes assigned through the first parameter of the class's methods: name -> [(method name, line)]."""
    attributes: dict[str, list[tuple[str, int]]] = {}
    for method in class_node.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) or not method.args.args:
            continue
        if _is_class_or_static(method):
            continue
        receiver = method.args.args[0].arg
        for node in _walk_without_nested_classes(method):
            for attribute in _assigned_attributes(node):
                if isinstance(attribute.value, ast.Name) and attribute.value.id == receiver:
                    attributes.setdefault(attribute.attr, []).append((method.name, attribute.lineno))
    return attributes


def _is_class_or_static(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """"""
    names = {decorator.id for decorator in method.decorator_list if isinstance(decorator, ast.Name)}
    return bool(names & {'classmethod', 'staticmethod'})


def _walk_without_nested_classes(method: ast.AST) -> list[ast.AST]:
    """"""
    collected: list[ast.AST] = []
    stack: list[ast.AST] = list(ast.iter_child_nodes(method))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.ClassDef):
            continue
        collected.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return collected


def _assigned_attributes(node: ast.AST) -> list[ast.Attribute]:
    """"""
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return []
    attributes: list[ast.Attribute] = []
    for target in targets:
        attributes.extend(_attribute_targets(target))
    return attributes


def _attribute_targets(target: ast.expr) -> list[ast.Attribute]:
    """"""
    if isinstance(target, ast.Attribute):
        return [target]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [attribute for element in target.elts for attribute in _attribute_targets(element)]
    if isinstance(target, ast.Starred):
        return _attribute_targets(target.value)
    return []
