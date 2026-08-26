# CinemaTicket-lint

A [pre-commit](https://pre-commit.com) hook with AST-based checks for code-style rules that [ruff](https://docs.astral.sh/ruff/) and [pylint](https://pylint.readthedocs.io/) can't express. Seven checks, `CT01`–`CT07`.

## Usage

Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/khabbazan/CinemaTicket-lint
    rev: v0.5.0
    hooks:
      - id: cinematicket-lint
```

## Scoping to directories

Add a `[tool.cinematicket_lint]` table to your project's `pyproject.toml` — same file, same idea as `[tool.ruff]`'s `exclude` and `[tool.pylint.MASTER]`'s `ignore`:

```toml
[tool.cinematicket_lint]
include = ["advertising", "advertising_core"]
exclude = ["migrations", "lint_eval_tmp"]
```

`exclude` entries are plain directory/file names, not glob patterns — a name matches if it appears as a path component anywhere in a checked file's path (so `"migrations"` skips `any/app/migrations/0001_initial.py`).

`include` entries are directories, relative to the `pyproject.toml` location, that get walked for every `.py` file **when the CLI is invoked with no file arguments** — e.g. `cinematicket-lint` on its own in a CI job, instead of `find advertising/ -name '*.py' | xargs cinematicket-lint`. `include` has no effect when file paths are passed on the command line (that's how pre-commit invokes the hook, so its behavior is unchanged).

`cinematicket-lint` looks for `pyproject.toml` starting from the current working directory and walking up. With no config found (or no `[tool.cinematicket_lint]` table), nothing is excluded and, with no file arguments, nothing is discovered either.

## Checks

| Code | Checks for |
|---|---|
| `CT01` | Backslash line continuation outside brackets (e.g. `total = 1 + \`). Complements ruff's `E502`, which only flags a *redundant* backslash inside an already-open bracket. |
| `CT02` | A local variable assigned without a type annotation, where the right-hand side is neither a class constructor call (`SomeClass(...)`, PascalCase target) nor a literal data-type initialization (`()`, `[]`, `''`, `""`, `{}`, a set literal, an f-string, or a number/bool/`None` constant). |
| `CT03` | A pydantic `BaseModel` / `@dataclass` field typed `Optional[X]` or `X \| None` with no default value. |
| `CT04` | A `drf_yasg` `openapi.Schema(...)` / `openapi.Parameter(...)` call assigned to a variable with `RESPONSE` (case-insensitive) in its name, missing `example=`. Request/other schemas are not required to have one. |
| `CT05` | Any `openapi.Schema(...)` / `openapi.Parameter(...)` call, regardless of variable name, missing `description=`. |
| `CT06` | Same call, `description=` present but doesn't end with a period. |
| `CT07` | In `test_*.py` files, a `def test_*` function whose name doesn't match `test_(success\|failure)_`. |

## Suppressing a check

Add `# ctlint: CTXX` as a trailing comment on the violating line (multiple codes may be comma-separated):

```python
value = compute()  # ctlint: CT02
```

Or on the file's first line to suppress that check for the whole file:

```python
# ctlint: CT02
"""Module docstring."""
```

## Local development

```bash
pip install -e .
cinematicket-lint path/to/file.py
```

## License

MIT
