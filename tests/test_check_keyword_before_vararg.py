"""Tests for CT13: a defaulted parameter before *args."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_keyword_before_vararg


def _check(source: str) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_keyword_before_vararg.check(Path('fake.py'), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_defaulted_parameter_before_vararg():
    """"""
    assert _check('def foo(a, b=None, *args):\n    pass\n') == ['foo']


def test_flags_when_the_only_positional_parameter_has_a_default():
    """"""
    assert _check('def foo(a=1, *args):\n    pass\n') == ['foo']


def test_flags_async_functions_and_methods():
    """"""
    flagged = _check(
        """
        async def coro(a=1, *args):
            pass

        class Foo:
            def method(self, a=1, *args):
                pass
        """
    )
    assert flagged == ['coro', 'method']


def test_flags_with_kwargs_present():
    """"""
    assert _check('def foo(a=1, *args, **kwargs):\n    pass\n') == ['foo']


def test_exempts_keyword_only_defaults_after_vararg():
    """"""
    assert _check('def foo(a, *args, b=None):\n    pass\n') == []


def test_exempts_functions_without_defaults():
    """"""
    assert _check('def foo(a, b, *args):\n    pass\n') == []


def test_exempts_functions_without_vararg():
    """"""
    assert _check('def foo(a, b=None, **kwargs):\n    pass\n') == []


def test_flags_positional_only_defaults():
    """"""
    assert _check('def foo(a=1, /, *args):\n    pass\n') == ['foo']
