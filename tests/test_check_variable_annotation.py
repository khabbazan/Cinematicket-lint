"""Tests for CT02: variable-annotation check, including scope-aware exemptions."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_variable_annotation


def _check(source: str) -> list[str]:
    tree = ast.parse(textwrap.dedent(source))
    violations = check_variable_annotation.check(Path('fake.py'), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_never_annotated_name():
    flagged = _check(
        """
        def foo():
            y = compute()
            return y
        """
    )
    assert flagged == ['y']


def test_exempts_a_class_constructor_call():
    flagged = _check(
        """
        def foo():
            thing = SomeClass()
            return thing
        """
    )
    assert flagged == []


def test_exempts_a_literal_initialization():
    flagged = _check(
        """
        def foo():
            items = []
            data = {}
            return items, data
        """
    )
    assert flagged == []


def test_does_not_reflag_a_reassignment_of_an_already_annotated_name():
    flagged = _check(
        """
        def foo():
            result: dict = compute()
            result = compute()
            return result
        """
    )
    assert flagged == []


def test_does_not_reflag_a_reassignment_inside_a_nested_if_block():
    flagged = _check(
        """
        def foo(flag: bool):
            result: dict = compute()
            if flag:
                result = compute()
            return result
        """
    )
    assert flagged == []


def test_flags_a_never_annotated_reassignment_inside_a_nested_if_block():
    flagged = _check(
        """
        def foo(flag: bool):
            if flag:
                result = compute()
            return result
        """
    )
    assert flagged == ['result']


def test_exempts_a_reassignment_of_an_annotated_parameter():
    flagged = _check(
        """
        def foo(count: int):
            count = count + 1
            return count
        """
    )
    assert flagged == []


def test_does_not_leak_annotations_across_function_scopes():
    flagged = _check(
        """
        def outer():
            value: dict = compute()

            def inner():
                value = compute()
                return value

            return value
        """
    )
    assert flagged == ['value']
