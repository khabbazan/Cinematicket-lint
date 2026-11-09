"""Tests for CT18: a parameter or local shadows a module-level name."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_redefined_outer_name


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_redefined_outer_name.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_parameter_shadowing_a_module_level_variable():
    """"""
    assert _check('value = 1\n\ndef foo(value) -> None:\n    pass\n') == ['value']


def test_flags_a_local_shadowing_a_module_level_variable():
    """"""
    assert _check('value = 1\n\ndef foo() -> None:\n    value = 2\n') == ['value']


def test_flags_shadowing_of_functions_classes_and_imports():
    """"""
    flagged = _check(
        """
        import os
        from pathlib import Path

        def helper() -> None:
            pass

        class Model:
            pass

        def foo(os, Path, helper, Model) -> None:
            pass
        """
    )
    assert flagged == ['os', 'Path', 'helper', 'Model']


def test_flags_loop_with_and_except_targets():
    """"""
    flagged = _check(
        """
        item = 1
        handle = 2
        error = 3

        def foo(items) -> None:
            for item in items:
                pass
            with open('f') as handle:
                pass
            try:
                pass
            except OSError as error:
                pass
        """
    )
    assert flagged == ['item', 'handle', 'error']


def test_flags_module_names_defined_under_if_and_try():
    """"""
    flagged = _check(
        """
        try:
            import json
        except ImportError:
            json = None

        def foo(json) -> None:
            pass
        """
    )
    assert flagged == ['json']


def test_flags_methods_and_nested_functions():
    """"""
    flagged = _check(
        """
        value = 1

        class Foo:
            def method(self, value) -> None:
                def inner(value):
                    pass
        """
    )
    assert flagged == ['value', 'value']


def test_reports_a_name_once_per_function():
    """"""
    assert _check('value = 1\n\ndef foo(value) -> None:\n    value = 2\n') == ['value']


def test_exempts_a_different_name():
    """"""
    assert _check('value = 1\n\ndef foo(other) -> None:\n    third = 2\n') == []


def test_exempts_names_declared_global():
    """"""
    assert _check('value = 1\n\ndef foo() -> None:\n    global value\n    value = 2\n') == []


def test_exempts_names_that_are_only_defined_in_another_function():
    """"""
    assert _check('def first() -> None:\n    value = 1\n\ndef second(value) -> None:\n    pass\n') == []


def test_exempts_class_level_names():
    """"""
    assert _check('class Foo:\n    value = 1\n\ndef bar(value) -> None:\n    pass\n') == []


def test_exempts_attribute_assignments():
    """"""
    assert _check('value = 1\n\ndef foo(obj) -> None:\n    obj.value = 2\n') == []


def test_does_not_flag_the_module_level_definition_itself():
    """"""
    assert _check('value = 1\n\ndef foo() -> None:\n    return value\n') == []


def test_honours_ignored_names():
    """"""
    source = 'value = 1\nfixture = 2\n\ndef foo(value, fixture) -> None:\n    pass\n'
    assert _check(source, {'ignored_names': ['fixture']}) == ['value']
