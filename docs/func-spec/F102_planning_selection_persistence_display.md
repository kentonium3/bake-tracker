# F102: Planning Selection Persistence Display

**Version**: 1.0
**Priority**: HIGH
**Type**: UI Enhancement

**Created**: 2026-02-28
**Status**: Draft

---

## Executive Summary

When returning to the Planning tab for an event with a saved draft plan, the Recipe and Finished Goods selection areas appear blank — showing placeholder text like "Select recipe category to see available recipes" despite the event having persisted selections that feed the visible batch calculations below. This creates a confusing disconnect: the user sees batch results but not the inputs that produced them.

Current gaps:
- ❌ Recipe selection frame shows blank placeholder when event has saved recipe selections
- ❌ FG selection frame shows blank placeholder when event has saved FG selections with quantities
- ❌ User cannot see what choices produced the batch calculations without re-applying filters
- ❌ Re-selecting recipes/FGs risks overwriting the existing plan

This spec makes saved selections visible on load so the planning workspace displays a coherent view of the plan in progress.

---

## Problem Statement

**Current State (BLANK SELECTION FRAMES ON RELOAD):**
```
Planning Tab — Event with saved draft plan
├─ Recipe Selection Frame
│  ├─ ❌ Shows "Select recipe category to see available recipes" placeholder
│  ├─ ❌ No indication of which recipes were selected
│  ├─ ✅ Count label shows "0 of 0 shown selected (N total)" — count is correct but unhelpful
│  └─ ✅ Internal _selected_recipe_ids set IS populated from database
│
├─ FG Selection Frame
│  ├─ ❌ Shows "Select filters to see available finished goods" placeholder
│  ├─ ❌ No indication of which FGs were selected or their quantities
│  └─ ✅ Internal _selected_fg_ids and _fg_quantities ARE populated from database
│
├─ Batch Options
│  └─ ✅ Shows batch calculations (user sees results but not inputs)
│
└─ Confusing User Experience
   ├─ ❌ Disconnect between blank selections and populated batch results
   ├─ ❌ Appears as if selections need to be made again
   └─ ❌ Re-selecting could overwrite existing plan choices
```

