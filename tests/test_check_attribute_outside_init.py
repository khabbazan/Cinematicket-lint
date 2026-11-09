"""Tests for CT15: attribute first defined outside the defining methods."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_attribute_outside_init


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_attribute_outside_init.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_an_attribute_defined_only_outside_init():
    """"""
    flagged = _check(
        """
        class Foo:
            def __init__(self) -> None:
                self.a = 1

            def run(self) -> None:
                self.b = 2
        """
    )
    assert flagged == ['b']


def test_flags_in_a_class_without_init():
    """"""
    assert _check('class Foo:\n    def run(self) -> None:\n        self.b = 2\n') == ['b']


def test_reports_an_attribute_once():
    """"""
    source = 'class Foo:\n    def run(self) -> None:\n        self.b = 1\n        self.b = 2\n\n    def stop(self) -> None:\n        self.b = 3\n'
    assert _check(source) == ['b']


def test_exempts_an_attribute_also_defined_in_init():
    """"""
    flagged = _check(
        """
        class Foo:
            def __init__(self) -> None:
                self.b = None

            def run(self) -> None:
                self.b = 2
        """
    )
    assert flagged == []


def test_exempts_attributes_defined_in_the_default_defining_methods():
    """"""
    flagged = _check(
        """
        class Foo:
            def __new__(cls) -> None:
                self = super().__new__(cls)
                self.a = 1

            def setUp(self) -> None:
                self.b = 1

            def __post_init__(self) -> None:
                self.c = 1
        """
    )
    assert flagged == []


def test_exempts_an_attribute_declared_at_class_level():
    """"""
    flagged = _check(
        """
        class Foo:
            b = None
            c: int = 0

            def run(self) -> None:
                self.b = 2
                self.c = 3
        """
    )
    assert flagged == []


def test_exempts_an_attribute_defined_in_a_local_base_class():
    """"""
    flagged = _check(
        """
        class Base:
            def __init__(self) -> None:
                self.b = None

        class Foo(Base):
            def run(self) -> None:
                self.b = 2
        """
    )
    assert flagged == []


def test_flags_when_a_local_base_class_does_not_define_it():
    """"""
    flagged = _check(
        """
        class Base:
            def __init__(self) -> None:
                self.a = None

        class Foo(Base):
            def run(self) -> None:
                self.b = 2
        """
    )
    assert flagged == ['b']


def test_skips_classes_with_unresolvable_bases():
    """"""
    flagged = _check(
        """
        class Foo(SomethingImported):
            def run(self) -> None:
                self.b = 2
        """
    )
    assert flagged == []


def test_checks_classes_with_an_explicit_object_base():
    """"""
    assert _check('class Foo(object):\n    def run(self) -> None:\n        self.b = 2\n') == ['b']


def test_ignores_assignments_to_other_objects_and_class_methods():
    """"""
    flagged = _check(
        """
        class Foo:
            def run(self, other) -> None:
                other.b = 2

            @classmethod
            def build(cls) -> None:
                cls.c = 3
        """
    )
    assert flagged == []


def test_honours_custom_defining_methods():
    """"""
    source = 'class Foo:\n    def configure(self) -> None:\n        self.b = 2\n'
    assert _check(source) == ['b']
    assert _check(source, {'defining_methods': ['configure']}) == []
