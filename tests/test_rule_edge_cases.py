"""Edge-case scenarios across the annotation, naming and structure rules."""

import ast
import textwrap
from pathlib import Path

from cinematicket_lint import (
    check_attribute_outside_init,
    check_bad_names,
    check_instance_attribute_count,
    check_keyword_before_vararg,
    check_local_variable_count,
    check_module_constant_naming,
    check_name_length,
    check_optional_default,
    check_parameter_annotation,
    check_redefined_outer_name,
    check_return_annotation,
    check_test_prefix,
    check_variable_annotation,
)


def _names(module, source: str, options: dict | None = None, filename: str = 'fake.py') -> list[str]:
    """"""
    tree = ast.parse(textwrap.dedent(source))
    if module in (
        check_parameter_annotation,
        check_return_annotation,
        check_variable_annotation,
        check_optional_default,
        check_test_prefix,
        check_keyword_before_vararg,
    ):
        violations = module.check(Path(filename), tree)
    else:
        violations = module.check(Path(filename), tree, options)
    return [
        violation.message.split("'")[1] if "'" in violation.message else violation.message for violation in violations
    ]


# --- CT02: variable annotation -------------------------------------------------------------


def test_ct02_flags_inside_async_functions():
    """"""
    assert _names(check_variable_annotation, 'async def f() -> None:\n    value = compute()\n') == ['value']


def test_ct02_flags_inside_methods():
    """"""
    source = 'class A:\n    def run(self) -> None:\n        value = compute()\n'
    assert _names(check_variable_annotation, source) == ['value']


def test_ct02_flags_a_call_on_a_lowercase_name():
    """"""
    assert _names(check_variable_annotation, 'def f() -> None:\n    value = make_thing()\n') == ['value']


def test_ct02_exempts_a_pascal_case_attribute_call():
    """"""
    assert _names(check_variable_annotation, 'def f() -> None:\n    value = module.Thing()\n') == []


def test_ct02_flags_a_lowercase_attribute_call():
    """"""
    assert _names(check_variable_annotation, 'def f() -> None:\n    value = module.make()\n') == ['value']


def test_ct02_exempts_every_literal_kind():
    """"""
    source = (
        'def f() -> None:\n'
        '    a = 1\n    b = 1.5\n    c = "s"\n    d = b"b"\n    e = True\n    g = None\n'
        '    h = []\n    i = ()\n    j = {}\n    k = {1}\n    ll = f"{a}"\n'
    )
    assert _names(check_variable_annotation, source) == []


def test_ct02_exempts_a_negative_number_literal():
    """"""
    assert _names(check_variable_annotation, 'def f() -> None:\n    offset = -1\n') == []


def test_ct02_flags_comprehensions_and_conditionals():
    """"""
    source = 'def f(items, flag) -> None:\n    doubled = [i * 2 for i in items]\n    pick = 1 if flag else 2\n'
    assert _names(check_variable_annotation, source) == ['doubled', 'pick']


def test_ct02_ignores_tuple_unpacking_and_attribute_targets():
    """"""
    source = (
        'def f(obj) -> None:\n    first, second = compute()\n    obj.value = compute()\n    obj["key"] = compute()\n'
    )
    assert _names(check_variable_annotation, source) == []


def test_ct02_ignores_chained_assignment_and_augmented_assignment():
    """"""
    source = 'def f() -> None:\n    first = second = compute()\n    count: int = 0\n    count += compute()\n'
    assert _names(check_variable_annotation, source) == []


def test_ct02_ignores_module_level_and_class_level_assignments():
    """"""
    assert _names(check_variable_annotation, 'value = compute()\nclass A:\n    attr = compute()\n') == []


def test_ct02_checks_nested_functions_separately():
    """"""
    source = 'def outer() -> None:\n    def inner() -> None:\n        value = compute()\n'
    assert _names(check_variable_annotation, source) == ['value']


