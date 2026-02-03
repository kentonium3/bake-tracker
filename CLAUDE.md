# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bake Tracker - Desktop application for managing event-based food production: inventory, recipes, finished goods, and gift package planning.

**Dual Purpose:** This application serves as both a practical tool for a real user (developer's wife) AND a workflow validator for future AI-assisted SaaS evolution. Features must work flawlessly for the current user while validating the workflows, data structures, and business logic that will underpin future voice/chat AI interactions.

**AI-Forward Foundation:** The principle "solve it manually first, then add AI" ensures AI assistance enhances rather than obscures validated processes. BT Mobile companion app proves AI-assisted data entry (purchase scanning, inventory updates) before real-time interfaces are built.

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

## Testing from Worktrees (IMPORTANT)

When working in a feature worktree (`.worktrees/NNN-feature/`), the Python venv is in the **main repo**, not the worktree. Use the helper script which handles this automatically:

```bash
# From anywhere (main repo or worktree) - PREFERRED METHOD
./run-tests.sh                           # Run all tests
./run-tests.sh -v                        # Verbose
./run-tests.sh src/tests/test_foo.py -v  # Specific file
./run-tests.sh -k "test_name"            # Specific test
./run-tests.sh --cov=src                 # With coverage
```

If you need to run Python directly from a worktree:

```bash
# Get main repo path (works from worktree or main)
MAIN_REPO="$(git rev-parse --show-toplevel)"
MAIN_REPO="${MAIN_REPO%%/.worktrees/*}"

# Use main repo's venv
$MAIN_REPO/venv/bin/python src/main.py
$MAIN_REPO/venv/bin/pytest src/tests -v
```

**Why this matters:** Worktrees share the git history but not the filesystem. The venv at `./venv` only exists in the main repo. Attempting to activate `./venv/bin/activate` from a worktree will fail.

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
    tasks/      # Individual work packages (flat structure, lane in frontmatter)
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

5. **Migration Strategy**: Schema changes use reset/re-import rather than migration scripts. Full data exports via the app's import/export service allow external transformation of import files to meet current schema requirements. This avoids maintaining version translation code.

## Development Workflow (Spec-Kitty)

Features follow a documentation-first workflow:

1. `/spec-kitty.specify` - Create feature spec in `kitty-specs/`
2. `/spec-kitty.plan` - Research and plan implementation
3. `/spec-kitty.tasks` - Generate atomic task prompts
4. `/spec-kitty.implement` - Execute with TDD
5. `/spec-kitty.review` - Validate against acceptance criteria
6. `/spec-kitty.accept` - Full acceptance checks
7. `/spec-kitty.merge` - Merge and cleanup

## Multi-Agent Orchestration

This project uses multi-agent orchestration with **Claude Code as the lead agent**. Gemini CLI is available as a teammate agent for parallel work.

### Lead Agent Responsibilities (Claude Code)

As lead agent, Claude Code:
- Initiates features via `/spec-kitty.specify` to generate spec, branch, and worktree
- Shares feature slug with teammate agents for coordinated work
- Owns the gated workflow progression: Specify → Plan → Tasks → Implement → Review → Accept → Merge
- Delegates parallelizable implementation tasks to Gemini
- Maintains overall feature coherence and integration

### Workflow Stages

1. **Specification Phase:** Lead agent creates feature foundation using spec-kitty commands
2. **Planning & Research:** Run `/spec-kitty.plan` and `/spec-kitty.research` to produce artifacts
3. **Task Decomposition:** `/spec-kitty.tasks` generates work packages in planned queue
4. **Parallel Implementation:** Delegate independent tasks to Gemini via `gemini-parallel-dev` agent
5. **Review & Integration:** Lead agent reviews completed work and manages merge

### Delegating to Gemini CLI

Use the `gemini-parallel-dev` agent for tasks that:
- Are independent and won't conflict with your current work
- Operate on different files or modules
- Can proceed without blocking each other

**Good candidates:**
- Running tests while implementing features
- Generating documentation while refactoring code
- Implementing independent features in separate parts of the codebase
- Research tasks that inform later implementation

**Gemini CLI capabilities:**
- Can run spec-kitty commands (`/spec-kitty.*`)
- Has access to the full codebase
- Can perform research, code generation, and file operations

### Coordination Best Practices

- **Enforce file boundaries:** Specify which files each agent modifies to prevent conflicts
- **Mark safe-to-parallelize tasks:** Clearly identify tasks that can run concurrently
- **Use official lane-movement scripts:** Never manually move files between task lanes
- **Refresh context after plan updates:** Re-read artifacts when plans change

## Agent Rules

- **Paths**: Always use exact paths relative to project root or absolute paths
- **Encoding**: UTF-8 only. Avoid Windows-1252 smart quotes (" " ' '). Use standard ASCII quotes.
- **Git**: Descriptive commit messages in imperative mood. Never commit secrets.
- **Context**: Read `plan.md`, `tasks.md`, and relevant artifacts at session start

## Spec-Kitty Workflow Compliance (NON-NEGOTIABLE)

This project uses spec-kitty (v0.13.x) for feature development. The workflow is AUTHORITATIVE.

### Golden Rule: Follow the Skill Prompts

The `/spec-kitty.*` skills contain up-to-date command syntax and workflow guidance. When executing spec-kitty workflows:

1. **Invoke the skill** (e.g., `/spec-kitty.implement`, `/spec-kitty.review`)
2. **Follow the prompt instructions exactly** - they are loaded from current templates
3. **Check `--help` before running CLI commands** - never guess at parameters
4. **Do not memorize CLI syntax** - it changes between versions

### STOP and Ask the User If:

- A `/spec-kitty.*` command fails or errors
- Task lane transitions don't work as expected
- Acceptance checks fail unexpectedly
- Any workflow step produces unexpected results
- You're unsure which skill or command to use

### NEVER Manually:

- Edit task frontmatter fields (`lane`, `agent`, `review_status`, etc.)
- Move files between task directories
- **Create lane subdirectories** (`planned/`, `doing/`, `for_review/`, `done/`) - these are DEPRECATED
- Run `git worktree` commands outside of `/spec-kitty.merge`
- Bypass validation failures with flags (e.g., `--lenient`) without user approval
- Invent CLI parameters - always verify with `--help`
- **Infer workflow patterns from training data or past context** - always follow the current prompt instructions

### When Validation Fails:

**STOP and investigate the root cause** rather than:
- Looking for bypass flags to skip validation
- Manually editing files to satisfy checks
- Guessing at what commands "should have" been run

If acceptance fails due to missing metadata, this indicates workflow commands were skipped during implementation. Report this to the user rather than patching around it.

### CLI Reference (Always Verify with --help)

The general command structure is:
```bash
# Move work package between lanes
spec-kitty agent tasks move-task <WP_ID> --to <lane> [--assignee <name>] [--note "..."]

# Mark subtask status in tasks.md
spec-kitty agent tasks mark-status <TASK_ID> --status done|pending

# List tasks with optional filtering
spec-kitty agent tasks list-tasks [--lane <lane>]
```

**Important:** Feature slug is auto-detected from git branch. Always run from the feature worktree. Use `--help` on any command to see current options.

### Session Start Checklist

Before working on spec-kitty tasks, verify:
1. `ls kitty-specs/<feature>/tasks/` shows flat WP files (e.g., `WP01-name.md`), NOT subdirectories
2. Task lane changes happen via `lane:` frontmatter field, NOT by moving files
3. Re-read this section if you feel uncertain about the workflow

### Deprecated Patterns (DO NOT USE - CRITICAL)

**Background:** Claude has demonstrated a tendency to infer workflow patterns from training data or past conversation context that override explicit written instructions. The following patterns are DEPRECATED and must NEVER be used, regardless of what past sessions may have done.

#### Lane Subdirectories (DEPRECATED)

NEVER create or use these directories:
- `tasks/planned/`
- `tasks/doing/`
- `tasks/for_review/`
- `tasks/done/`

The CORRECT pattern is:
- All WP files remain in `tasks/` (flat structure)
- Lane state is tracked ONLY in YAML frontmatter: `lane: "planned"`, `lane: "doing"`, etc.
- Lane transitions are done via `spec-kitty agent tasks move-task` command

#### Why This Matters

If you find yourself about to:
- Create a `planned/`, `doing/`, `for_review/`, or `done/` subdirectory
- Move a WP file from one directory to another
- Infer "this is how it was done before" from context

**STOP IMMEDIATELY.** Re-read the spec-kitty prompt instructions. The prompt you received contains the authoritative, current workflow. Past patterns in training data or conversation history are NOT authoritative.

#### Self-Check Before Lane Operations

Before any task lane operation, ask yourself:
1. Am I about to create a subdirectory? → STOP, this is wrong
2. Am I about to move a file? → STOP, this is wrong
3. Am I using the `spec-kitty agent tasks move-task` command? → CORRECT
4. Does the WP file stay in `tasks/` with only frontmatter changing? → CORRECT

## Key Design Decisions

- **Ingredients vs Products**: Recipes reference generic Ingredients; Inventory holds specific Products (brands/packages). This enables recipe sharing and brand flexibility.
- **Slug-based FKs**: Use slugs instead of display names for foreign keys (enables future localization)
- **UUID support**: BaseModel includes UUID for future distributed/multi-user scenarios
- **Nested Recipes**: Recipes can include other recipes as components via RecipeComponent junction table. Maximum 3 levels of nesting. Circular references are prevented at validation time. Shopping lists aggregate ingredients from all levels.
- **Event-Centric Production Model**: ProductionRun and AssemblyRun link to Events via optional `event_id` FK. This enables: (1) tracking which production is for which event, (2) explicit production targets per event via EventProductionTarget/EventAssemblyTarget, (3) progress tracking (produced vs target), (4) package fulfillment status workflow (pending/ready/delivered). See `docs/design/schema_v0.6_design.md`.

## Session Management (CRITICAL - Read Before Modifying Services)

**Problem:** Nested `session_scope()` calls cause SQLAlchemy objects to become detached, resulting in silent data loss where modifications are not persisted.

### The Anti-Pattern (DO NOT DO THIS)

```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function()  # If this uses session_scope(), obj becomes detached!
        obj.field = value  # THIS CHANGE IS SILENTLY LOST
```

### The Correct Pattern

```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function(session=session)  # Pass session to maintain tracking
        obj.field = value  # This change persists correctly

def inner_function(..., session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _inner_function_impl(..., session)
    with session_scope() as session:
        return _inner_function_impl(..., session)
```

### Rules for Service Functions

1. **Multi-step operations MUST share a session** - If a function queries an object, calls other services, then modifies the object, all operations must use the same session.

2. **Service functions that may be called from other services MUST accept `session=None`** - This allows callers to pass their session for transactional atomicity.

3. **When calling another service function within a transaction, ALWAYS pass the session** - Even if the called function works without it, passing the session ensures objects remain tracked.

4. **Never return ORM objects from `session_scope()` if they'll be modified later** - Objects become detached when the scope exits. Return IDs or DTOs instead, or keep operations within the same session.

### Functions That Accept Session Parameter

These functions have been updated to accept an optional `session` parameter and correctly use it:
- `recipe_service.get_aggregated_ingredients()`
- `ingredient_service.get_ingredient()`
- `inventory_item_service.consume_fifo()` (always had it)
- `batch_production_service.check_can_produce()` - fixed 2025-12-11
- `batch_production_service.record_batch_production()` - already correct
- `assembly_service.check_can_assemble()` - fixed 2025-12-11
- `assembly_service.record_assembly()` - fixed 2025-12-11

### Transaction Patterns Guide

For comprehensive documentation of transaction patterns, including code examples
and common pitfalls, see:

**`docs/design/transaction_patterns_guide.md`**

### Reference

See `docs/design/session_management_remediation_spec.md` for full technical details.

## Pagination Pattern (Web Migration Ready)

### DTOs Available

- `PaginationParams`: Page number and items per page (`src/services/dto.py`)
- `PaginatedResult[T]`: Generic result container with metadata

### Usage Pattern (Future Service Adoption)

When adding pagination to a service function:

**Pattern: Optional Pagination (Backward-Compatible)**

```python
from src.services.dto import PaginationParams, PaginatedResult

def list_items(
    filter: Optional[ItemFilter] = None,
    pagination: Optional[PaginationParams] = None,  # Optional!
    session: Optional[Session] = None
) -> PaginatedResult[Item]:
    """
    List items with optional pagination.

    Desktop usage: pagination=None returns all items (current behavior)
    Web usage: pagination=PaginationParams(...) returns one page
    """
    def _impl(sess: Session) -> PaginatedResult[Item]:
        query = sess.query(Item)

        # Apply filters...
        if filter:
            # ... filtering logic
            pass

        # Count total
        total = query.count()

        # Apply pagination (if provided)
        if pagination:
            # Web: return one page
            items = query.offset(pagination.offset()).limit(pagination.per_page).all()
            page = pagination.page
            per_page = pagination.per_page
        else:
            # Desktop: return all items (current behavior)
            items = query.all()
            page = 1
            per_page = total or 1

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Desktop vs Web Usage

**Desktop (current pattern unchanged):**
```python
# No pagination parameter - get all items
result = list_ingredients(filter=IngredientFilter(category="baking"))
all_items = result.items  # All ingredients
```

**Web (future FastAPI):**
```python
@app.get("/api/ingredients")
def get_ingredients(page: int = 1, per_page: int = 50):
    result = list_ingredients(
        pagination=PaginationParams(page=page, per_page=per_page)
    )
    return {
        "items": [serialize(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
        "has_next": result.has_next
    }
```

### When to Adopt

- **New services**: Use pagination from the start
- **Existing services**: Adopt incrementally during refactoring
- **Desktop UI**: No changes needed (pagination=None)
- **Web migration**: See web-prep/F003 for comprehensive adoption plan
