"""Tests for the per-rule configuration plumbing and the CLI wiring."""

import sys
import textwrap

from cinematicket_lint import cli
from cinematicket_lint.config import load_config, resolve_options


def test_resolve_options_returns_defaults_without_overrides():
    """"""
    assert resolve_options({'max': 7}, None) == {'max': 7}


def test_resolve_options_lets_overrides_win_and_keeps_other_defaults():
    """"""
    assert resolve_options({'max': 7, 'names': ['a']}, {'max': 3}) == {'max': 3, 'names': ['a']}


def test_load_config_reads_per_rule_tables(tmp_path):
    """"""
    (tmp_path / 'pyproject.toml').write_text(
        textwrap.dedent(
            """
            [tool.cinematicket_lint]
            include = ["pkg"]

            [tool.cinematicket_lint.max_locals]
            max = 3
            """
        )
    )
    config = load_config(tmp_path)
    assert config['include'] == ['pkg']
    assert config['max_locals'] == {'max': 3}


def test_load_config_is_empty_without_a_pyproject(tmp_path):
    """"""
    assert load_config(tmp_path / 'missing') == {}


def _run_cli(monkeypatch, capsys, tmp_path, pyproject: str, source: str) -> tuple[int, str]:
    """"""
    (tmp_path / 'pyproject.toml').write_text(textwrap.dedent(pyproject))
    target = tmp_path / 'sample.py'
    target.write_text(textwrap.dedent(source))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['cinematicket-lint', str(target)])
    exit_code = cli.main()
    return exit_code, capsys.readouterr().out


def test_cli_runs_new_rules_by_default(monkeypatch, capsys, tmp_path):
    """"""
    exit_code, output = _run_cli(monkeypatch, capsys, tmp_path, '', "app_name = 'x'\n")
    assert exit_code == 1
    assert 'CT12' in output


def test_cli_disables_a_rule_with_enabled_false(monkeypatch, capsys, tmp_path):
    """"""
    pyproject = """
        [tool.cinematicket_lint.module_constant_naming]
        enabled = false
        """
    exit_code, output = _run_cli(monkeypatch, capsys, tmp_path, pyproject, "app_name = 'x'\n")
    assert 'CT12' not in output


def test_cli_passes_rule_options_to_the_check(monkeypatch, capsys, tmp_path):
    """"""
    pyproject = """
        [tool.cinematicket_lint.module_constant_naming]
        allowed_names = ["app_name"]
        """
    _, output = _run_cli(monkeypatch, capsys, tmp_path, pyproject, "app_name = 'x'\n")
    assert 'CT12' not in output


def test_cli_reports_every_new_rule_code(monkeypatch, capsys, tmp_path):
    """"""
    source = (
        'import os\n'
        "app_name = 'x'\n"
        'def foo(os, a=1, *args):\n'
        '    x = 1\n'
        'class Many:\n'
        '    def run(self):\n' + ''.join(f'        self.attr{index} = 1\n' for index in range(8))
    )
    pyproject = """
        [tool.cinematicket_lint.module_line_count]
        max = 5
        """
    _, output = _run_cli(monkeypatch, capsys, tmp_path, pyproject, source)
    for code in ('CT10', 'CT11', 'CT12', 'CT13', 'CT14', 'CT15', 'CT17', 'CT18'):
        assert code in output, code


def test_cli_inline_suppression_works_for_new_rules(monkeypatch, capsys, tmp_path):
    """"""
    _, output = _run_cli(monkeypatch, capsys, tmp_path, '', "app_name = 'x'  # ctlint: CT12\n")
    assert 'CT12' not in output
