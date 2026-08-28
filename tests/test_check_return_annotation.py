"""Tests for CT09: function-return-annotation check."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_return_annotation


def _check(source: str) -> list[str]:
    tree = ast.parse(textwrap.dedent(source))
    violations = check_return_annotation.check(Path('fake.py'), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_missing_return_annotation():
    flagged = _check(
        """
        def foo():
            return 1
        """
    )
    assert flagged == ['foo']


def test_exempts_an_annotated_return_type():
    flagged = _check(
        """
        def foo() -> int:
            return 1
        """
    )
    assert flagged == []


def test_exempts_bare_test_success_and_test_failure():
    flagged = _check(
        """
        def test_success():
            pass

        def test_failure():
            pass
        """
    )
    assert flagged == []


def test_exempts_test_success_and_test_failure_with_suffix():
    flagged = _check(
        """
        def test_success_with_pagination():
            pass

        def test_failure_when_not_found():
            pass
        """
    )
    assert flagged == []


def test_exempts_dunder_methods():
    flagged = _check(
        """
        class Foo:
            def __init__(self):
                pass

            def __str__(self):
                return ''
        """
    )
    assert flagged == []


def test_still_flags_a_regular_method_without_return_annotation():
    flagged = _check(
        """
        class Foo:
            def bar(self):
                return 1
        """
    )
    assert flagged == ['bar']
