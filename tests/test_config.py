"""Tests for [tool.cinematicket_lint] loading, file discovery and exclusion."""

import textwrap
from pathlib import Path

from cinematicket_lint.config import (
    discover_files,
    is_excluded,
    load_config,
    load_exclude_names,
    load_include_dirs,
    resolve_options,
)


def _write(path: Path, text: str = '') -> Path:
    """"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding='utf-8')
    return path


def test_load_exclude_names_reads_the_exclude_list(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["migrations", "build"]\n')
    assert load_exclude_names(tmp_path) == ['migrations', 'build']


def test_load_include_dirs_reads_the_include_list(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["a", "b"]\n')
    assert load_include_dirs(tmp_path) == ['a', 'b']


def test_missing_pyproject_yields_empty_config(tmp_path):
    """"""
    assert load_exclude_names(tmp_path) == []
    assert load_include_dirs(tmp_path) == []
    assert load_config(tmp_path) == {}


def test_pyproject_without_the_table_yields_empty_config(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.ruff]\nline-length = 120\n')
    assert load_config(tmp_path) == {}
    assert load_exclude_names(tmp_path) == []


def test_config_is_found_by_walking_up_from_a_subdirectory(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["x"]\n')
    nested = tmp_path / 'a' / 'b'
    nested.mkdir(parents=True)
    assert load_exclude_names(nested) == ['x']


def test_config_is_found_when_the_start_is_a_file(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["x"]\n')
    source = _write(tmp_path / 'pkg' / 'module.py', 'x = 1\n')
    assert load_exclude_names(source) == ['x']


def test_the_nearest_pyproject_wins(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["outer"]\n')
    _write(tmp_path / 'inner' / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["inner"]\n')
    assert load_exclude_names(tmp_path / 'inner') == ['inner']


def test_load_config_returns_rule_tables_and_lists_together(tmp_path):
    """"""
    _write(
        tmp_path / 'pyproject.toml',
        """
        [tool.cinematicket_lint]
        include = ["pkg"]
        exclude = ["migrations"]

        [tool.cinematicket_lint.module_line_count]
        max = 5
        """,
    )
    config = load_config(tmp_path)
    assert config['include'] == ['pkg']
    assert config['exclude'] == ['migrations']
    assert config['module_line_count'] == {'max': 5}


def test_discover_files_walks_include_dirs_recursively_in_sorted_order(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["pkg"]\n')
    _write(tmp_path / 'pkg' / 'b.py')
    _write(tmp_path / 'pkg' / 'a.py')
    _write(tmp_path / 'pkg' / 'sub' / 'c.py')
    _write(tmp_path / 'pkg' / 'notes.txt')
    _write(tmp_path / 'other' / 'ignored.py')
    found = [path.relative_to(tmp_path).as_posix() for path in discover_files(tmp_path)]
    assert found == ['pkg/a.py', 'pkg/b.py', 'pkg/sub/c.py']


def test_discover_files_resolves_include_relative_to_the_pyproject(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["pkg"]\n')
    _write(tmp_path / 'pkg' / 'a.py')
    nested = tmp_path / 'pkg' / 'sub'
    nested.mkdir()
    found = [path.name for path in discover_files(nested)]
    assert found == ['a.py']


def test_discover_files_handles_several_include_dirs(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["one", "two"]\n')
    _write(tmp_path / 'one' / 'a.py')
    _write(tmp_path / 'two' / 'b.py')
    assert [path.name for path in discover_files(tmp_path)] == ['a.py', 'b.py']


def test_discover_files_is_empty_without_include(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\nexclude = ["x"]\n')
    _write(tmp_path / 'pkg' / 'a.py')
    assert discover_files(tmp_path) == []


def test_discover_files_is_empty_with_an_empty_include(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = []\n')
    _write(tmp_path / 'pkg' / 'a.py')
    assert discover_files(tmp_path) == []


def test_discover_files_is_empty_without_a_pyproject(tmp_path):
    """"""
    _write(tmp_path / 'pkg' / 'a.py')
    assert discover_files(tmp_path) == []


def test_discover_files_skips_include_dirs_that_do_not_exist(tmp_path):
    """"""
    _write(tmp_path / 'pyproject.toml', '[tool.cinematicket_lint]\ninclude = ["missing"]\n')
    assert discover_files(tmp_path) == []


def test_is_excluded_matches_a_directory_component_anywhere(tmp_path):
    """"""
    path = _write(tmp_path / 'app' / 'migrations' / '0001_initial.py')
    assert is_excluded(path, ['migrations']) is True


def test_is_excluded_matches_a_file_name(tmp_path):
    """"""
    path = _write(tmp_path / 'app' / 'settings.py')
    assert is_excluded(path, ['settings.py']) is True


def test_is_excluded_matches_a_glob_pattern(tmp_path):
    """"""
    path = _write(tmp_path / 'app' / 'generated_pb2.py')
    assert is_excluded(path, ['*_pb2.py']) is True


def test_is_excluded_does_not_match_a_partial_directory_name(tmp_path):
    """"""
    path = _write(tmp_path / 'app' / 'migrations_helpers' / 'tool.py')
    assert is_excluded(path, ['migrations']) is False


def test_is_excluded_is_false_without_exclude_names(tmp_path):
    """"""
    path = _write(tmp_path / 'app' / 'module.py')
    assert is_excluded(path, []) is False


def test_resolve_options_does_not_mutate_the_defaults():
    """"""
    defaults = {'max': 7}
    resolve_options(defaults, {'max': 3})
    assert defaults == {'max': 7}


def test_resolve_options_accepts_unknown_override_keys():
    """"""
    assert resolve_options({'max': 7}, {'extra': 1}) == {'max': 7, 'extra': 1}
