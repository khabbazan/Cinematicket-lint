"""Entry point for the cinematicket-lint pre-commit hook.

Runs the doc-rule checks that ruff and pylint cannot express, against
the file paths pre-commit passes on argv.
"""

import ast
import sys
from pathlib import Path

from cinematicket_lint import (
    check_backslash_continuation,
    check_openapi_schema,
    check_optional_default,
    check_test_prefix,
    check_variable_annotation,
)
from cinematicket_lint.config import discover_files, is_excluded, load_exclude_names
from cinematicket_lint.suppressions import filter_suppressed
from cinematicket_lint.violations import Violation


def main() -> int:
    exclude_names = load_exclude_names(Path.cwd())
    file_arguments = sys.argv[1:]
    paths = [Path(file_argument) for file_argument in file_arguments] if file_arguments else discover_files(Path.cwd())

    all_violations: list[Violation] = []
    for path in paths:
        if is_excluded(path, exclude_names):
            continue
        all_violations.extend(_check_file(path))

    for violation in all_violations:
        print(violation)
    return 1 if all_violations else 0


def _check_file(path: Path) -> list[Violation]:
    if path.suffix != '.py':
        return []

    source = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    violations.extend(check_backslash_continuation.check(path))
    violations.extend(check_variable_annotation.check(path, tree))
    violations.extend(check_optional_default.check(path, tree))
    violations.extend(check_openapi_schema.check(path, tree))
    violations.extend(check_test_prefix.check(path, tree))
    return filter_suppressed(path, violations)


if __name__ == '__main__':
    sys.exit(main())
