<!--
Sync Impact Report:
- Version change: INITIAL → 1.0.0
- Modified principles: N/A (initial version)
- Added sections: All sections (initial creation)
- Removed sections: N/A
- Templates requiring updates:
  ✅ plan-template.md - reviewed, constitution check section compatible
  ✅ spec-template.md - reviewed, requirements align with principles
  ✅ commands/*.md - reviewed, no agent-specific references requiring updates
- Follow-up TODOs: None
-->

# Bake Tracker Constitution

## Core Principles

### I. User-Centric Design

**The application serves a real user with real needs - all features must deliver practical value.**

- Features MUST solve actual user problems, not theoretical ones
- UI MUST be intuitive for non-technical users
- Workflows MUST match natural baking planning processes
- User testing with the primary user (wife) MUST validate major features before completion
- Complexity that doesn't serve the user MUST be rejected

**Rationale:** This is a personal tool for managing holiday baking operations. Features exist to make the user's life easier, not to demonstrate technical sophistication. If the user can't understand or use it, it fails.

### II. Data Integrity & FIFO Accuracy (NON-NEGOTIABLE)

**Cost calculations and inventory tracking must be accurate and trustworthy.**

- FIFO (First In, First Out) consumption MUST be enforced for pantry items
- Unit conversions MUST be ingredient-specific where density/volume matters
- Cost calculations MUST reflect actual pantry consumption or preferred variant pricing
- Database migrations MUST preserve all existing data with validation
- Data import/export MUST be lossless and version-controlled

**Rationale:** The user relies on this application for expense tracking and shopping planning. Incorrect costs or lost data breaks trust and renders the application useless. FIFO matches physical reality (using oldest ingredients first) and provides accurate historical costing.

### III. Future-Proof Schema, Present-Simple Implementation

**Database schema supports future enhancements, but only required fields are populated initially.**

- Schema MUST include industry standard fields (FoodOn, GTIN, etc.) as nullable
- Implementation MUST populate only essential fields initially
- Features MUST be added incrementally without schema breaking changes
- User MUST NOT be burdened with unnecessary data entry upfront
- Optional enhancements MUST be clearly documented for future phases

**Rationale:** The schema is designed to support potential commercial product evolution, but the immediate need is a working personal tool. This principle allows the application to grow without disruptive migrations while keeping the MVP simple and usable.

### IV. Test-Driven Development

**Service layer logic must be tested before implementation is considered complete.**

- Unit tests MUST be written for all service layer methods
- Tests MUST cover happy path, edge cases, and error conditions
- Integration tests MUST validate database operations
- Test coverage MUST exceed 70% for services layer
- Failing tests MUST block feature completion

**Rationale:** The application involves complex calculations (FIFO costing, unit conversions, event planning aggregations). Manual testing cannot reliably catch regressions. Automated tests provide confidence during refactoring and feature additions.

### V. Layered Architecture Discipline

**Clear separation between UI, business logic, and data access layers.**

- UI layer (`src/ui/`) MUST NOT contain business logic
- Services layer (`src/services/`) MUST NOT import UI components
- Models layer (`src/models/`) MUST define schema and relationships only
- Cross-layer dependencies MUST flow downward only (UI → Services → Models → Database)
- Each layer MUST have a single, well-defined responsibility

**Rationale:** Layered architecture enables independent testing, easier refactoring, and potential future UI alternatives (web, mobile). Violations create tight coupling and make the codebase unmaintainable.

### VI. Migration Safety & Validation

**Database migrations must be reversible and thoroughly validated before execution.**

- Migration scripts MUST support dry-run mode for preview
- Dry-run MUST be executed and reviewed before actual migration
- Migration MUST preserve all data with validation queries
- Rollback plan MUST be documented before migration
- Schema changes MUST be backward-compatible during transition periods

**Rationale:** The database contains the user's planning data for important holiday events. Data loss or corruption is unacceptable. Gradual migration strategies (dual foreign keys, parallel models) provide safety nets during major refactors.

## Technology Stack Constraints

**Fixed technology choices for consistency and compatibility.**

- **Language:** Python 3.10+ (minimum version for type hints and syntax features)
- **UI Framework:** CustomTkinter (modern appearance, cross-platform, desktop-native)
- **Database:** SQLite with WAL mode (portable, no server, excellent Python integration)
- **ORM:** SQLAlchemy 2.x (type safety, relationship management, migration support)
- **Testing:** pytest (de facto standard for Python, excellent fixtures and plugins)
- **Packaging:** PyInstaller (single executable for Windows distribution)

**Rationale:** These technologies are mature, well-documented, and meet the requirements for a desktop application. Changes require strong justification (e.g., fundamental limitation discovered) and full migration plan.

## Development Workflow

**Spec-Kitty driven development with documentation-first approach.**

- Feature specifications MUST be created in `/kitty-specs/` before implementation
- Implementation plans MUST define technical approach and complexity justifications
- Tasks MUST be tracked in `/tasks/` directory with clear status (backlog/doing/done)
- Documentation MUST be updated before feature is marked complete
- Git commits MUST reference feature numbers and follow conventional commit format

**Workflow Steps:**
1. `/spec-kitty.specify` - Create feature specification with user stories
2. `/spec-kitty.plan` - Research and plan technical implementation
3. `/spec-kitty.tasks` - Generate atomic, testable task prompts
4. `/spec-kitty.implement` - Execute tasks with TDD approach
5. `/spec-kitty.review` - Validate implementation against acceptance criteria
6. `/spec-kitty.accept` - Run full acceptance checks and user testing
7. `/spec-kitty.merge` - Merge feature branch and cleanup

**Rationale:** Spec-Kitty enforces a disciplined approach that prevents scope creep, ensures testability, and maintains comprehensive documentation. The workflow matches software engineering best practices while providing AI-assisted automation.

## Governance

**The constitution guides all development decisions and must be respected.**

### Amendment Process

- Constitution amendments MUST be proposed with clear rationale
- Version MUST be incremented according to semantic versioning:
  - **MAJOR:** Backward incompatible principle removals or redefinitions
  - **MINOR:** New principles added or material guidance expansions
  - **PATCH:** Clarifications, wording improvements, typo fixes
- Sync Impact Report MUST be generated showing affected templates
- All dependent templates and documentation MUST be updated

### Compliance Review

- Feature plans MUST pass Constitution Check gate before implementation
- Principle violations MUST be explicitly justified in Complexity Tracking table
- "Simpler alternative rejected because" MUST be documented for violations
- Unjustified complexity MUST be rejected and simplified

### Living Documentation

- This constitution supersedes ad-hoc decisions and undocumented practices
- Questions about architecture or approach MUST consult constitution first
- Conflicts between constitution and existing code MUST be resolved in favor of constitution
- Runtime guidance for AI agents found in `.kittify/AGENTS.md`

**Version**: 1.0.0 | **Ratified**: 2025-11-08 | **Last Amended**: 2025-11-08
