"""Tests for CT10: variable/argument naming pattern check (minimum name length)."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_name_length


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_name_length.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_single_character_local_variable():
    """"""
    assert _check('def foo() -> None:\n    x = 1\n') == ['x']


def test_flags_a_single_character_parameter():
    """"""
    assert _check('def foo(x: int) -> None:\n    pass\n') == ['x']


def test_flags_keyword_only_and_positional_only_parameters():
    """"""
    assert _check('def foo(a, /, *, b) -> None:\n    pass\n') == ['a', 'b']


def test_flags_vararg_and_kwarg_names():
    """"""
    assert _check('def foo(*a, **k) -> None:\n    pass\n') == ['a', 'k']


def test_flags_for_with_except_and_walrus_targets():
    """"""
    flagged = _check(
        """
        def foo(items) -> None:
            for i in items:
                pass
            with open('f') as f:
                pass
            try:
                pass
            except OSError as e:
                pass
            if (n := 1):
                pass
        """
    )
    assert flagged == ['i', 'f', 'e', 'n']


def test_flags_tuple_unpacking_targets():
    """"""
    assert _check('def foo() -> None:\n    a, (b, c) = 1, (2, 3)\n') == ['a', 'b', 'c']


def test_reports_a_repeated_name_once_per_function():
    """"""
    assert _check('def foo() -> None:\n    x = 1\n    x = 2\n') == ['x']


def test_exempts_names_of_two_or_more_characters():
    """"""
    assert _check('def foo(ab: int, _a: int, a1: int) -> None:\n    cd = 1\n') == []


def test_exempts_the_default_good_names():
    """"""
    flagged = _check(
        """
        def foo(pk, _) -> None:
            ex = 1
            Run = 2
        """
    )
    assert flagged == []


def test_exempts_comprehension_variables():
    """"""
    assert _check('def foo(items) -> None:\n    return [i for i in items]\n') == []


def test_does_not_flag_attribute_assignment():
    """"""
    assert _check('def foo(self) -> None:\n    self.x = 1\n') == []


def test_does_not_flag_module_level_variables():
    """"""
    assert _check('x = 1\n') == []


def test_checks_nested_functions_and_methods():
    """"""
    flagged = _check(
        """
        class Foo:
            def method(self, a) -> None:
                def inner(b):
                    return b
        """
    )
    assert flagged == ['a', 'b']


def test_does_not_flag_names_declared_global():
    """"""
    assert _check('def foo() -> None:\n    global x\n    x = 1\n') == []


def test_honours_a_custom_variable_pattern():
    """"""
    options = {'variable_pattern': '^[a-z]{3,}$'}
    assert _check('def foo() -> None:\n    ab = 1\n    abc = 2\n', options) == ['ab']


def test_honours_a_custom_argument_pattern():
    """"""
    options = {'argument_pattern': '^[a-z]{3,}$'}
    assert _check('def foo(ab: int, abc: int) -> None:\n    xy = 1\n', options) == ['ab']


def test_honours_custom_good_names():
    """"""
    options = {'good_names': ['x']}
    assert _check('def foo(x: int, y: int) -> None:\n    pass\n', options) == ['y']
