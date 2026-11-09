# CinemaTicket-lint

A [pre-commit](https://pre-commit.com) hook with AST-based checks for code-style rules that [ruff](https://docs.astral.sh/ruff/) and [pylint](https://pylint.readthedocs.io/) can't express. Eighteen checks, `CT01`–`CT18`.

## Usage

Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/khabbazan/CinemaTicket-lint
    rev: <LATEST-VERSION>
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
| `CT02` | A local variable assigned without a type annotation, where the right-hand side is neither a class constructor call (`SomeClass(...)`, PascalCase target) nor a literal data-type initialization (`()`, `[]`, `''`, `""`, `{}`, a set literal, an f-string, or a number/bool/`None` constant), and the name hasn't already been annotated earlier in the same function (as a parameter, or via a prior `name: T = ...`) — checked anywhere in the function, including inside `if`/`for`/`while`/`try`/`with` blocks, but not inside a nested function/class. |
| `CT03` | A pydantic `BaseModel` field typed `Optional[X]` or `X \| None` with no default value. |
| `CT04` | A `drf_yasg` `openapi.Schema(...)` / `openapi.Parameter(...)` call assigned to a variable with `RESPONSE` (case-insensitive) in its name, missing `example=`. Request/other schemas are not required to have one. |
| `CT05` | Any `openapi.Schema(...)` / `openapi.Parameter(...)` call, regardless of variable name, missing `description=`. |
| `CT06` | Same call, `description=` present but doesn't end with a period. |
| `CT07` | In `test_*.py` files, a `def test_*` function whose name isn't `test_success`, `test_failure`, or one of those with a `_...` suffix. |
| `CT08` | A function/method parameter (positional, keyword-only) with no type annotation. `self`, `cls`, `*args`, and `**kwargs` are exempt. |
| `CT09` | A function/method with no return-type annotation. Exempt: `test_success[_...]` / `test_failure[_...]` functions, and dunder methods (`__init__`, `__str__`, ...). |
| `CT10` | A local variable or parameter name that doesn't match the naming pattern (default `^[a-z_][a-z0-9_]+$`, i.e. at least two characters). Comprehension variables, attributes and module-level names are not checked. |
| `CT11` | A variable, parameter, function, class or `except ... as` name from the disallowed list (default `foo`, `bar`, `baz`, `toto`, `tutu`, `tata`). |
| `CT12` | A module-level assignment of a constant value (literal, or arithmetic over literals) whose name isn't `UPPER_CASE`. Dunder names, PascalCase aliases and `allowed_names` are exempt. |
| `CT13` | A parameter with a default value placed before `*args`. |
| `CT14` | A class with more instance attributes (`self.x = ...` across all its methods) than the maximum (default 7). |
| `CT15` | An instance attribute defined only outside the defining methods (default `__init__`, `__new__`, `setUp`, `__post_init__`). Classes with a base that isn't defined in the same file are skipped. |
| `CT16` | A function with more local variables than the maximum (default 15). Parameters count, as they do in pylint; names declared `global`/`nonlocal`, comprehension variables and parameters matching `ignored_argument_pattern` don't. |
| `CT17` | A module with more lines than the maximum (default 1000). |
| `CT18` | A parameter or local variable that shadows a module-level name (variable, function, class or import). |

## Per-rule configuration

`CT10`–`CT18` are configured through one table each under `[tool.cinematicket_lint]`. Every table and every key is optional; omitted keys use the defaults shown. `enabled = false` turns a rule off.

```toml
[tool.cinematicket_lint.name_length]                # CT10
variable_pattern = '^[a-z_][a-z0-9_]+$'
argument_pattern = '^[a-z_][a-z0-9_]+$'
good_names = ["ex", "Run", "_", "pk"]

[tool.cinematicket_lint.bad_names]                  # CT11
names = ["foo", "bar", "baz", "toto", "tutu", "tata"]

[tool.cinematicket_lint.module_constant_naming]     # CT12
pattern = '^_*[A-Z][A-Z0-9_]*$'
allowed_names = []
only_constant_values = true                         # false: check every module-level assignment

[tool.cinematicket_lint.keyword_before_vararg]      # CT13
enabled = true

[tool.cinematicket_lint.instance_attribute_count]   # CT14
max = 7

[tool.cinematicket_lint.attribute_outside_init]     # CT15
defining_methods = ["__init__", "__new__", "setUp", "__post_init__"]

[tool.cinematicket_lint.local_variable_count]       # CT16
max = 15
ignored_argument_pattern = '_.*|^ignored_|^unused_'

[tool.cinematicket_lint.module_line_count]          # CT17
max = 1000

[tool.cinematicket_lint.redefined_outer_name]       # CT18
ignored_names = []
```

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

The hook is a Rust binary (pre-commit builds it with `cargo`, so a Rust toolchain must be installed).

```bash
cargo build --release
./target/release/cinematicket-lint path/to/file.py
```

## License

MIT
