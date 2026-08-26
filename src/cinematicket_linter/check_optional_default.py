"""Doc rule 3.4: optional fields must have a default value.

Scoped to pydantic BaseModel subclasses and @dataclass-decorated classes,
checking Optional[X] / X | None annotated fields for a missing default.
"""

import ast
from pathlib import Path

from cinematicket_linter.violations import Violation

CODE = 'CT03'


def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for class_node in ast.walk(tree):
        if not isinstance(class_node, ast.ClassDef) or not _is_model_class(class_node):
            continue
        for statement in class_node.body:
            if not isinstance(statement, ast.AnnAssign) or statement.value is not None:
                continue
            if not _is_optional_annotation(statement.annotation):
                continue
            field_name = statement.target.id if isinstance(statement.target, ast.Name) else '<field>'
            violations.append(
                Violation(
                    path=str(path),
                    line=statement.lineno,
                    code=CODE,
                    message=f"optional field '{field_name}' has no default value",
                )
            )
    return violations


def _is_model_class(class_node: ast.ClassDef) -> bool:
    for decorator in class_node.decorator_list:
        decorator_name = decorator.id if isinstance(decorator, ast.Name) else getattr(decorator, 'attr', '')
        if decorator_name == 'dataclass':
            return True
    for base in class_node.bases:
        base_name = base.id if isinstance(base, ast.Name) else getattr(base, 'attr', '')
        if base_name in ('BaseModel', 'Model'):
            return True
    return False


def _is_optional_annotation(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript):
        value = annotation.value
        name = value.id if isinstance(value, ast.Name) else getattr(value, 'attr', '')
        return name == 'Optional'
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _is_none(annotation.left) or _is_none(annotation.right)
    return False


def _is_none(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None
