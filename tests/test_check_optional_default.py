"""Tests for CT03: optional fields of pydantic BaseModel need a default."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_optional_default


def _check(source: str) -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_optional_default.check(Path('fake.py'), tree)
    return [violation.message.split("'")[1] for violation in violations]


def test_flags_an_optional_field_without_default_on_a_base_model():
    """"""
    assert _check('class Foo(BaseModel):\n    name: Optional[str]\n') == ['name']


def test_flags_a_none_union_field_without_default_on_a_base_model():
    """"""
    assert _check('class Foo(BaseModel):\n    name: str | None\n') == ['name']


def test_flags_a_qualified_base_model():
    """"""
    assert _check('class Foo(pydantic.BaseModel):\n    name: str | None\n') == ['name']


def test_exempts_an_optional_field_with_a_default():
    """"""
    assert _check('class Foo(BaseModel):\n    name: str | None = None\n') == []


def test_exempts_a_required_field():
    """"""
    assert _check('class Foo(BaseModel):\n    name: str\n') == []


def test_does_not_flag_dataclasses():
    """"""
    source = (
        '@dataclass\nclass Foo:\n    name: str | None\n\n@dataclasses.dataclass\nclass Bar:\n    name: Optional[str]\n'
    )
    assert _check(source) == []


def test_does_not_flag_plain_classes_and_django_models():
    """"""
    source = 'class Foo:\n    name: str | None\n\nclass Bar(models.Model):\n    name: str | None\n'
    assert _check(source) == []