def test_ct02_sees_inside_try_with_for_while_blocks():
    """"""
    source = (
        'def f(items) -> None:\n'
        '    try:\n        first = compute()\n    except ValueError:\n        second = compute()\n'
        '    finally:\n        third = compute()\n'
        '    with open("f") as handle:\n        fourth = compute()\n'
        '    for item in items:\n        fifth = compute()\n'
        '    while items:\n        sixth = compute()\n'
    )
    assert sorted(_names(check_variable_annotation, source)) == ['fifth', 'first', 'fourth', 'second', 'sixth', 'third']


def test_ct02_does_not_enter_class_bodies_inside_functions():
    """"""
    source = 'def f() -> None:\n    class Inner:\n        attr = compute()\n'
    assert _names(check_variable_annotation, source) == []


# --- CT03: optional default ----------------------------------------------------------------


def test_ct03_flags_typing_qualified_optional():
    """"""
    assert _names(check_optional_default, 'class M(BaseModel):\n    name: typing.Optional[str]\n') == ['name']


def test_ct03_flags_none_first_union():
    """"""
    assert _names(check_optional_default, 'class M(BaseModel):\n    name: None | str\n') == ['name']


def test_ct03_exempts_non_optional_unions_and_generics():
    """"""
    source = 'class M(BaseModel):\n    a: str | int\n    b: list[str]\n    c: dict[str, int | None]\n'
    assert _names(check_optional_default, source) == []


def test_ct03_exempts_fields_with_field_defaults():
    """"""
    assert _names(check_optional_default, 'class M(BaseModel):\n    name: str | None = Field(default=None)\n') == []


def test_ct03_ignores_methods_and_plain_assignments_in_the_model():
    """"""
    source = 'class M(BaseModel):\n    x = 1\n\n    def method(self) -> None:\n        value: str | None\n'
    assert _names(check_optional_default, source) == []


def test_ct03_flags_a_model_nested_in_another_class():
    """"""
    source = 'class Outer:\n    class Inner(BaseModel):\n        name: str | None\n'
    assert _names(check_optional_default, source) == ['name']


def test_ct03_flags_a_model_with_several_bases():
    """"""
    assert _names(check_optional_default, 'class M(Mixin, BaseModel):\n    name: str | None\n') == ['name']


# --- CT07: test names ----------------------------------------------------------------------


def test_ct07_accepts_valid_names_in_test_files():
    """"""
    source = 'def test_success(): pass\ndef test_failure_x(): pass\ndef test_success_a_b(): pass\n'
    assert _names(check_test_prefix, source, filename='test_a.py') == []


def test_ct07_flags_near_miss_names():
    """"""
    source = 'def test_successful(): pass\ndef test_Success(): pass\ndef test_fail(): pass\ndef test_(): pass\n'
    assert _names(check_test_prefix, source, filename='test_a.py') == [
        'test_successful',
        'test_Success',
        'test_fail',
        'test_',
    ]


def test_ct07_checks_async_and_method_tests():
    """"""
    source = 'async def test_bad(): pass\nclass T:\n    def test_other(self): pass\n'
    assert _names(check_test_prefix, source, filename='test_a.py') == ['test_bad', 'test_other']


def test_ct07_ignores_helpers_without_the_test_prefix():
    """"""
    assert _names(check_test_prefix, 'def helper(): pass\ndef make_test_data(): pass\n', filename='test_a.py') == []


def test_ct07_is_limited_to_files_named_test_star():
    """"""
    assert _names(check_test_prefix, 'def test_bad(): pass\n', filename='pytest_a.py') == []
    assert _names(check_test_prefix, 'def test_bad(): pass\n', filename='helpers.py') == []


# --- CT08 / CT09: annotations --------------------------------------------------------------


def test_ct08_flags_defaulted_parameters_without_annotation():
    """"""
    assert _names(check_parameter_annotation, 'def f(a=1, *, b=2) -> None: pass\n') == ['a', 'b']


def test_ct08_checks_async_methods_and_nested_functions():
    """"""
    source = 'class A:\n    async def run(self, a) -> None:\n        def inner(b) -> None: pass\n'
    assert _names(check_parameter_annotation, source) == ['a', 'b']


def test_ct08_does_not_check_lambdas():
    """"""
    assert _names(check_parameter_annotation, 'handler = lambda x: x\n') == []


