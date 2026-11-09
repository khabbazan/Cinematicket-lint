"""Tests for CT14: too many instance attributes."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_instance_attribute_count


def _class_with_attributes(count: int) -> str:
    """"""
    assignments = '\n'.join(f'        self.attr{index} = {index}' for index in range(count))
    return f'class Foo:\n    def __init__(self) -> None:\n{assignments}\n'


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_instance_attribute_count.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_class_above_the_default_maximum():
    """"""
    assert _check(_class_with_attributes(8)) == ['Foo']


def test_exempts_a_class_at_the_default_maximum():
    """"""
    assert _check(_class_with_attributes(7)) == []


def test_counts_each_attribute_once_across_assignments():
    """"""
    source = (
        _class_with_attributes(7) + '    def other(self) -> None:\n        self.attr0 = 5\n        self.attr1 = 6\n'
    )
    assert _check(source) == []


def test_counts_attributes_from_all_methods():
    """"""
    source = _class_with_attributes(7) + '    def other(self) -> None:\n        self.extra = 1\n'
    assert _check(source) == ['Foo']


def test_counts_annotated_and_tuple_assignments():
    """"""
    source = textwrap.dedent(
        """
        class Foo:
            def __init__(self) -> None:
                self.a1: int = 1
                self.a2, self.a3 = 1, 2
                self.a4 = self.a5 = 3
                self.a6 = 1
                self.a7 = 1
                self.a8 = 1
        """
    )
    assert _check(source) == ['Foo']


def test_does_not_count_class_level_attributes():
    """"""
    class_level = '\n'.join(f'    field{index}: int = {index}' for index in range(10))
    assert _check(f'class Foo:\n{class_level}\n') == []


def test_does_not_count_assignments_to_other_objects():
    """"""
    assignments = '\n'.join(f'        other.attr{index} = {index}' for index in range(10))
    assert _check(f'class Foo:\n    def method(self, other) -> None:\n{assignments}\n') == []


def test_does_not_count_class_or_static_method_assignments():
    """"""
    assignments = '\n'.join(f'        cls.attr{index} = {index}' for index in range(10))
    source = f'class Foo:\n    @classmethod\n    def build(cls) -> None:\n{assignments}\n'
    assert _check(source) == []


def test_counts_nested_classes_separately():
    """"""
    inner = '\n'.join(f'            self.attr{index} = {index}' for index in range(8))
    source = f'class Outer:\n    class Inner:\n        def __init__(self) -> None:\n{inner}\n'
    assert _check(source) == ['Inner']


def test_honours_a_custom_maximum():
    """"""
    assert _check(_class_with_attributes(3), {'max': 2}) == ['Foo']
    assert _check(_class_with_attributes(3), {'max': 3}) == []
