# Research: Finished Goods Builder UI

**Feature**: 097-finished-goods-builder-ui
**Date**: 2026-02-06

## R-001: Composition Model (Not FinishedGoodComponent)

**Decision**: The junction table is `Composition` (not `FinishedGoodComponent` as referenced in the func spec)

**Rationale**: The Composition model at `src/models/composition.py` implements a polymorphic junction with a 4-way XOR constraint. Each Composition record links a parent (assembly_id → FinishedGood) to exactly one of:
- `finished_unit_id` → FinishedUnit (food item)
- `finished_good_id` → FinishedGood (nested assembly)
- `packaging_product_id` → Product (packaging)
- `material_unit_id` → MaterialUnit (material consumption unit)

Factory methods exist: `Composition.create_unit_composition()`, `create_assembly_composition()`, `create_material_unit_composition()`

**Alternatives considered**: None — this is the existing schema.

## R-002: Materials Step Shows MaterialUnits (Not MaterialProducts Directly)

**Decision**: Step 2 (Materials) must show `MaterialUnit` records for selection, since that is what gets stored in Composition records.

**Rationale**: A `MaterialUnit` is a child of `MaterialProduct` and defines an atomic consumption unit (e.g., "6-inch Red Ribbon" = 6 inches of the parent product per use). The Composition model stores `material_unit_id`, not `material_product_id`. The func spec references "MaterialProducts" but the data model requires MaterialUnit references.

**UI approach**: Group MaterialUnits by their parent MaterialProduct's MaterialCategory for filtering. Display the MaterialUnit name (which is more specific than the product name).

**Alternatives considered**: Showing MaterialProducts and auto-selecting their default MaterialUnit — rejected because a MaterialProduct may have multiple MaterialUnits with different consumption quantities.

## R-003: Service Layer Component Format

**Decision**: Use the existing component dict format accepted by `FinishedGoodService.create_finished_good()` and `update_finished_good()`

**Rationale**: Both methods accept components as:
```python
[{"type": "finished_unit"|"material_unit"|"finished_good",
  "id": int, "quantity": int, "notes": str|None, "sort_order": int}]
```

The `update_finished_good()` method uses a delete-and-replace strategy for components: when a component list is provided, ALL existing Composition records are deleted and replaced with the new list. This simplifies the builder's save logic — no need to diff old vs. new components.

**Alternatives considered**: Incremental component updates (add/remove/modify individual compositions) — rejected because the service already handles delete-and-replace atomically.

## R-004: "Bare Items Only" Filter Implementation

**Decision**: Filter by `FinishedGood.assembly_type == AssemblyType.BARE` for the "Bare items only" toggle.

**Rationale**: In the data model, bare items are auto-created FinishedGoods with `assembly_type=BARE`. These represent single FinishedUnits (direct from recipes with EA yield). The "Include assemblies" toggle would show items where `assembly_type != BARE`.

The existing `FinishedGoodsTab` already uses `AssemblyType` for filtering, confirming this approach.

**Alternatives considered**: Querying FinishedUnits directly — rejected because the builder creates FinishedGoods from other FinishedGoods/FinishedUnits, so selecting at the FinishedGood level (which wraps FinishedUnits) is more appropriate.

## R-005: Category Filtering for Food Items (Step 1)

**Decision**: Use the `category` string field on FinishedUnit (inherited from Recipe) for category filtering in Step 1. For FinishedGoods that are assemblies, derive category from their components or show them in an "Assemblies" section.

**Rationale**: There is no `ProductCategory` model/table. FinishedUnit has a `category` field (String(100), nullable, indexed) that stores the recipe's category. The `finished_unit_service.get_all_finished_units()` method supports `category` parameter for filtering.

For Step 1 filtering, we query the distinct categories across FinishedUnits and use those as dropdown options.

**Alternatives considered**: Using AssemblyType metadata for categories — rejected because AssemblyType describes the bundle type, not the food category.

## R-006: No Existing Accordion Widget

**Decision**: Create a custom `AccordionStep` widget using CTkFrame with pack/pack_forget pattern.

**Rationale**: The codebase has no accordion widget. The closest pattern is the provisional form toggle in `add_purchase_dialog.py` (lines 531-560) which uses `pack()`/`pack_forget()` for show/hide. A reusable accordion widget should:
- Have a clickable header frame with step number, title, status icon, and summary text
- Toggle content frame visibility via pack/pack_forget
- Support states: active (expanded), completed (collapsed with checkmark + summary), locked (greyed out, not clickable)
- Emit callbacks when expanded/collapsed

**Alternatives considered**: Using CTkTabview — rejected because tabs allow random access; accordion enforces sequential workflow with visual progress indication.

## R-007: Existing FinishedGoodFormDialog Integration

**Decision**: The builder replaces the current `FinishedGoodFormDialog` for create/edit operations on non-BARE FinishedGoods. The existing form may remain for simple BARE item editing.

**Rationale**: The `FinishedGoodsTab` currently:
- `_add_finished_good()` launches `FinishedGoodFormDialog` in create mode
- `_edit_finished_good()` launches `FinishedGoodFormDialog` with existing FinishedGood data
- Both use `self.wait_window(dialog)` + `dialog.result` pattern

The builder dialog will follow the same integration pattern — return a result dict on save, None on cancel. The tab's existing `_add_finished_good()` and `_edit_finished_good()` methods will be updated to launch the new builder instead.

**Alternatives considered**: Adding the builder as a separate button alongside the existing form — rejected because having two creation paths would confuse the user.

## R-008: Circular Reference Prevention

**Decision**: Use the existing `FinishedGoodService._validate_no_circular_references()` method when including FinishedGood components (nested assemblies) in Step 1.

**Rationale**: The service already validates circular references during create/update. However, the builder should also prevent the user from selecting the FinishedGood being edited as a component (self-reference check at UI level). The database has a constraint `ck_composition_no_self_reference`.

For the builder, in edit mode, exclude the current FinishedGood from the selectable items in Step 1's "Include assemblies" list.

**Alternatives considered**: Allowing selection and catching the error on save — rejected because immediate feedback is better UX.

## R-009: Name Uniqueness Validation

**Decision**: Check name uniqueness via slug generation. The service generates a slug from display_name and checks for uniqueness.

**Rationale**: `FinishedGoodService._generate_slug()` and `_generate_unique_slug()` handle this. The `create_finished_good()` method catches `IntegrityError` with "uq_finished_good_slug" check. For the builder, we should validate before submission by checking if a slug would collide, providing immediate feedback rather than waiting for a save error.

**Alternatives considered**: Checking display_name directly — rejected because the system uses slug-based uniqueness (display names could differ but generate the same slug).
