# Research: Phase 1 Ingredient Hierarchy Fixes

**Feature**: `033-phase-1-ingredient`
**Date**: 2026-01-02
**Status**: Complete

## Executive Summary

This feature fixes conceptual issues in F032's ingredient hierarchy implementation. Research focused on understanding the current implementation state and determining the minimal changes needed.

## Key Decisions

### Decision 1: Remove Level Selector, Compute from Parent

**Decision**: Remove the explicit `ingredient_level_dropdown` from the inline edit form. Display level as read-only text computed from parent selection.

**Rationale**:
- Current UI has BOTH level selector AND parent selectors - conceptually conflicting
- Level is deterministic: no parent = L0, L0 parent = L1, L1 parent = L2
- User should select parent; level follows automatically
- Reduces cognitive load and eliminates impossible states

**Evidence**:
- Code review of `src/ui/ingredients_tab.py:866-924` shows hybrid implementation
- Gap analysis in `docs/requirements/req_ingredients_GAP_ANALYSIS.md` identified this as critical issue

**Alternatives Considered**:
- Keep level selector with validation → Rejected: still allows conceptual confusion
- Hide level entirely → Rejected: users need to see hierarchy position

### Decision 2: Informational Warnings Only (Non-Blocking)

**Decision**: When changing an ingredient's parent, display informational warnings inline. No confirmation dialogs required.

**Rationale**:
- Changing parent doesn't break product relationships - just reorganizes taxonomy
- Products still link to the same ingredient; only categorization changes
- Blocking dialogs create friction for safe operations
- User explicitly requested non-blocking approach

**Evidence**:
- Planning interview: "there is no negative consequence to a product by having its ingredient change categories"
- Product-Ingredient FK uses `ingredient_id`, not hierarchy path

**Alternatives Considered**:
- Blocking confirmation for products → Rejected: no actual data risk
- Different behavior for products vs children → Rejected: inconsistent UX

### Decision 3: Deprecate Legacy ingredient_form.py

**Decision**: Mark `src/ui/forms/ingredient_form.py` for deprecation. Do not update it with hierarchy support.

**Rationale**:
- Legacy dialog uses category dropdown (pre-hierarchy design)
- Inline form in ingredients_tab.py is the primary interface
- Maintaining two forms creates inconsistency and double maintenance
- Future work should remove legacy dialog entirely

**Evidence**:
- Code review shows legacy form has no hierarchy fields
- Inline form already has (flawed) hierarchy implementation to fix

**Alternatives Considered**:
- Update both forms → Rejected: doubles work, legacy form rarely used
- Remove legacy form now → Rejected: out of scope for this fix feature

### Decision 4: Reuse Existing Hierarchy Functions

**Decision**: Build new convenience functions on top of existing `ingredient_hierarchy_service.py` functions rather than rewriting.

**Rationale**:
- `validate_hierarchy()` already handles cycle detection, depth validation
- `get_children()` and `get_descendants()` already exist
- `get_ancestors()` can build hierarchy path
- New functions are thin wrappers with consistent return format

**Evidence**:
- Code review of `src/services/ingredient_hierarchy_service.py` shows complete validation logic
- Functions tested and working in F031/F032

**Alternatives Considered**:
- Duplicate validation logic in new functions → Rejected: DRY violation
- Refactor existing functions → Rejected: unnecessary churn, may break existing code

## Data Model Impact

No schema changes required. This feature only modifies:
- Service layer (new convenience functions)
- UI layer (form restructuring, display column)

See `data-model.md` for entity documentation.

## Open Questions

None - all planning questions resolved during discovery.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Regression in ingredient CRUD | Low | High | Comprehensive test coverage; run existing tests |
| User confusion during transition | Low | Medium | Clear level display shows computed value |
| Legacy form usage unknown | Low | Low | Add deprecation warning to legacy form |

## Sources

| ID | Source | Type | Relevance |
|----|--------|------|-----------|
| S1 | `src/ui/ingredients_tab.py` | Code | Current hybrid implementation |
| S2 | `src/services/ingredient_hierarchy_service.py` | Code | Existing validation functions |
| S3 | `docs/requirements/req_ingredients_GAP_ANALYSIS.md` | Doc | Gap analysis driving this feature |
| S4 | Planning interview 2026-01-02 | Interview | Form scope and warning behavior decisions |