def test_ct08_accepts_annotated_star_arguments():
    """"""
    assert _names(check_parameter_annotation, 'def f(*args: int, **kwargs: str) -> None: pass\n') == []


def test_ct09_flags_async_nested_and_private_functions():
    """"""
    source = 'async def a(): pass\ndef b():\n    def c(): pass\ndef _d(): pass\n'
    assert sorted(_names(check_return_annotation, source)) == ['_d', 'a', 'b', 'c']


def test_ct09_exempts_all_dunder_methods():
    """"""
    source = 'class A:\n    def __init__(self): pass\n    def __repr__(self): pass\n    def __enter__(self): pass\n'
    assert _names(check_return_annotation, source) == []


def test_ct09_flags_a_name_that_only_looks_like_a_dunder():
    """"""
    assert _names(check_return_annotation, 'def __partial(): pass\ndef trailing__(): pass\n') == [
        '__partial',
        'trailing__',
    ]


def test_ct09_exempts_test_names_in_any_file():
    """"""
    assert _names(check_return_annotation, 'def test_success_case(): pass\n', filename='module.py') == []


def test_ct09_accepts_none_and_complex_return_annotations():
    """"""
    source = 'def a() -> None: pass\ndef b() -> dict[str, list[int]] | None: pass\ndef c() -> "Forward": pass\n'
    assert _names(check_return_annotation, source) == []


# --- CT10 / CT11 ---------------------------------------------------------------------------


def test_ct10_ignores_comprehension_variables_in_every_form():
    """"""
    source = 'def f(items) -> None:\n    [i for i in items]\n    {i for i in items}\n    {i: j for i, j in items}\n    (i for i in items)\n'
    assert _names(check_name_length, source) == []


def test_ct10_does_not_flag_lambda_parameters():
    """"""
    assert _names(check_name_length, 'def f() -> None:\n    handler = lambda x: x\n') == []


def test_ct10_flags_a_name_bound_by_an_import_alias_inside_a_function():
    """"""
    assert _names(check_name_length, 'def f() -> None:\n    import numpy as n\n') == ['n']


def test_ct10_flags_a_nested_function_name_that_is_too_short():
    """"""
    assert _names(check_name_length, 'def f() -> None:\n    def g() -> None: pass\n') == ['g']


def test_ct10_flags_uppercase_local_names_against_the_default_pattern():
    """"""
    assert _names(check_name_length, 'def f() -> None:\n    LOCAL = 1\n') == ['LOCAL']


def test_ct10_exempts_names_declared_nonlocal():
    """"""
    source = 'def f() -> None:\n    x = 1\n    def inner() -> None:\n        nonlocal x\n        x = 2\n'
    assert _names(check_name_length, source) == ['x']


def test_ct11_flags_names_in_every_binding_position():
    """"""
    source = 'import foo\nclass bar: pass\ndef baz(toto): tutu = 1\n'
    assert _names(check_bad_names, source) == ['bar', 'baz', 'toto', 'tutu']


def test_ct11_matches_names_exactly():
    """"""
    assert _names(check_bad_names, 'Foo = 1\nfoo2 = 2\n_foo = 3\n') == []


# --- CT12 ----------------------------------------------------------------------------------


def test_ct12_accepts_private_and_numbered_upper_case_names():
    """"""
    assert _names(check_module_constant_naming, '_PRIVATE = 1\nVALUE_2 = 2\n__DOUBLE = 3\n') == []


def test_ct12_flags_a_lower_case_string_constant_after_an_import():
    """"""
    assert _names(check_module_constant_naming, "import os\nname = 'x'\n") == ['name']


def test_ct12_flags_a_lower_case_none_constant():
    """"""
    assert _names(check_module_constant_naming, 'cache = None\n') == ['cache']


def test_ct12_exempts_a_class_alias_assignment():
    """"""
    assert _names(check_module_constant_naming, 'Alias = SomeClass\n') == []


def test_ct12_flags_a_pascal_case_name_assigned_a_literal():
    """"""
    assert _names(check_module_constant_naming, 'Limit = 3\n') == ['Limit']


