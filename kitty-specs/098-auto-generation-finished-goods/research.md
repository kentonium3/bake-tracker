# Research: F098 Auto-Generation of Finished Goods

**Feature**: 098-auto-generation-finished-goods
**Date**: 2026-02-08

## Research Question 1: How to distinguish bare vs assembled FinishedGoods?

**Decision**: Use existing `AssemblyType.BARE` enum value

**Rationale**: The `AssemblyType` enum in `src/models/assembly_type.py` already has `BARE = "bare"` with metadata specifying single-component limits (min=1, max=1, recommended=1). No schema changes needed.

**Alternatives considered**:
- Add `is_assembled` boolean field (func-spec suggestion) — rejected because `assembly_type` already distinguishes this and adding a redundant boolean would violate single source of truth
- Add new enum values — unnecessary since BARE already captures the semantics

## Research Question 2: What junction model links FinishedGood to FinishedUnit?

**Decision**: Use existing `Composition` model with `Composition.create_unit_composition()` factory method

**Rationale**: `Composition` (`src/models/composition.py`) already supports polymorphic component linking via a 4-way XOR constraint (`finished_unit_id`, `finished_good_id`, `packaging_product_id`, `material_unit_id`). The factory method `create_unit_composition(assembly_id, finished_unit_id, quantity, notes, sort_order)` creates the exact record needed. `FinishedGoodService._create_composition()` already uses this pattern.

**Alternatives considered**:
- Create new `FinishedGoodComponent` model (func-spec suggestion) — rejected because it duplicates existing `Composition` functionality

## Research Question 3: Where should auto-generation be triggered?

**Decision**: Move FinishedUnit CRUD orchestration from UI layer into `recipe_service`, then add FinishedGood auto-generation in the same service-layer orchestration

**Rationale**: Currently `recipes_tab.py._save_yield_types()` (UI layer) directly calls `finished_unit_service.create/update/delete_finished_unit()`. This violates Constitution Principle V (Layered Architecture Discipline: UI MUST NOT contain business logic). The recipe save must become an atomic service-layer operation.

**Current flow (broken)**:
```
UI: recipes_tab._add_recipe()
  → recipe_service.create_recipe()          # Transaction A
  → recipes_tab._save_yield_types()         # UI orchestration
    → finished_unit_service.create_finished_unit()  # Transaction B (separate!)
```

**Target flow (correct)**:
```
UI: recipes_tab._add_recipe()
  → recipe_service.save_recipe_with_yields()   # Single transaction
    → Create/update Recipe
    → Create/update/delete FinishedUnits
    → Auto-create/update/delete bare FinishedGoods
    → All atomic within one session
```

**Alternatives considered**:
- SQLAlchemy event hooks (`after_insert` on FinishedUnit) — rejected because it hides business logic in model layer, makes debugging harder, and doesn't solve the session isolation problem
- Trigger in `finished_unit_service.create_finished_unit()` — rejected because it couples two services and doesn't address the UI-layer orchestration violation

## Research Question 4: Can finished_unit_service accept session parameters?

**Decision**: Add `session: Optional[Session] = None` parameter to all three CRUD methods

**Rationale**: Constitution Principle VI.C mandates ALL service functions accept optional session parameter. `finished_unit_service` methods currently create their own `session_scope()` internally, preventing transaction composition. `finished_good_service` already follows the correct pattern.

**Methods requiring session parameter**:
- `create_finished_unit()` (line 274) — currently no session param
- `update_finished_unit()` (line 390) — currently no session param
- `delete_finished_unit()` (line 495) — currently no session param

## Research Question 5: How to handle propagation on FinishedUnit updates?

**Decision**: When `update_finished_unit()` changes name or category, find the corresponding bare FinishedGood (via Composition lookup) and update it within the same session

**Rationale**: The propagation must be:
1. Same transaction as FU update (atomic)
2. Only for bare FGs (assembly_type=BARE)
3. Only for name/category changes (not all fields)

**Lookup pattern**: Query `Composition` where `finished_unit_id=<fu_id>`, join to `FinishedGood` where `assembly_type=BARE`. This finds the 1:1 bare FG for a given FU.

## Research Question 6: How to handle cascade delete with assembly protection?

**Decision**: Before deleting a bare FinishedGood, check if it's used as a component in any assembled FinishedGood

**Rationale**: `delete_finished_unit()` already checks for Composition references (`ReferencedUnitError`). The new flow must additionally check if the bare FG itself is referenced as a component in other assemblies via `Composition.finished_good_id`.

**Cascade order**:
1. Check if bare FG is referenced by any assembly → block if yes
2. Delete Composition linking bare FG to FU
3. Delete bare FinishedGood
4. Delete FinishedUnit
5. All within same transaction

## Research Question 7: How to handle bulk import?

**Decision**: Extend `catalog_import_service._import_recipes_impl()` to call auto-generation after recipe creation

**Rationale**: Currently the import creates recipes but does NOT create FinishedUnits or FinishedGoods. The import data includes `yield_types` in the recipe data. After recipe creation, the orchestration function should be called to create FU+FG pairs.

**Key finding**: Import already operates within a single session, so adding FU+FG creation to the same flow maintains transactional atomicity.

## Research Question 8: Migration of existing bare FinishedGoods

**Decision**: Write a one-time migration function that identifies existing bare FGs and ensures 1:1 linkage

**Identification criteria**:
- FinishedGood with `assembly_type=BARE`
- Has exactly one Composition record
- That Composition references a `finished_unit_id`
- These are already correct — just need verification

**Edge case**: Manually-created FGs that are effectively bare but have `assembly_type=BUNDLE` — these need reclassification.
