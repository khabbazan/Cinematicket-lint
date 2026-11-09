"""Tests for CT04/CT05/CT06: drf-yasg openapi.Schema / openapi.Parameter conventions."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import check_openapi_schema

_IMPORT = 'from drf_yasg import openapi\n'


def _check(source: str) -> list[tuple[str, int]]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    violations = check_openapi_schema.check(Path('fake.py'), tree)
    return [(violation.code, violation.line) for violation in violations]


def _codes(source: str) -> list[str]:
    """"""
    return [code for code, _ in _check(source)]


def test_ct04_flags_a_response_schema_without_example():
    """"""
    source = _IMPORT + "SUCCESS_RESPONSE = openapi.Schema(type=openapi.TYPE_OBJECT, description='Done.')\n"
    assert _codes(source) == ['CT04']


def test_ct04_matches_response_in_the_variable_name_case_insensitively():
    """"""
    source = _IMPORT + "user_response = openapi.Schema(type=openapi.TYPE_OBJECT, description='Done.')\n"
    assert _codes(source) == ['CT04']


def test_ct04_accepts_a_response_schema_with_example():
    """"""
    source = _IMPORT + "RESPONSE = openapi.Schema(type=openapi.TYPE_OBJECT, description='Done.', example={})\n"
    assert _codes(source) == []


def test_ct04_does_not_require_an_example_for_request_schemas():
    """"""
    source = _IMPORT + "REQUEST_BODY = openapi.Schema(type=openapi.TYPE_OBJECT, description='Input.')\n"
    assert _codes(source) == []


def test_ct04_applies_to_nested_schemas_inside_a_response_assignment():
    """"""
    source = (
        _IMPORT
        + 'RESPONSE = openapi.Schema(\n'
        + "    type=openapi.TYPE_OBJECT, description='Outer.', example={},\n"
        + "    properties={'a': openapi.Schema(type=openapi.TYPE_STRING, description='Inner.')},\n"
        + ')\n'
    )
    assert _codes(source) == ['CT04']


def test_ct04_applies_to_parameters_assigned_to_a_response_variable():
    """"""
    source = _IMPORT + "RESPONSE_PARAM = openapi.Parameter('a', openapi.IN_QUERY, description='Done.')\n"
    assert _codes(source) == ['CT04']


def test_ct05_flags_a_schema_without_description():
    """"""
    assert _codes(_IMPORT + 'BODY = openapi.Schema(type=openapi.TYPE_OBJECT)\n') == ['CT05']


def test_ct05_flags_a_parameter_without_description():
    """"""
    assert _codes(_IMPORT + "PARAM = openapi.Parameter('a', openapi.IN_QUERY)\n") == ['CT05']


def test_ct05_applies_regardless_of_the_variable_name():
    """"""
    assert _codes(_IMPORT + "x = [openapi.Schema(type='string')]\n") == ['CT05']


def test_ct05_applies_to_calls_that_are_not_assigned():
    """"""
    assert _codes(_IMPORT + "def build():\n    return openapi.Schema(type='string')\n") == ['CT05']


def test_ct06_flags_a_description_without_a_trailing_period():
    """"""
    assert _codes(_IMPORT + "BODY = openapi.Schema(description='No period')\n") == ['CT06']


def test_ct06_accepts_a_description_with_a_trailing_period():
    """"""
    assert _codes(_IMPORT + "BODY = openapi.Schema(description='Has period.')\n") == []


def test_ct06_ignores_trailing_whitespace_after_the_period():
    """"""
    assert _codes(_IMPORT + "BODY = openapi.Schema(description='Has period.  ')\n") == []


def test_ct06_ignores_descriptions_that_are_not_string_literals():
    """"""
    assert _codes(_IMPORT + 'BODY = openapi.Schema(description=DESCRIPTION)\n') == []
    assert _codes(_IMPORT + "BODY = openapi.Schema(description=_('Text'))\n") == []


def test_ct06_flags_an_empty_description():
    """"""
    assert _codes(_IMPORT + "BODY = openapi.Schema(description='')\n") == ['CT06']


def test_reports_ct06_on_the_line_of_the_description_value():
    """"""
    source = _IMPORT + "BODY = openapi.Schema(\n    type='string',\n    description='No period',\n)\n"
    assert _check(source) == [('CT06', 4)]


def test_reports_ct04_and_ct05_on_the_line_of_the_call():
    """"""
    source = _IMPORT + 'RESPONSE = openapi.Schema(\n    type="string",\n)\n'
    assert _check(source) == [('CT04', 2), ('CT05', 2)]


def test_reports_every_problem_of_one_call():
    """"""
    assert sorted(_codes(_IMPORT + 'RESPONSE = openapi.Schema(type="string")\n')) == ['CT04', 'CT05']


def test_skips_files_that_do_not_import_openapi_from_drf_yasg():
    """"""
    assert _codes('RESPONSE = openapi.Schema(type="string")\n') == []
    assert _codes('from other import openapi\nRESPONSE = openapi.Schema(type="string")\n') == []


def test_ignores_other_openapi_callables():
    """"""
    source = _IMPORT + 'RESPONSE = openapi.Response("ok")\nITEMS = openapi.Items(type="string")\n'
    assert _codes(source) == []


def test_ignores_schema_calls_on_other_objects():
    """"""
    assert _codes(_IMPORT + 'value = other.Schema(type="string")\n') == []


def test_accepts_a_fully_valid_response_schema():
    """"""
    source = _IMPORT + "RESPONSE = openapi.Schema(type='object', description='Done.', example={'a': 1})\n"
    assert _codes(source) == []
