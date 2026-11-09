"""Entry point for the cinematicket-lint pre-commit hook.

Runs the doc-rule checks that ruff and pylint cannot express, against
the file paths pre-commit passes on argv.
"""

import ast
import sys
from pathlib import Path

from cinematicket_lint import (
    check_attribute_outside_init,
    check_backslash_continuation,
    check_bad_names,
    check_instance_attribute_count,
    check_keyword_before_vararg,
    check_local_variable_count,
    check_module_constant_naming,
    check_module_line_count,
    check_name_length,
    check_openapi_schema,
    check_optional_default,
    check_parameter_annotation,
    check_redefined_outer_name,
    check_return_annotation,
    check_test_prefix,
    check_variable_annotation,
)
from cinematicket_lint.config import discover_files, is_excluded, load_config
from cinematicket_lint.suppressions import filter_suppressed
from cinematicket_lint.violations import Violation

_CONFIGURABLE_CHECKS = (
    check_name_length,
    check_bad_names,
    check_module_constant_naming,
    check_keyword_before_vararg,
    check_instance_attribute_count,
    check_attribute_outside_init,
    check_local_variable_count,
    check_module_line_count,
    check_redefined_outer_name,
)


def main() -> int:
    config = load_config(Path.cwd())
    exclude_names = config.get('exclude', [])
    file_arguments = sys.argv[1:]
    paths = [Path(file_argument) for file_argument in file_arguments] if file_arguments else discover_files(Path.cwd())

    all_violations: list[Violation] = []
    for path in paths:
        if is_excluded(path, exclude_names):
            continue
        all_violations.extend(_check_file(path, config))

    for violation in all_violations:
        print(violation)
    return 1 if all_violations else 0


def _check_file(path: Path, config: dict) -> list[Violation]:
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
    violations.extend(check_parameter_annotation.check(path, tree))
    violations.extend(check_return_annotation.check(path, tree))
    for configurable_check in _CONFIGURABLE_CHECKS:
        rule_options = config.get(configurable_check.CONFIG_KEY, {})
        if rule_options.get('enabled', True):
            violations.extend(configurable_check.check(path, tree, rule_options))
    return filter_suppressed(path, violations)


if __name__ == '__main__':
    sys.exit(main())
