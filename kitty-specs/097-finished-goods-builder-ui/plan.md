# Implementation Plan: Finished Goods Builder UI

**Branch**: `097-finished-goods-builder-ui` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/097-finished-goods-builder-ui/spec.md`

## Summary

Build a 3-step accordion builder dialog for creating and editing composite FinishedGoods (bundles, variety packs, gift baskets). The builder replaces the existing `FinishedGoodFormDialog` for non-BARE items, providing multi-select component selection with per-component quantity specification across Food (Step 1), Materials (Step 2), and Review (Step 3) stages. Edit mode pre-populates all steps from existing Composition records. No schema changes required — this is a pure UI feature leveraging existing service layer operations.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI framework), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode (existing)
**Testing**: pytest
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: Dialog opens in <500ms; save completes in <2s for up to 20 components
**Constraints**: Single-user desktop, no concurrency concerns; dialog must be responsive during filtering/search
**Scale/Scope**: ~50-200 FinishedUnits, ~20-100 MaterialUnits typical; selectable items fit in scrollable lists

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Paper prototype validated (2026-02-06); 3-step workflow matches user mental model |
| II. Data Integrity & FIFO | PASS | No FIFO operations; uses atomic create/update via existing service |
| III. Future-Proof Schema | PASS | No schema changes; uses existing Composition model |
| IV. Test-Driven Development | PASS | Tests required for builder state management, save operations, filtering logic |
| V. Layered Architecture | PASS | Builder dialog calls service methods only; no business logic in UI |
| VI. Code Quality | PASS | Session parameter pattern used; exception-based error handling; no hardcoded maps |
| VII. Schema Change Strategy | N/A | No schema changes |
| VIII. Pragmatic Aspiration | PASS | Service layer remains UI-independent; builder is desktop-only but service calls are web-ready |

**Post-Phase-1 re-check**: Confirmed — no violations introduced by design. The custom AccordionStep widget is desktop-only but doesn't affect service layer portability.

## Project Structure

### Documentation (this feature)

```
kitty-specs/097-finished-goods-builder-ui/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model documentation
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── models/                              # No changes — existing models used as-is
│   ├── finished_good.py                 # FinishedGood model (parent assembly)
│   ├── composition.py                   # Composition junction table (components)
│   ├── finished_unit.py                 # FinishedUnit model (food items)
│   ├── material_unit.py                 # MaterialUnit model (material items)
│   └── assembly_type.py                 # AssemblyType enum
│
├── services/                            # Minimal changes — may add query helpers
│   ├── finished_good_service.py         # Existing create/update operations
│   ├── finished_unit_service.py         # Existing query operations
│   └── material_catalog_service.py      # Existing material queries
│
├── ui/
│   ├── widgets/
│   │   └── accordion_step.py            # NEW: Reusable accordion step widget
│   ├── builders/
│   │   └── finished_good_builder.py     # NEW: 3-step builder dialog
│   └── finished_goods_tab.py            # MODIFIED: Wire up builder for add/edit
│
└── tests/
    ├── test_finished_good_builder.py    # NEW: Builder dialog unit tests
    └── test_accordion_step.py           # NEW: Accordion widget tests
