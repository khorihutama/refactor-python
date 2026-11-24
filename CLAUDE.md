# Project & Refactoring Guidelines

## Environment & Tooling
- **Package Manager**: Always use `uv` (`uv run pytest`, `uv add`). Never use raw `pip` or `python`.
- **Linting & Formatting**: Run `uv run ruff check --fix . && uv run ruff format .` after every file edit.
- **Type Checking**: Run `uv run mypy --strict .` before finalizing any refactor. All new/modified functions must include full Python 3.11+ type hints.

## Refactoring Rules
- **One Pattern at a Time**: Never mix structural refactoring (e.g., extracting classes) with behavior changes or feature additions in the same step.
- **Keep Functions Small**: Target < 25 lines per function and cyclomatic complexity under 8.
- **Pythonic Simplifications**:
  - Replace nested `if/else` chains with early returns (guard clauses) or dispatch dictionaries.
  - Extract magic numbers and hardcoded strings into `Enum` classes or module-level `Final` constants.
  - Prefer `pathlib.Path` over `os.path`, and `dataclasses` / `pydantic` models over untyped dictionaries.
- **No Unsolicited Abstractions**: Do not introduce abstract base classes, factories, or singletons unless deduplicating 3+ concrete implementations.

## Goals
#### 1. Refactor into class-based / modular design, including:

- User management & quota control module
- Task data model
- Task executor (extensible)
- Scheduling system (simple implementation is fine)

#### 2. Support the following requirements:

- A single user can have multiple tasks simultaneously
- Task parameters should be configurable (e.g., via dictionary input)
- Task execution must include logging (use logging module)

#### 3. Optional extensions (if time allows):

- Support different action strategies (OOP design)
- Rewrite as an async execution version (optional)

## Verification & Git Workflow
- **Test-First Safety**: Before refactoring a module, verify existing `pytest` coverage. If coverage is missing, write characterization tests first to pin current behavior.
- **Stop on Failure**: If `mypy` or `pytest` fails after a change, fix or revert immediately before touching another file.
- **Atomic Commits**: Commit after each isolated refactoring step passes all checks.

## Do NOT
- NEVER read, inspect, grep, or output the contents of `.env` or `.env.*` files.
- Do not use bash commands (such as `cat`, `head`, `tail`, `grep`, or `echo`) to view environment variables or secret files.
- If you need to know which environment variables exist, read `.env.example` or ask the user directly instead.
- Never hardcode API keys, tokens, or secrets into code or logs.