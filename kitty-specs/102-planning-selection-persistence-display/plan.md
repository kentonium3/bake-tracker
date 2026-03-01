# Implementation Plan: Planning Selection Persistence Display

**Branch**: `102-planning-selection-persistence-display` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/102-planning-selection-persistence-display/spec.md`

## Summary

When the Planning tab loads an event with saved recipe/FG selections, the selection frames show blank placeholders despite having the data loaded into memory. This plan adds `render_saved_selections()` methods to both frames that display saved selections on load, with a contextual label ("Saved plan selections") to distinguish them from filter results. The fix is purely UI rendering — no service or model changes.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI framework), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode (no changes — persistence already correct)
**Testing**: pytest (regression tests for blank-start and saved-selections display)
**Target Platform**: macOS desktop (CustomTkinter)
**Project Type**: Single desktop application
**Performance Goals**: Saved selections render in <1 second
**Constraints**: UI-only changes; no service or model modifications
**Scale/Scope**: 3 files modified, ~60 lines of new code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Directly addresses user confusion from testing — blank selections → populated batch calculations disconnect |
| II. Data Integrity & FIFO Accuracy | N/A | No data changes — persistence layer untouched |
| IV. Test-Driven Development | PASS | Regression tests will cover both blank-start and saved-selections paths |
| V. Layered Architecture | PASS | All changes in UI layer only; service queries already correct |
| VI.C. Dependency & State Management | PASS | Uses existing session_scope() pattern for DB queries within UI frame (consistent with populate_categories()) |
| VI.G. Code Organization | PASS | New methods follow existing patterns in both frames |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/102-planning-selection-persistence-display/
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── spec.md              # Feature specification
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/
└── ui/
    ├── planning_tab.py                          # Trigger render after set_selected() calls
    └── components/
        ├── recipe_selection_frame.py            # Add render_saved_selections() method
        └── fg_selection_frame.py                # Add render_saved_selections() method

src/
└── tests/
    └── (regression tests for planning tab load)
```

**Structure Decision**: Existing single-project structure. No new files created — only modifications to 3 existing UI files plus test additions.

## Design

### Change 1: RecipeSelectionFrame — Add `render_saved_selections()`

**File**: `src/ui/components/recipe_selection_frame.py`

**New method** that queries Recipe objects by the IDs in `_selected_recipe_ids` and renders them:

1. Guard: if `_selected_recipe_ids` is empty, do nothing (preserve blank placeholder)
2. Query: Use `session_scope()` to fetch `Recipe` objects matching `_selected_recipe_ids`
3. Add contextual label: Insert a "Saved plan selections" label before the recipe list
4. Render: Call existing `_render_recipes(recipes)` with the fetched recipes
5. All recipes will appear checked because `_render_recipes()` already reads from `_selected_recipe_ids` (line 222)

**Pattern reference**: Follows the same query-then-render pattern as FGSelectionFrame's `_render_selected_only()` (lines 775-788).

**Contextual label**: Add a muted italic label ("Saved plan selections") at the top of the scroll frame. This label is destroyed when `_render_recipes()` is called by a filter (since it clears all children at line 200-201).

### Change 2: FGSelectionFrame — Add `render_saved_selections()`

**File**: `src/ui/components/fg_selection_frame.py`

**New method** that leverages existing `_render_selected_only()`:

1. Guard: if `_selected_fg_ids` is empty, do nothing (preserve blank placeholder)
2. Set visual state: `_show_selected_only = True`, update button text to "Show Filtered View"
3. Update indicator: Set `_selected_indicator` to "Saved plan selections (N items)"
4. Call: `_render_selected_only()` — this queries FG objects and renders them

**Why not call `_render_selected_only()` directly from planning_tab.py**: The method is private (`_render_selected_only`). A public `render_saved_selections()` wrapper encapsulates the state setup and provides a clean API.

**Filter transition**: When user applies a filter, `_on_filter_change()` is called. It checks `_show_selected_only` (line 276-279) and exits that mode, which is exactly the correct transition behavior.

### Change 3: PlanningTab — Trigger render after data load

**File**: `src/ui/planning_tab.py`

**In `_show_recipe_selection()`** (after line 614):
- After `self._recipe_selection_frame.set_selected(selected_ids)`, add:
- `if selected_ids: self._recipe_selection_frame.render_saved_selections()`

**In `_show_fg_selection()`** (after line 777):
- After `self._fg_selection_frame.set_selected_with_quantities(qty_tuples)`, add:
- `if qty_tuples: self._fg_selection_frame.render_saved_selections()`

Both are single-line additions — the conditional preserves blank-start for events with no selections.

### Contextual Label Design

Both frames display a contextual label when showing saved selections:

- **Text**: "Saved plan selections" (recipe frame) / "Saved plan selections (N items)" (FG frame)
- **Style**: Italic, muted color (`gray50`/`gray60`), matching placeholder style
- **Lifecycle**: Destroyed automatically when user applies a filter (render methods clear all children before re-rendering)
- **FG frame**: Uses existing `_selected_indicator` label (already positioned correctly)
- **Recipe frame**: Adds a label to the scroll frame before rendering recipes

### State Diagram

```
Event selected in Planning tab
│
├── Has saved selections?
│   ├── YES → set_selected() + render_saved_selections()
│   │         → Show saved items with contextual label
│   │         → User applies filter?
│   │              → Transition to filtered view (selections pre-checked)
│   │
│   └── NO  → set_selected([]) → Show blank placeholder (unchanged)
│            → User applies filter?
│                 → Normal filter-first workflow (unchanged)
```

## Complexity Tracking

No constitution violations. No complexity justifications needed.
