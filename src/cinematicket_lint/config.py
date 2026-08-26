"""Loads [tool.cinematicket_lint] exclude config from pyproject.toml.

Exclude entries are plain directory/file names (not glob patterns) that
are matched against every path component, e.g. "migrations" skips any
path with a "migrations" directory anywhere in it.
"""

import tomllib
from pathlib import Path


def load_exclude_names(start: Path) -> list[str]:
    config_path = _find_pyproject_toml(start)
    if config_path is None:
        return []
    with config_path.open('rb') as config_file:
        data = tomllib.load(config_file)
    return data.get('tool', {}).get('cinematicket_lint', {}).get('exclude', [])


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
