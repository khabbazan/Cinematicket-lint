"""End-to-end tests for the cinematicket-lint command line entry point."""

import sys
import textwrap
from pathlib import Path

import pytest

from cinematicket_lint import cli

_ROOT = Path(__file__).resolve().parent.parent


def _write(path: Path, text: str) -> Path:
    """"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding='utf-8')
    return path


def _run(monkeypatch, capsys, cwd: Path, arguments: list[str]) -> tuple[int, list[str]]:
    """"""
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, 'argv', ['cinematicket-lint', *arguments])
    exit_code = cli.main()
    output = capsys.readouterr().out
    return exit_code, [line for line in output.splitlines() if line]


def test_exits_zero_and_prints_nothing_for_a_clean_file(monkeypatch, capsys, tmp_path):
    """"""
    clean = _write(tmp_path / 'clean.py', '"""Doc."""\n\nVALUE = 1\n')
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(clean)])
    assert exit_code == 0
    assert lines == []


def test_exits_one_and_prints_violations_in_path_line_code_format(monkeypatch, capsys, tmp_path):
    """"""
    dirty = _write(tmp_path / 'dirty.py', 'def foo():\n    return 1\n')
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(dirty)])
    assert exit_code == 1
    assert any(line.startswith(f'{dirty}:1: CT09 ') for line in lines)


def test_checks_every_file_given_on_the_command_line(monkeypatch, capsys, tmp_path):
    """"""
    first = _write(tmp_path / 'first.py', "app_name = 'x'\n")
    second = _write(tmp_path / 'second.py', "app_name = 'y'\n")
    _, lines = _run(monkeypatch, capsys, tmp_path, [str(first), str(second)])
    assert sum('CT12' in line for line in lines) == 2


def test_ignores_files_that_are_not_python(monkeypatch, capsys, tmp_path):
    """"""
    text = _write(tmp_path / 'notes.txt', 'def foo():\n    return 1\n')
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(text)])
    assert (exit_code, lines) == (0, [])


def test_skips_files_with_a_syntax_error(monkeypatch, capsys, tmp_path):
    """"""
    broken = _write(tmp_path / 'broken.py', 'def foo(:\n')
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(broken)])
    assert (exit_code, lines) == (0, [])


def test_skips_excluded_files(monkeypatch, capsys, tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["migrations"]\n')
    migration = _write(tmp_path / 'app' / 'migrations' / '0001.py', "app_name = 'x'\n")
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(migration)])
    assert (exit_code, lines) == (0, [])


def test_without_arguments_it_walks_the_include_directories(monkeypatch, capsys, tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["pkg"]\n')
    _write(tmp_path / 'pkg' / 'a.py', "app_name = 'x'\n")
    _write(tmp_path / 'other' / 'b.py', "app_name = 'x'\n")
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [])
    assert exit_code == 1
    assert len(lines) == 1
    assert 'pkg' in lines[0]


def test_without_arguments_and_without_include_it_checks_nothing(monkeypatch, capsys, tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["x"]\n')
    _write(tmp_path / 'pkg' / 'a.py', "app_name = 'x'\n")
    assert _run(monkeypatch, capsys, tmp_path, []) == (0, [])


def test_include_is_ignored_when_files_are_passed(monkeypatch, capsys, tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["pkg"]\n')
    other = _write(tmp_path / 'other' / 'b.py', "app_name = 'x'\n")
    exit_code, lines = _run(monkeypatch, capsys, tmp_path, [str(other)])
    assert exit_code == 1
    assert 'CT12' in lines[0]


def test_inline_suppression_removes_a_violation(monkeypatch, capsys, tmp_path):
    """"""
    suppressed = _write(tmp_path / 'ok.py', "app_name = 'x'  # ctlint: CT12\n")
    assert _run(monkeypatch, capsys, tmp_path, [str(suppressed)]) == (0, [])


def test_file_wide_suppression_removes_a_violation(monkeypatch, capsys, tmp_path):
    """"""
    suppressed = _write(tmp_path / 'ok.py', "# ctlint: CT12\napp_name = 'x'\nother = 'y'\n")
    assert _run(monkeypatch, capsys, tmp_path, [str(suppressed)]) == (0, [])


@pytest.mark.parametrize(
    ('table', 'source'),
    [
        ('name_length', 'def a_function() -> None:\n    x = 1\n'),
        ('bad_names', 'foo = 1\n'),
        ('module_constant_naming', "app_name = 'x'\n"),
        ('keyword_before_vararg', 'def func(first: int = 1, *args: int) -> None:\n    pass\n'),
        ('instance_attribute_count', 'class A:\n    def __init__(self) -> None:\n        self.a1 = self.a2 = 1\n'),
        ('attribute_outside_init', 'class A:\n    def run(self) -> None:\n        self.a1 = 1\n'),
        ('local_variable_count', 'def func(first: int, second: int) -> None:\n    pass\n'),
        ('module_line_count', 'VALUE = 1\nOTHER = 2\n'),
        ('redefined_outer_name', 'VALUE = 1\n\ndef func(VALUE: int) -> None:\n    pass\n'),
    ],
)
def test_every_configurable_rule_can_be_disabled(monkeypatch, capsys, tmp_path, table, source):
    """"""
    limits = {
        'instance_attribute_count': 'max = 1\n',
        'local_variable_count': 'max = 1\n',
        'module_line_count': 'max = 1\n',
    }
    enabled_config = f'[tool.cinematicket_lint.{table}]\n{limits.get(table, "")}'
    target = _write(tmp_path / 'sample.py', source)

    _write(tmp_path / 'pyproject.toml', enabled_config)
    _, with_rule = _run(monkeypatch, capsys, tmp_path, [str(target)])
    _write(tmp_path / 'pyproject.toml', enabled_config + 'enabled = false\n')
    _, without_rule = _run(monkeypatch, capsys, tmp_path, [str(target)])

    new_codes = {line.split(': ')[1].split(' ')[0] for line in with_rule} - {
        line.split(': ')[1].split(' ')[0] for line in without_rule
    }
    assert len(new_codes) == 1
    assert next(iter(new_codes)).startswith('CT')


def test_every_rule_code_fires_on_one_file(monkeypatch, capsys, tmp_path):
    """"""
    source = """\
        from drf_yasg import openapi
        from pydantic import BaseModel
        total = 1 + \\
            2
        app_name = 'x'
        RESPONSE = openapi.Schema(type='object')
        BODY = openapi.Schema(type='object', description='No period')


        class Model(BaseModel):
            name: str | None


        def foo(a, b=1, *args):
            first = compute()
            return first


        class Many:
            def run(self):
                self.a1 = 1
                self.a2 = 2


        def shadow(app_name: str) -> None:
            pass


        def test_something() -> None:
            pass
        """
    _write(
        tmp_path / 'pyproject.toml',
        '[tool.cinematicket_lint.instance_attribute_count]\nmax = 1\n'
        '[tool.cinematicket_lint.local_variable_count]\nmax = 1\n'
        '[tool.cinematicket_lint.module_line_count]\nmax = 5\n',
    )
    target = _write(tmp_path / 'test_sample.py', source)
    _, lines = _run(monkeypatch, capsys, tmp_path, [str(target)])
    codes = {line.split(': ')[1].split(' ')[0] for line in lines}
    expected = {f'CT{number:02d}' for number in range(1, 19)}
    assert expected <= codes, sorted(expected - codes)


def test_ct07_fires_for_test_files_with_a_bad_test_name(monkeypatch, capsys, tmp_path):
    """"""
    target = _write(tmp_path / 'test_sample.py', 'def test_something() -> None:\n    pass\n')
    _, lines = _run(monkeypatch, capsys, tmp_path, [str(target)])
    assert any('CT07' in line for line in lines)


def test_pre_commit_hook_definition_points_at_the_entry_point():
    """"""
    hooks = (_ROOT / '.pre-commit-hooks.yaml').read_text(encoding='utf-8')
    assert 'id: cinematicket-lint' in hooks
    assert 'entry: cinematicket-lint' in hooks
    assert 'python' in hooks


def test_console_script_points_at_cli_main():
    """"""
    pyproject = (_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'cinematicket-lint = "cinematicket_lint.cli:main"' in pyproject
