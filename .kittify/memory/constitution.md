<!--
SYNC IMPACT REPORT
==================
Version change: 0.0.0 → 1.0.0 (MAJOR - initial ratification)
Modified principles: N/A (initial creation)
Added sections:
  - Core Principles (6 principles)
  - Quality Standards
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .kittify/templates/plan-template.md: ✅ already aligned (Constitution Check section exists)
  - .kittify/templates/spec-template.md: ✅ already aligned (user stories, requirements, success criteria)
  - .kittify/templates/tasks-template.md: ✅ already aligned (testing, work package structure)
Follow-up TODOs: None
-->

# Bake-Tracker Constitution

## Core Principles

### I. Layered Architecture (NON-NEGOTIABLE)

The codebase MUST follow strict layered architecture with unidirectional dependency flow:
**UI -> Services -> Models -> Database**

- UI layer (`src/ui/`) MUST NOT contain business logic
- Services layer (`src/services/`) MUST NOT import UI components
- Models layer (`src/models/`) defines schema and relationships only
- Cross-layer dependencies MUST flow downward only
- Violations require explicit justification in the Complexity Tracking section of plan.md

**Rationale**: Clean separation enables independent testing, future web migration, and prevents
tangled dependencies that make refactoring dangerous.

### II. Build for Today, Architect for Tomorrow

Make decisions that serve current needs without blocking future web migration.

- Current scope: Single-user desktop app (CustomTkinter + SQLite)
- Medium-term goal: Web app for friends/family to vet workflow and design
- MUST NOT prematurely optimize for multi-user or distributed scenarios
- MUST NOT introduce complexity for hypothetical future requirements
- SHOULD include lightweight future-proofing that costs nothing today:
  - UUID fields in models (already present via BaseModel)
  - Slug-based foreign keys (enables future localization)
  - Nullable industry-standard fields (FoodOn, GTIN) for future expansion
- Service layer MUST remain UI-agnostic (no CustomTkinter imports)

**Rationale**: The app will eventually migrate to web, but over-engineering now wastes effort
and adds maintenance burden. Keep the path open without walking it prematurely.

### III. FIFO Accuracy

First In, First Out consumption MUST be enforced for all pantry item usage.

- Pantry consumption calculations MUST reflect actual FIFO order
- Cost calculations MUST use the actual cost of consumed items, not averages
- Inventory queries MUST return items in acquisition order
- Tests MUST verify FIFO ordering with multi-batch scenarios

**Rationale**: Accurate cost tracking is a core value proposition. Users rely on cost data for
budgeting and gift package pricing decisions.

### IV. User-Centric Design

The primary user is non-technical. All features MUST prioritize intuitive usability.

- UI MUST be self-explanatory without documentation
- Error messages MUST use plain language, not technical jargon
- Features MUST solve actual user problems, not theoretical ones
- When in doubt, ask the user (developer's wife) before implementing
- Avoid feature creep: if the user didn't request it, don't build it

**Rationale**: This is a personal tool built for a specific person. Technical elegance that
sacrifices usability is a failure.

### V. Test-Driven Development

Service layer MUST maintain >70% test coverage. TDD is the expected workflow.

- Unit tests MUST exist for all service methods
- Tests MUST cover happy path, edge cases, and error conditions
- Red-Green-Refactor cycle SHOULD be followed for new features
- Contract tests for external dependencies (database, file I/O)
- Integration tests for multi-service workflows

**Rationale**: The service layer contains critical business logic (FIFO, cost calculations).
Untested changes risk data corruption and calculation errors.

### VI. Migration Safety

Database migrations MUST be safe and reversible.

- Migrations MUST support dry-run mode for validation
- All existing data MUST be preserved with explicit validation
- Rollback plans MUST be documented before execution
- Breaking schema changes require a migration plan in plan.md
- No raw SQL without ORM equivalent available

**Rationale**: User data (recipes, pantry history) is irreplaceable. A bad migration could
destroy years of baking history.

## Quality Standards

Code quality gates that all features MUST pass:

- **Formatting**: All code MUST pass `black` formatting
- **Linting**: All code MUST pass `flake8` with no errors
- **Type Safety**: All code MUST pass `mypy` type checking
- **Encoding**: UTF-8 only. No Windows-1252 smart quotes (" " ' ')
- **Commits**: Descriptive messages in imperative mood. Never commit secrets.
- **Paths**: Always use exact paths relative to project root or absolute paths

## Development Workflow

Features follow the Spec-Kitty documentation-first workflow:

1. `/spec-kitty.specify` - Create feature spec with user stories
2. `/spec-kitty.plan` - Research and design implementation
3. `/spec-kitty.tasks` - Generate atomic work packages
4. `/spec-kitty.implement` - Execute with TDD discipline
5. `/spec-kitty.review` - Validate against acceptance criteria
6. `/spec-kitty.accept` - Full acceptance verification
7. `/spec-kitty.merge` - Merge and cleanup

**Context Loading**: At session start, read `plan.md`, `tasks.md`, and relevant artifacts.

## Governance

This constitution supersedes all other development practices for the bake-tracker project.

### Amendment Process

1. Proposed amendments MUST be documented with rationale
2. Amendments MUST include migration guidance for in-flight features
3. Version increments follow semantic versioning:
   - MAJOR: Principle removals or incompatible redefinitions
   - MINOR: New principles or material expansions
   - PATCH: Clarifications, wording, typo fixes

### Compliance

- All PRs/reviews MUST verify compliance with these principles
- The `/spec-kitty.analyze` command validates constitution alignment
- Complexity MUST be justified in the Complexity Tracking section
- See CLAUDE.md for runtime development guidance

**Version**: 1.0.0 | **Ratified**: 2025-12-01 | **Last Amended**: 2025-12-01
