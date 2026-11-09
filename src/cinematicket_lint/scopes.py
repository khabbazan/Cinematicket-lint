"""AST helpers shared by the scope-aware checks (names bound per function, module-level names)."""

import ast
import re
from collections.abc import Iterator

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef

_NESTED_SCOPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def iter_functions(tree: ast.AST) -> Iterator[FunctionNode]:
    """"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def iter_scope_nodes(function: FunctionNode) -> Iterator[ast.AST]:
    """Yield every node of the function's own scope; nested scopes are yielded but not entered."""
    stack: list[ast.AST] = list(reversed(function.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _NESTED_SCOPES):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def parameters(function: FunctionNode) -> list[ast.arg]:
    """"""
    arguments = function.args
    collected = [*arguments.posonlyargs, *arguments.args]
    if arguments.vararg is not None:
        collected.append(arguments.vararg)
    collected.extend(arguments.kwonlyargs)
    if arguments.kwarg is not None:
        collected.append(arguments.kwarg)
    return collected


def declared_outer_names(function: FunctionNode) -> set[str]:
    """Names declared `global` or `nonlocal` in the function's own scope."""
    declared: set[str] = set()
    for node in iter_scope_nodes(function):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            declared.update(node.names)
    return declared


def bound_names(function: FunctionNode) -> dict[str, int]:
    """Names bound in the function's own scope (excluding parameters) mapped to their first line."""
    bound: dict[str, int] = {}
    outer = declared_outer_names(function)

    def add(name: str, line: int) -> None:
        """"""
        if name not in outer and name not in bound:
            bound[name] = line

    for node in iter_scope_nodes(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            add(node.id, node.lineno)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            add(node.name, node.lineno)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                add((alias.asname or alias.name).split('.')[0], node.lineno)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            add(node.name, node.lineno)
    return bound


def module_level_statements(tree: ast.Module) -> Iterator[ast.stmt]:
    """Module-level statements, entering `if`/`try`/`with` blocks but never functions or classes."""
    stack: list[ast.stmt] = list(reversed(tree.body))
    while stack:
        node = stack.pop()
        yield node
        children: list[ast.stmt] = []
        if isinstance(node, ast.If):
            children = [*node.body, *node.orelse]
        elif isinstance(node, ast.Try):
            children = [
                *node.body,
                *[stmt for handler in node.handlers for stmt in handler.body],
                *node.orelse,
                *node.finalbody,
            ]
        elif isinstance(node, ast.With):
            children = list(node.body)
        stack.extend(reversed(children))


def target_names(target: ast.expr) -> Iterator[ast.Name]:
    """Plain names inside an assignment target (tuple/list/starred unpacking included)."""
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from target_names(element)
    elif isinstance(target, ast.Starred):
        yield from target_names(target.value)


def matches(pattern: str, name: str) -> bool:
    """"""
    return re.match(pattern, name) is not None
