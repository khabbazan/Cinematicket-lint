"""Loads [tool.cinematicket_lint] config from pyproject.toml.

Exclude entries are plain directory/file names (not glob patterns) that
are matched against every path component, e.g. "migrations" skips any
path with a "migrations" directory anywhere in it.

Include entries are directories, relative to the pyproject.toml location,
that are walked for `.py` files when the CLI is invoked with no file
arguments (e.g. `include = ["advertising", "advertising_core"]`).
"""

import tomllib
from pathlib import Path


def load_exclude_names(start: Path) -> list[str]:
    return _load_config(start).get('exclude', [])


def load_include_dirs(start: Path) -> list[str]:
    return _load_config(start).get('include', [])


def discover_files(start: Path) -> list[Path]:
    config_path = _find_pyproject_toml(start)
    root = config_path.parent if config_path is not None else start
    include_dirs = load_include_dirs(start)
    files: list[Path] = []
    for include_dir in include_dirs:
        files.extend(sorted((root / include_dir).rglob('*.py')))
    return files


def _load_config(start: Path) -> dict:
    config_path = _find_pyproject_toml(start)
    if config_path is None:
        return {}
    with config_path.open('rb') as config_file:
        data = tomllib.load(config_file)
    return data.get('tool', {}).get('cinematicket_lint', {})


def _find_pyproject_toml(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_dir():
        search_from = current
    else:
        search_from = current.parent
    for directory in (search_from, *search_from.parents):
        candidate = directory / 'pyproject.toml'
        if candidate.is_file():
            return candidate
    return None


def is_excluded(path: Path, exclude_names: list[str]) -> bool:
    resolved = path.resolve()
    return any(name in resolved.parts or resolved.match(name) for name in exclude_names)
