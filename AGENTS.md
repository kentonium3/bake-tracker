# Repository Guidelines

## Project Structure & Module Organization
- `src/` holds application code: `models/` (SQLAlchemy schema), `services/` (business logic), `ui/` (CustomTkinter), `utils/`, and `tests/` (pytest).
- `docs/` contains architecture, schema, and user docs; `kitty-specs/` stores feature specs and plans.
- `data/` is created at runtime for the local SQLite database; do not commit generated DB files.

## Build, Test, and Development Commands
- `python src/main.py` runs the desktop app locally.
- `dev.bat` (Windows) or `make` (Linux/Mac) provides shortcuts: `dev test` / `make test`, `dev lint` / `make lint`, `dev format` / `make format`.
- `./run-tests.sh` is preferred when working in git worktrees because it reuses the main repo venv.

## Coding Style & Naming Conventions
- Python 3.10+, PEP 8, 4-space indentation, max line length 100 (Black).
- Format with `black src/`, lint with `flake8 src/`, type-check with `mypy src/`.
- Naming: classes `PascalCase`, functions `snake_case`, constants `UPPER_SNAKE_CASE`, private members `_leading_underscore`.
- Public classes and methods should include docstrings and type hints where useful.

## Testing Guidelines
- Framework: `pytest` with configs in `pytest.ini` and `pyproject.toml`.
- Place tests in `src/tests/`, name files `test_*.py`, functions `test_*`.
- Coverage target: services should stay above 70% when feasible (`pytest --cov=src`).

## Commit & Pull Request Guidelines
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, etc.
- PRs should include a clear description, linked issue (if any), and screenshots for UI changes.
- Update docs when behavior changes (`README.md`, `docs/SCHEMA.md`, `CHANGELOG.md`).

## Architecture & Data Rules
- Respect layered dependencies: UI -> Services -> Models -> Database. Avoid UI logic in services.
- For multi-step service operations, pass a shared SQLAlchemy session to prevent detached objects.