# --- CT13 ----------------------------------------------------------------------------------


def test_ct13_exempts_lambdas_and_keyword_only_defaults():
    """"""
    assert _names(check_keyword_before_vararg, 'handler = lambda a=1, *args: a\ndef f(*args, a=1): pass\n') == []


def test_ct13_flags_nested_functions():
    """"""
    assert _names(check_keyword_before_vararg, 'def outer():\n    def inner(a=1, *args): pass\n') == ['inner']


# --- CT14 / CT15 ---------------------------------------------------------------------------


def test_ct14_counts_augmented_assignments_as_the_same_attribute():
    """"""
    source = 'class A:\n    def __init__(self) -> None:\n        self.a = 0\n    def bump(self) -> None:\n        self.a += 1\n'
    assert _names(check_instance_attribute_count, source, {'max': 1}) == []


def test_ct14_counts_assignments_inside_nested_blocks():
    """"""
    source = (
        'class A:\n    def run(self, flag) -> None:\n'
        '        if flag:\n            self.a = 1\n        else:\n            self.b = 2\n'
        '        try:\n            self.c = 3\n        except ValueError:\n            self.d = 4\n'
    )
    assert _names(check_instance_attribute_count, source, {'max': 3}) == ['A']


def test_ct14_ignores_static_methods():
    """"""
    source = 'class A:\n    @staticmethod\n    def build(a) -> None:\n        a.x = 1\n        a.y = 2\n'
    assert _names(check_instance_attribute_count, source, {'max': 1}) == []


def test_ct15_skips_a_class_whose_base_is_a_dotted_name():
    """"""
    source = 'class A(module.Base):\n    def run(self) -> None:\n        self.x = 1\n'
    assert _names(check_attribute_outside_init, source) == []


def test_ct15_follows_a_chain_of_local_bases():
    """"""
    source = (
        'class A:\n    def __init__(self) -> None:\n        self.x = 1\n'
        'class B(A):\n    pass\n'
        'class C(B):\n    def run(self) -> None:\n        self.x = 2\n        self.y = 3\n'
    )
    assert _names(check_attribute_outside_init, source) == ['y']


def test_ct15_survives_inheritance_cycles():
    """"""
    source = 'class A(B):\n    def run(self) -> None:\n        self.x = 1\nclass B(A):\n    pass\n'
    assert _names(check_attribute_outside_init, source) == []


def test_ct15_treats_methods_and_nested_classes_as_defined_names():
    """"""
    source = 'class A:\n    def helper(self) -> None: pass\n    def run(self) -> None:\n        self.helper = None\n'
    assert _names(check_attribute_outside_init, source) == []


# --- CT16 / CT18 ---------------------------------------------------------------------------


def test_ct16_counts_walrus_and_match_free_bindings():
    """"""
    source = 'def f(data) -> None:\n    if (first := data):\n        pass\n    if (second := data):\n        pass\n'
    assert _names(check_local_variable_count, source, {'max': 2}) == ['f']


def test_ct16_counts_a_decorated_nested_function_name_once():
    """"""
    source = 'def f() -> None:\n    @decorator\n    def inner() -> None: pass\n'
    assert _names(check_local_variable_count, source, {'max': 0}) == ['f']
    assert _names(check_local_variable_count, source, {'max': 1}) == []


def test_ct18_flags_every_assignment_style_of_the_module_name():
    """"""
    source = 'value = 1\ndef f() -> None:\n    value, other = 1, 2\n'
    assert _names(check_redefined_outer_name, source) == ['value']


def test_ct18_does_not_treat_names_bound_inside_other_blocks_as_module_level_functions():
    """"""
    source = 'def first() -> None:\n    helper = 1\ndef second() -> None:\n    helper = 2\n'
    assert _names(check_redefined_outer_name, source) == []


def test_ct18_flags_a_parameter_shadowing_a_conditionally_defined_name():
    """"""
    source = 'if True:\n    value = 1\ndef f(value) -> None: pass\n'
    assert _names(check_redefined_outer_name, source) == ['value']
