"""Tests for CT16: too many local variables (parameters included)."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_local_variable_count


def _function_with_locals(count: int, parameters: str = '') -> str:
    """"""
    assignments = '\n'.join(f'    local{index} = {index}' for index in range(count))
    return f'def foo({parameters}) -> None:\n{assignments}\n    pass\n'


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_local_variable_count.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_function_above_the_default_maximum():
    """"""
    assert _check(_function_with_locals(16)) == ['foo']


def test_exempts_a_function_at_the_default_maximum():
    """"""
    assert _check(_function_with_locals(15)) == []


def test_counts_parameters_as_locals():
    """"""
    assert _check(_function_with_locals(14, 'first, second')) == ['foo']
    assert _check(_function_with_locals(13, 'first, second')) == []


def test_counts_self_and_variadic_parameters():
    """"""
    source = textwrap.dedent(
        """
        class Foo:
            def method(self, *args, **kwargs) -> None:
        """
    ) + '\n'.join(f'        local{index} = {index}' for index in range(13))
    assert _check(source) == ['method']


def test_counts_a_reassigned_name_once():
    """"""
    source = 'def foo() -> None:\n' + '    value = 1\n' * 30
    assert _check(source) == []


def test_counts_loop_with_except_import_and_nested_definition_names():
    """"""
    source = textwrap.dedent(
        """
        def foo(items) -> None:
            for item in items:
                pass
            with open('f') as handle:
                pass
            try:
                pass
            except OSError as error:
                pass
            import os
            from sys import path
            def inner():
                pass
            class Inner:
                pass
        """
    )
    assert _check(source, {'max': 7}) == ['foo']
    assert _check(source, {'max': 8}) == []


def test_does_not_count_nested_function_locals():
    """"""
    inner = '\n'.join(f'        inner{index} = {index}' for index in range(20))
    source = f'def foo() -> None:\n    def helper() -> None:\n{inner}\n'
    assert _check(source) == ['helper']


def test_does_not_count_comprehension_variables():
    """"""
    comprehensions = '\n'.join(f'    [value{index} for value{index} in range(3)]' for index in range(20))
    assert _check(f'def foo() -> None:\n{comprehensions}\n') == []


def test_does_not_count_names_declared_global():
    """"""
    names = ', '.join(f'g{index}' for index in range(20))
    assignments = '\n'.join(f'    g{index} = 1' for index in range(20))
    assert _check(f'def foo() -> None:\n    global {names}\n{assignments}\n') == []


def test_does_not_count_ignored_parameters():
    """"""
    parameters = ', '.join(['_a', 'ignored_b', 'unused_c'])
    assert _check(_function_with_locals(14, parameters)) == []


def test_checks_async_functions():
    """"""
    source = _function_with_locals(16).replace('def foo', 'async def foo')
    assert _check(source) == ['foo']


def test_honours_a_custom_maximum():
    """"""
    assert _check(_function_with_locals(4), {'max': 3}) == ['foo']
    assert _check(_function_with_locals(4), {'max': 4}) == []


def test_honours_a_custom_ignored_parameter_pattern():
    """"""
    options = {'max': 3, 'ignored_argument_pattern': '^skip_'}
    assert _check(_function_with_locals(2, 'skip_a, skip_b'), options) == []
    assert _check(_function_with_locals(2, 'a, b'), options) == ['foo']
