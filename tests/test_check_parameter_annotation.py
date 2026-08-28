"""Tests for CT08: function-parameter-annotation check."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_parameter_annotation


def _check(source: str) -> list[str]:
    tree = ast.parse(textwrap.dedent(source))
    violations = check_parameter_annotation.check(Path('fake.py'), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_an_unannotated_parameter():
    flagged = _check(
        """
        def foo(value):
            return value
        """
    )
    assert flagged == ['value']


def test_exempts_self_and_cls():
    flagged = _check(
        """
        class Foo:
            def method(self, value: int):
                return value

            @classmethod
            def make(cls, value: int):
                return cls()
        """
    )
    assert flagged == []


def test_flags_unannotated_star_args_and_kwargs():
    flagged = _check(
        """
        def foo(*args, **kwargs):
            return args, kwargs
        """
    )
    assert flagged == ['args', 'kwargs']


def test_exempts_fully_annotated_parameters():
    flagged = _check(
        """
        def foo(a: int, b: str = '', *args: object, c: bool = False, **kwargs: object):
            return a, b, args, c, kwargs
        """
    )
    assert flagged == []


def test_flags_a_keyword_only_parameter():
    flagged = _check(
        """
        def foo(*, value):
            return value
        """
    )
    assert flagged == ['value']
