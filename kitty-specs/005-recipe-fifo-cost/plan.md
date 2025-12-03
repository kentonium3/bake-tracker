# Implementation Plan: Recipe FIFO Cost Integration

**Branch**: `005-recipe-fifo-cost` | **Date**: 2025-12-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/005-recipe-fifo-cost/spec.md`

## Summary

Extend RecipeService to calculate recipe costs using actual pantry inventory costs via FIFO consumption logic. The feature provides two costing modes:
1. **Actual cost**: Uses FIFO-ordered pantry inventory to determine real ingredient costs
2. **Estimated cost**: Uses preferred variant pricing for planning when pantry is empty

Key technical approach:
- Refactor `PantryService.consume_fifo()` with `dry_run=True` parameter for read-only cost simulation
- Extend RecipeService with new cost calculation methods that coordinate with existing services
- Use `INGREDIENT_DENSITIES` constants for unit conversions (ignore unused `density_g_per_ml` field)
- Fail fast on uncostable ingredients to surface data integrity issues upstream

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (UI - not touched by this feature)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage required
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: Cost calculations complete in <100ms for recipes with up to 50 ingredients
**Constraints**: Read-only costing (no pantry modification); FIFO accuracy is NON-NEGOTIABLE
**Scale/Scope**: Single-user desktop app; recipes typically have 5-20 ingredients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | ✅ PASS | RecipeService calls PantryService/VariantService/PurchaseService (downward flow only) |
| II. Build for Today | ✅ PASS | Using existing infrastructure; no over-engineering; constants-only density approach |
| III. FIFO Accuracy | ✅ PASS | Centralized FIFO logic via `consume_fifo(dry_run=True)`; no drift risk |
| IV. User-Centric Design | ✅ PASS | Fail-fast ensures accurate costs; no misleading partial results |
| V. Test-Driven Development | ✅ PASS | Service layer changes require >70% coverage per spec |
| VI. Migration Safety | ✅ PASS | No schema changes required; service-layer only |

## Project Structure

### Documentation (this feature)

```
kitty-specs/005-recipe-fifo-cost/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (if applicable)
├── checklists/          # Requirements checklist
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── ingredient.py        # Ingredient model (existing)
│   ├── recipe.py            # Recipe/RecipeIngredient models (existing)
│   ├── pantry_item.py       # PantryItem model (existing)
│   ├── variant.py           # Variant model (existing)
│   └── unit_conversion.py   # UnitConversion model (existing)
├── services/
│   ├── recipe_service.py    # MODIFY: Add cost calculation methods
│   ├── pantry_service.py    # MODIFY: Add dry_run parameter to consume_fifo()
│   ├── variant_service.py   # EXISTING: Preferred variant lookup
│   ├── purchase_service.py  # EXISTING: Price history access
│   └── unit_converter.py    # EXISTING: Unit conversion with density support
├── utils/
│   └── constants.py         # EXISTING: INGREDIENT_DENSITIES lookup
├── ui/                      # NOT TOUCHED by this feature
└── tests/
    ├── test_recipe_service.py    # ADD: Cost calculation tests
    ├── test_pantry_service.py    # MODIFY: Add dry_run tests
    └── test_unit_converter.py    # EXISTING: May add density tests
```

**Structure Decision**: Single desktop application structure. This feature modifies existing service layer files only - no new files except tests.

## Engineering Alignment

*Decisions confirmed during planning interrogation:*

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Service Organization | Extend RecipeService directly | Avoids premature abstraction; keeps service layer focused |
| FIFO Simulation | Refactor `consume_fifo()` with `dry_run=True` | Keeps FIFO logic centralized; prevents drift |
| Unit Conversion | Use existing `UnitConverter` + `INGREDIENT_DENSITIES` constants | Infrastructure is 95% ready; density constants are simple and elegant |
| Density Source | Constants only; ignore `density_g_per_ml` field | Previous over-engineered approaches failed; constants are sufficient |
| Error Handling | Fail fast on uncostable ingredients | Forces upstream data completeness; prevents misleading costs |

## Complexity Tracking

*No constitution violations. No complexity justification required.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |

## Phase 0: Research (Complete)

**Artifacts Generated**:
- `research.md` - Key decisions with rationale and evidence
- `data-model.md` - Entity relationships for costing flow
- `research/evidence-log.csv` - Source references for decisions
- `research/source-register.csv` - File inventory consulted

**Key Findings**:
1. Unit conversion infrastructure is mature and ready to use
2. `INGREDIENT_DENSITIES` constants cover ~40 common baking ingredients
3. `consume_fifo()` can be extended with `dry_run` parameter
4. Existing service patterns provide clear template for new methods

## Phase 1: Design & Contracts (Complete)

**Artifacts Generated**:
- `quickstart.md` - Usage examples and API overview
- `contracts/recipe_service_costing.py` - Protocol for new RecipeService methods
- `contracts/pantry_service_dry_run.py` - Protocol for consume_fifo() extension

**Interface Contracts**:

```python
# RecipeService additions
def calculate_actual_cost(recipe_id: int) -> Decimal
def calculate_estimated_cost(recipe_id: int) -> Decimal

# PantryService modification
def consume_fifo(ingredient_slug: str, quantity_needed: Decimal, dry_run: bool = False) -> ConsumeFifoResult
```

## Constitution Re-Check (Post-Design)

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Layered Architecture | ✅ PASS | Contracts confirm downward-only dependencies |
| II. Build for Today | ✅ PASS | No new abstractions; extending existing patterns |
| III. FIFO Accuracy | ✅ PASS | Single source of truth via consume_fifo() |
| IV. User-Centric Design | ✅ PASS | Clear error messages; fail-fast for data issues |
| V. Test-Driven Development | ✅ PASS | Test contracts defined; TDD workflow planned |
| VI. Migration Safety | ✅ PASS | No schema changes; service-only modifications |

## Implementation Scope

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `src/services/pantry_service.py` | MODIFY | Add `dry_run` parameter to `consume_fifo()` |
| `src/services/recipe_service.py` | MODIFY | Add `calculate_actual_cost()` and `calculate_estimated_cost()` |
| `src/tests/test_pantry_service.py` | MODIFY | Add tests for `dry_run=True` behavior |
| `src/tests/test_recipe_service.py` | ADD/MODIFY | Add tests for new costing methods |

### Files NOT Modified

- `src/models/*` - No schema changes
- `src/ui/*` - Service layer only
- `src/services/unit_converter.py` - Already sufficient
- `src/utils/constants.py` - Already sufficient

## Next Steps

Run `/spec-kitty.tasks` to generate work packages for implementation.
