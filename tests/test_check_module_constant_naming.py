"""Tests for CT12: module-level constants must be UPPER_CASE."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_module_constant_naming


def _check(source: str, options: dict | None = None) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_module_constant_naming.check(Path('fake.py'), tree, options)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_a_lower_case_module_level_assignment():
    """"""
    assert _check("app_name = 'advertising'\n") == ['app_name']


def test_flags_a_mixed_case_module_level_constant():
    """"""
    assert _check('MaxRetries = 3\n') == ['MaxRetries']


def test_flags_an_annotated_module_level_assignment():
    """"""
    assert _check('limit: int = 3\n') == ['limit']


def test_flags_constant_expressions():
    """"""
    flagged = _check(
        """
        negative = -1
        nothing = None
        joined = 'a' + 'b'
        total = 1 + 2
        """
    )
    assert flagged == ['negative', 'nothing', 'joined', 'total']


def test_does_not_flag_non_constant_values_by_default():
    """"""
    flagged = _check(
        """
        router = DefaultRouter()
        urlpatterns = router.urls + []
        items = []
        mapping = {'key': 1}
        pair = (1, 2)
        text = f'{router}'
        first, second = 1, 2
        """
    )
    assert flagged == []


def test_flags_non_constant_values_when_only_constant_values_is_disabled():
    """"""
    flagged = _check(
        'router = DefaultRouter()\nfirst, second = 1, 2\n',
        {'only_constant_values': False},
    )
    assert flagged == ['router', 'first', 'second']


def test_flags_assignments_nested_in_module_level_if_and_try():
    """"""
    flagged = _check(
        """
        if True:
            inside_if = 1
        try:
            inside_try = 1
        except ImportError:
            inside_except = 1
        """
    )
    assert flagged == ['inside_if', 'inside_try', 'inside_except']


def test_exempts_upper_case_names():
    """"""
    assert _check('MAX_RETRIES = 3\nX = 1\n_PRIVATE = 2\nA1 = 3\n') == []


def test_exempts_dunder_names():
    """"""
    assert _check("__all__ = ['a']\n__version__ = '1'\n") == []


def test_exempts_class_aliases_and_type_variables():
    """"""
    flagged = _check(
        """
        Alias = SomeClass
        Qualified = module.SomeClass
        Generic = TypeVar('Generic')
        Json = dict[str, int]
        """
    )
    assert flagged == []


def test_exempts_annotated_values_without_an_assignment():
    """"""
    assert _check('limit: int\n') == []


def test_does_not_flag_assignments_inside_functions_and_classes():
    """"""
    flagged = _check(
        """
        def func() -> None:
            local_value = 1

        class Foo:
            class_value = 1
        """
    )
    assert flagged == []


def test_does_not_flag_attribute_or_subscript_targets():
    """"""
    assert _check('settings.value = 1\nregistry["key"] = 2\n') == []


def test_honours_allowed_names():
    """"""
    source = "app_name = 'x'\nnamespace = 'y'\nother = 1\n"
    assert _check(source, {'allowed_names': ['app_name', 'namespace']}) == ['other']


def test_honours_a_custom_pattern():
    """"""
    assert _check('Limit = 1\nlimit = 2\n', {'pattern': '^[a-z]+$'}) == ['Limit']
