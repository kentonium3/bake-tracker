# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Seasonal Baking Tracker - Desktop application for managing holiday baking inventory, recipes, and gift package planning. Built for a single user (developer's wife) with aspirations toward web deployment.

## Technology Stack

- **Python 3.10+** (minimum for type hints)
- **CustomTkinter** - Modern UI framework
- **SQLite** with WAL mode - Local database
- **SQLAlchemy 2.x** - ORM with type safety
- **pytest** - Testing framework

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run application
python src/main.py

# Testing
pytest src/tests -v                           # Run all tests
pytest src/tests -v --cov=src                 # With coverage
pytest src/tests/test_specific.py -v          # Single test file
pytest src/tests -v -k "test_name"            # Single test by name

# Code quality
black src/                                     # Format
flake8 src/                                    # Lint
mypy src/                                      # Type check
```

## Project Structure

```
src/
  models/       # SQLAlchemy database models
  services/     # Business logic layer (FIFO, calculations, etc.)
  ui/           # CustomTkinter UI components
  utils/        # Helpers and utilities
  tests/        # pytest test suite
kitty-specs/    # Feature specifications (Spec-Kitty workflow)
  NNN-feature/
    spec.md     # Feature specification
    plan.md     # Implementation plan
    tasks.md    # Task tracking
    tasks/      # Individual work packages (planned/doing/done)
docs/           # Documentation
.kittify/       # Spec-Kitty templates and constitution
```

## Architecture (NON-NEGOTIABLE)

**Layered architecture with strict dependency flow: UI -> Services -> Models -> Database**

- UI layer (`src/ui/`) must NOT contain business logic
- Services layer (`src/services/`) must NOT import UI components
- Models layer (`src/models/`) defines schema and relationships only
- Cross-layer dependencies flow downward only

## Core Principles

1. **FIFO Accuracy**: First In, First Out consumption must be enforced for pantry items. Cost calculations must reflect actual pantry consumption.

2. **User-Centric Design**: The primary user is non-technical. UI must be intuitive. Features must solve actual problems, not theoretical ones.

3. **Test-Driven Development**: Service layer must have >70% test coverage. Unit tests for all service methods. Tests cover happy path, edge cases, and errors.

4. **Future-Proof Schema**: Database includes nullable industry-standard fields (FoodOn, GTIN) for future expansion, but only essential fields are populated now.

5. **Migration Safety**: Database migrations must support dry-run mode, preserve all data with validation, and have documented rollback plans.

## Development Workflow (Spec-Kitty)

Features follow a documentation-first workflow:

1. `/spec-kitty.specify` - Create feature spec in `kitty-specs/`
2. `/spec-kitty.plan` - Research and plan implementation
3. `/spec-kitty.tasks` - Generate atomic task prompts
4. `/spec-kitty.implement` - Execute with TDD
5. `/spec-kitty.review` - Validate against acceptance criteria
6. `/spec-kitty.accept` - Full acceptance checks
7. `/spec-kitty.merge` - Merge and cleanup

## Agent Rules

- **Paths**: Always use exact paths relative to project root or absolute paths
- **Encoding**: UTF-8 only. Avoid Windows-1252 smart quotes (" " ' '). Use standard ASCII quotes.
- **Git**: Descriptive commit messages in imperative mood. Never commit secrets.
- **Context**: Read `plan.md`, `tasks.md`, and relevant artifacts at session start

## Spec-Kitty Workflow Compliance (NON-NEGOTIABLE)

This project uses spec-kitty for feature development. The workflow is AUTHORITATIVE.

**STOP and ask the user if:**
- A `/spec-kitty.*` command fails or errors
- Task lane transitions don't work as expected
- Acceptance checks fail
- Any workflow step produces unexpected results

**NEVER manually:**
- Move files between `planned/`, `doing/`, `for_review/`, `done/` directories
- Edit task frontmatter fields (`lane`, `review_status`, `assignee`, etc.)
- Run `git worktree` commands outside of `/spec-kitty.merge`
- "Fix" git state to make acceptance pass
- Simulate what a workflow command "should have done"

**The correct response to workflow issues is to STOP and report, not to work around.**

## Key Design Decisions

- **Ingredients vs Products**: Recipes reference generic Ingredients; Inventory holds specific Products (brands/packages). This enables recipe sharing and brand flexibility.
- **Slug-based FKs**: Use slugs instead of display names for foreign keys (enables future localization)
- **UUID support**: BaseModel includes UUID for future distributed/multi-user scenarios
- **Nested Recipes**: Recipes can include other recipes as components via RecipeComponent junction table. Maximum 3 levels of nesting. Circular references are prevented at validation time. Shopping lists aggregate ingredients from all levels.
- **Event-Centric Production Model**: ProductionRun and AssemblyRun link to Events via optional `event_id` FK. This enables: (1) tracking which production is for which event, (2) explicit production targets per event via EventProductionTarget/EventAssemblyTarget, (3) progress tracking (produced vs target), (4) package fulfillment status workflow (pending/ready/delivered). See `docs/design/schema_v0.6_design.md`.