```

**Structure Decision**: Single desktop project. New UI code goes in `src/ui/builders/` (new directory for multi-step builder patterns) and `src/ui/widgets/` (existing widget directory). Tests alongside existing test files.

## Complexity Tracking

No constitution violations — no entries needed.

## Design Decisions

### D-001: AccordionStep Widget Architecture

The builder uses a custom `AccordionStep` widget since CustomTkinter has no built-in accordion. Each step is a CTkFrame containing:
- **Header frame**: Step number label, title label, status icon (lock/checkmark/arrow), summary text, "Change" button
- **Content frame**: Shown/hidden via `pack()`/`pack_forget()`
- **States**: `locked` (greyed, not clickable), `active` (expanded, blue border), `completed` (collapsed, checkmark + summary)

The builder dialog manages a list of AccordionStep instances and enforces mutual exclusion (only one expanded at a time).

Pattern based on `add_purchase_dialog.py` provisional form toggle (lines 531-560).

### D-002: Builder Dialog as CTkToplevel

Follows existing dialog patterns from `FinishedGoodFormDialog`:
- `CTkToplevel` with `transient(parent)` + `grab_set()` for modal behavior
- Returns `result` dict on save, `None` on cancel
- `wait_window()` pattern for synchronous dialog usage from parent tab

Size: 700x750 (larger than existing forms to accommodate multi-select lists).

### D-003: Component Selection as Inline Checkboxes

Rather than the existing `ComponentSelectionPopup` (single-select popup), the builder uses **inline multi-select** within each accordion step:
- Filter bar (category dropdown + search entry) at top of step content
- Scrollable CTkFrame below with one row per selectable item
- Each row: CTkCheckBox + name label + CTkEntry for quantity (disabled until checked)
- Checking the checkbox enables the quantity field and sets default quantity to 1

This is a new pattern but is more usable for multi-select than repeated popup invocations.

### D-004: State Management Between Steps

Builder maintains an internal `BuilderState` object:
- `food_selections: Dict[int, ComponentSelection]` — keyed by component ID for O(1) lookup
- `material_selections: Dict[int, ComponentSelection]` — same pattern
- Selections are global (not per-filter-view) — changing category filter preserves all selections
- When navigating back to a step, the UI re-renders from state, re-checking previously selected items

### D-005: Edit Mode Loading

In edit mode, the builder:
1. Receives the `FinishedGood` object with eagerly-loaded `components` relationship
2. Partitions existing Composition records by `component_type`:
   - `finished_unit` and `finished_good` → food_selections
   - `material_unit` → material_selections
3. Pre-populates all steps, marks Step 1 and Step 2 as completed
4. Opens directly to Step 3 (Review) so user can see current state before making changes
5. Excludes the current FinishedGood from selectable items to prevent self-reference

### D-006: Save Operation

On save, the builder:
1. Collects all selections from `food_selections` + `material_selections`
2. Converts to service format: `[{"type": str, "id": int, "quantity": int, "sort_order": int}]`
3. Calls `create_finished_good()` (create mode) or `update_finished_good()` (edit mode)
4. The service handles atomicity — all-or-nothing transaction
5. On success: sets `self.result` with result data and calls `self.destroy()`
6. On error: displays error message, stays open for correction

### D-007: Integration with FinishedGoodsTab

The tab's `_add_finished_good()` and `_edit_finished_good()` methods will be updated to launch `FinishedGoodBuilderDialog` instead of `FinishedGoodFormDialog`. Same integration pattern:
- Create: `dialog = FinishedGoodBuilderDialog(self)`
- Edit: `dialog = FinishedGoodBuilderDialog(self, finished_good=fg)`
- Both: `self.wait_window(dialog)` → check `dialog.result` → call service → refresh

The existing `FinishedGoodFormDialog` in `src/ui/forms/finished_good_form.py` is NOT deleted — it may still be useful for quick edits or future use. The tab simply stops calling it.

### D-008: Materials — MaterialUnit Selection

Step 2 shows MaterialUnits (not MaterialProducts), because Composition records store `material_unit_id`. MaterialUnits are grouped by their parent MaterialProduct's MaterialCategory for the category filter dropdown.

Query approach: Join MaterialUnit → MaterialProduct → MaterialSubcategory → MaterialCategory for category filtering. Display MaterialUnit.name in the list.

## Implementation Phases (Work Package Guidance)

### Phase A: Foundation (AccordionStep Widget)
- Create `AccordionStep` widget class with states: locked, active, completed
- Implement header with step number, title, status icon, summary, "Change" button
- Implement content frame show/hide
- Unit tests for state transitions

### Phase B: Builder Dialog Shell
- Create `FinishedGoodBuilderDialog` as CTkToplevel
- Wire up 3 AccordionStep instances (Food, Materials, Review)
- Implement step navigation logic (mutual exclusion, sequential progression)
- Name entry field in header area
- Cancel with confirmation dialog
- Unit tests for navigation state

### Phase C: Step 1 — Food Selection
- Category filter dropdown (distinct categories from FinishedUnits)
- Bare/Assembly toggle buttons
- Search entry with real-time filtering
- Scrollable checkbox list with quantity entries
- Selection state management (persist across filter changes)
- Minimum-1-item validation before Continue
- Unit tests for filtering, selection, validation

### Phase D: Step 2 — Materials Selection
- MaterialCategory filter dropdown
- Search entry with real-time filtering
- Scrollable checkbox list with quantity entries
- Skip button to bypass materials
- Unit tests for filtering, skip, selection

### Phase E: Step 3 — Review & Save
- Component summary display (food items + materials with quantities)
- Editable name field with uniqueness check
- Notes text field
- Auto-suggested tags from component names
- Save button → service call (create or update)
- Start Over button
- Error handling with user feedback
- Unit tests for save, validation, error cases

### Phase F: Edit Mode
- Pre-populate builder state from existing FinishedGood components
- Open to Step 3 (Review) in edit mode
- Exclude self from selectable items
- Test edit → modify → save round-trip
- Integration tests

### Phase G: Tab Integration
- Update `FinishedGoodsTab._add_finished_good()` to use builder
- Update `FinishedGoodsTab._edit_finished_good()` to use builder
- Verify double-click and Edit button launch builder
- Verify list refresh after save
- Integration tests