**Target State (SAVED SELECTIONS VISIBLE ON LOAD):**
```
Planning Tab — Event with saved draft plan
├─ Recipe Selection Frame
│  ├─ ✅ Shows saved recipes with checkboxes checked
│  ├─ ✅ User immediately sees which recipes are part of the plan
│  ├─ ✅ Count label accurate and visible
│  └─ ✅ Filters still available for browsing/modifying
│
├─ FG Selection Frame
│  ├─ ✅ Shows saved FGs with checkboxes checked and quantities displayed
│  ├─ ✅ User immediately sees FG selections and their quantities
│  ├─ ✅ Count label accurate and visible
│  └─ ✅ Filters still available for browsing/modifying
│
├─ Batch Options
│  └─ ✅ Shows batch calculations (inputs now visible above)
│
└─ Coherent User Experience
   ├─ ✅ Selection inputs visually connected to batch calculation outputs
   ├─ ✅ User understands the current plan at a glance
   └─ ✅ Can modify selections through normal filter workflow
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Planning Tab Load Flow**
   - Find: `src/ui/planning_tab.py`
   - Study: `_show_recipe_selection()` (lines 579-627) — loads saved IDs, calls `set_selected()` but no render triggered
   - Study: `_show_fg_selection()` (lines 749-790) — loads saved FG+quantities, calls `set_selected_with_quantities()` but no render triggered
   - Note: Both frames are packed blank; data is in memory but invisible

2. **Recipe Selection Frame**
   - Find: `src/ui/components/recipe_selection_frame.py`
   - Study: `set_selected()` (lines 290-303) — updates persistence set and visible checkbox vars, but only for already-rendered recipes
   - Study: `_render_recipes()` (lines 189-233) — the render method that creates checkboxes; respects `_selected_recipe_ids` at line 222
   - Note: When frame loads blank, `_recipe_vars` dict is empty — `set_selected()` has nothing to check
   - Note: `_update_count()` (lines 264-278) — shows "N total" even when recipes not rendered

3. **FG Selection Frame**
   - Find: `src/ui/components/fg_selection_frame.py`
   - Study: `set_selected_with_quantities()` (lines 519-550) — updates persistence but only checks visible widgets
   - Study: `_toggle_show_selected()` (lines 750-773) — existing "Show All Selected" toggle renders only selected FGs
   - Study: `_render_selected_only()` (line 775+) — already renders a filtered view of only selected items
   - Note: This existing mechanism is very close to what's needed for the initial load display

4. **Event Service Persistence**
   - Find: `src/services/event_service.py`
   - Study: `get_event_recipe_ids()` — retrieves saved recipe IDs for event
   - Study: `get_event_fg_quantities()` — retrieves saved FG+quantity pairs for event
   - Note: Both return correct data; the issue is purely in the UI rendering

---

## Requirements Reference

This specification addresses:
- **User feedback**: Plan selections should be visible when returning to a draft plan
- **UX coherence**: Selection inputs must be visually connected to batch calculation outputs
- **Data safety**: User must not be misled into re-selecting when selections already exist

From: User testing feedback (2026-02-28)

---

## Functional Requirements

### FR-1: Display Saved Recipe Selections on Load

**What it must do:**
- When an event with existing recipe selections is loaded, display the selected recipes immediately
- Show selected recipes with checkboxes checked, matching the appearance of a manually filtered view
- Selection count label must reflect the saved selections accurately
- Category filter must remain available for browsing or modifying selections

**Behavior by event state:**
- **Event with saved recipes**: Render saved recipes on load (checked checkboxes visible)
- **Event with NO saved recipes**: Show current blank placeholder (unchanged)
- **New event**: Show current blank placeholder (unchanged)

**Pattern reference:** Study how `_render_recipes()` already reads from `_selected_recipe_ids` when creating checkboxes — the render path respects saved state, it just isn't called on load

**Success criteria:**
- [ ] Saved recipes visible immediately when event with selections is loaded
- [ ] Checkboxes shown as checked for saved recipes
- [ ] Selection count label accurate on load
- [ ] Category filter still functional for browsing/modifying
- [ ] Events with no saved recipes show blank placeholder (no regression)

---

### FR-2: Display Saved FG Selections with Quantities on Load

**What it must do:**
- When an event with existing FG selections is loaded, display the selected FGs with their quantities immediately
- Show selected FGs with checkboxes checked and quantity values populated
- Selection count label must reflect the saved selections accurately
- Filter dropdowns must remain available for browsing or modifying selections

**Behavior by event state:**
- **Event with saved FGs**: Render saved FGs on load (checked checkboxes + quantities visible)
- **Event with NO saved FGs**: Show current blank placeholder (unchanged)

**Pattern reference:** Study `_render_selected_only()` and `_toggle_show_selected()` in fg_selection_frame.py — the "Show All Selected" mode already renders only selected FGs. This is very close to the needed behavior on initial load.

**Success criteria:**
- [ ] Saved FGs visible immediately when event with selections is loaded
- [ ] Checkboxes shown as checked for saved FGs
- [ ] Quantities displayed in entry fields for each saved FG
- [ ] Selection count label accurate on load
- [ ] Filter dropdowns still functional for browsing/modifying
- [ ] Events with no saved FGs show blank placeholder (no regression)

---

### FR-3: Clear Visual Context Connecting Selections to Calculations

**What it must do:**
- The visible recipe and FG selections must appear as plan inputs that clearly feed the batch calculation section below
- User must be able to see, at a glance: "these recipes + these FGs at these quantities = these batch calculations"
- The display must not suggest that selections need to be re-made

**UI Requirements:**
- Saved selection display should be visually consistent with the appearance after a manual filter+select workflow
- A label or indicator should communicate that these are the saved plan selections (not a filter result)
- The transition from "viewing saved selections" to "filtering/modifying" must be smooth and obvious

**Success criteria:**
- [ ] User can see recipe selections, FG selections, and batch calculations together
- [ ] Display does not suggest selections need to be re-entered
- [ ] User understands they are viewing the current saved plan
- [ ] Modifying selections follows the existing filter workflow naturally

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Edit mode with amendment tracking (F-PLAN-010 / F078 — separate feature)
- ❌ Plan state guards (preventing edits in LOCKED/IN_PRODUCTION — F103)
- ❌ New filter patterns or progressive disclosure changes (F100 already covers this)
- ❌ Batch calculation display changes (already working correctly)
- ❌ Shopping summary or assembly status changes (already working correctly)
- ❌ Changes to save/cancel workflow (already working correctly)

---

## Success Criteria

**Complete when:**

### Selection Display
- [ ] Recipe selections visible on load for events with saved recipes
- [ ] FG selections with quantities visible on load for events with saved FGs
- [ ] Selection count labels accurate on initial display
- [ ] Blank placeholder shown for events with no selections (no regression)

### User Experience
- [ ] User sees a coherent plan view: selections → batch calculations
- [ ] No confusion about whether selections need to be re-made
- [ ] Returning to planning tab shows current plan state immediately
- [ ] App relaunch preserves plan display (selections loaded from database)

### Filter Workflow Preserved
- [ ] Category filter still works for recipe browsing/modification
- [ ] FG filter dropdowns still work for browsing/modification
- [ ] "Show All Selected" toggle in FG frame still functions
- [ ] Save/Cancel workflow unchanged
- [ ] Selection persistence across filter changes unchanged

### Quality
- [ ] No regressions in new event (blank start) workflow
- [ ] No regressions in save/cancel behavior
- [ ] No regressions in batch calculation downstream
- [ ] Performance acceptable (rendering saved selections must be fast)

---

## Architecture Principles

### Minimal Change, Maximum Impact

**This is a targeted rendering fix, not an architectural change:**
- The database persistence layer is correct and unchanged
- The in-memory persistence layer (`_selected_recipe_ids`, `_selected_fg_ids`) is correct and unchanged
- The render methods already respect saved state — they just need to be called at the right time
- The "Show All Selected" mechanism in FGSelectionFrame is a near-exact precedent

### Preserve Filter-First for New Plans

**Blank start behavior must be preserved for events with no selections:**
- The F099/F100 progressive disclosure pattern remains correct for new plans
- Only events with existing database-persisted selections get the pre-populated display
- The conditional is straightforward: if selections exist → render them; if not → show placeholder

### No Business Logic in UI

**The rendering change stays in the UI layer:**
- Service layer queries are already correct (`get_event_recipe_ids()`, `get_event_fg_quantities()`)
- No new service functions needed
- The fix is purely about calling existing render methods after existing data load

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design & Workflow Validation**
- Eliminates confusing disconnect between blank selections and populated batch results
- User immediately sees the complete plan state without manual filter interaction
- Addresses direct user feedback from testing

✅ **Principle V: Layered Architecture Discipline**
- Fix is purely in UI rendering layer
- No service or model changes needed
- Existing service queries are correct and unchanged

✅ **Principle VI.G: Code Organization Patterns**
- Leverages existing render methods rather than creating new ones
- Leverages existing "Show All Selected" pattern in FGSelectionFrame
- Minimal new code expected

---

## Risk Considerations

**Risk: Interaction between pre-populated display and filter workflow**
- Context: User sees saved selections, then selects a category filter — what happens to the display?
- Mitigation: Planning phase must determine the transition behavior. Natural approach: applying a filter replaces the "saved selections" view with the filtered view, and selections persist in memory as they do today. The "Show All Selected" button returns to the full selected view.

**Risk: Performance rendering saved selections**
- Context: An event could have 50+ selected recipes or FGs
- Mitigation: The existing render methods already handle similar list sizes. Profile if needed during implementation.

**Risk: Visual consistency between "saved selections" view and "filtered" view**
- Context: The pre-populated display should look consistent with the filtered result display to avoid confusion
- Mitigation: Planning phase should use the same render methods for both views. The FG frame's `_render_selected_only()` is the model to follow.

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `_render_selected_only()` in fg_selection_frame.py → model for rendering only saved items on load
- Study `_render_recipes()` in recipe_selection_frame.py → understand how it reads `_selected_recipe_ids`
- Study `_show_recipe_selection()` in planning_tab.py → understand where to trigger render after `set_selected()`
- Study `_show_fg_selection()` in planning_tab.py → understand where to trigger render after `set_selected_with_quantities()`

**Key Patterns to Copy:**
- FGSelectionFrame `_render_selected_only()` → adapt for initial load display
- RecipeSelectionFrame `_render_recipes()` → call after `set_selected()` with saved recipe data

**Focus Areas:**
- **Conditional rendering**: Render saved selections only when they exist; preserve blank start otherwise
- **Transition behavior**: Define what happens when user starts filtering after viewing saved selections
- **Visual labeling**: Indicate the user is viewing "saved plan selections" vs a filter result
- **Minimal code change**: The fix should be small — the infrastructure already exists

**Estimated Scope:**
- Small feature — primarily wiring existing render calls at the right points
- Recipe frame: fetch saved recipe objects, call render method after set_selected()
- FG frame: trigger `_render_selected_only()` (or similar) after `set_selected_with_quantities()` when selections exist

---

**END OF SPECIFICATION**
