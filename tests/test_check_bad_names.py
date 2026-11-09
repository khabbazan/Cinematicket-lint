"""Tests for CT11: disallowed placeholder names (foo, bar, ...)."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_bad_names


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_bad_names.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_each_default_bad_name_as_a_variable():
    """"""
    source = '\n'.join(f'{name} = 1' for name in ('foo', 'bar', 'baz', 'toto', 'tutu', 'tata'))
    assert _check(source) == ['foo', 'bar', 'baz', 'toto', 'tutu', 'tata']


def test_flags_a_bad_parameter_name():
    """"""
    assert _check('def process(bar: int) -> None:\n    pass\n') == ['bar']


def test_flags_a_bad_function_name():
    """"""
    assert _check('def baz() -> None:\n    pass\n') == ['baz']


def test_flags_a_bad_async_function_name():
    """"""
    assert _check('async def baz() -> None:\n    pass\n') == ['baz']


def test_flags_a_bad_class_name():
    """"""
    assert _check('class toto:\n    pass\n') == ['toto']


def test_flags_loop_and_except_targets():
    """"""
    flagged = _check(
        """
        for foo in range(3):
            pass
        try:
            pass
        except OSError as bar:
            pass
        """
    )
    assert flagged == ['foo', 'bar']


def test_does_not_flag_attribute_names():
    """"""
    assert _check('self.foo = 1\nvalue = other.bar\n') == []


def test_does_not_flag_names_that_merely_contain_a_bad_name():
    """"""
    assert _check('foobar = 1\nfoo_value = 2\n') == []


def test_does_not_flag_names_that_are_only_read():
    """"""
    assert _check('value = foo\n') == []


def test_honours_custom_names():
    """"""
    assert _check('temp = 1\nfoo = 2\n', {'names': ['temp']}) == ['temp']


def test_an_empty_names_list_disables_the_check():
    """"""
    assert _check('foo = 1\n', {'names': []}) == []
