# CinemaTicket-linter

A [pre-commit](https://pre-commit.com) hook with AST-based checks for code-style rules that [ruff](https://docs.astral.sh/ruff/) and [pylint](https://pylint.readthedocs.io/) can't express. Seven checks, `CT01`–`CT07`.

## Usage

Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/khabbazan/CinemaTicket-linter
    rev: v0.1.0
    hooks:
      - id: cinematicket-lint
```

## Checks

| Code | Checks for |
|---|---|
| `CT01` | Backslash line continuation outside brackets (e.g. `total = 1 + \`). Complements ruff's `E502`, which only flags a *redundant* backslash inside an already-open bracket. |
| `CT02` | A local variable assigned without a type annotation, where the right-hand side is neither a class constructor call (`SomeClass(...)`, PascalCase target) nor a literal data-type initialization (`()`, `[]`, `''`, `""`, `{}`, a set literal, an f-string, or a number/bool/`None` constant). |
| `CT03` | A pydantic `BaseModel` / `@dataclass` field typed `Optional[X]` or `X \| None` with no default value. |
| `CT04` | A `drf_yasg` `openapi.Schema(...)` / `openapi.Parameter(...)` call missing `example=`. |
| `CT05` | Same call, missing `description=`. |
| `CT06` | Same call, `description=` present but doesn't end with a period. |
| `CT07` | In `test_*.py` files, a `def test_*` function whose name doesn't match `test_(success\|failure)_`. |

## Suppressing a check

Add `# CTXX` as a trailing comment on the violating line:

```python
value = compute()  # CT02
```

Or on the file's first line to suppress that check for the whole file:

```python
# CT02
"""Module docstring."""
```

## Local development

```bash
pip install -e .
cinematicket-lint path/to/file.py
```

## License

MIT
