# Research: Streamlined Inventory Entry

**Feature**: 029-streamlined-inventory-entry
**Created**: 2025-12-24
**Status**: Complete

## Executive Summary

This research validates the technical approach for transforming inventory entry from a 15-20 minute workflow to a 5-minute flow-optimized experience. Key decisions are grounded in existing codebase patterns and user-confirmed architectural preferences.

## Research Questions

### RQ-001: Session State Architecture

**Question**: Where should session state (last supplier, last category) be stored?

**Decision**: Application-level SessionState singleton in `src/ui/session_state.py`

**Rationale**:
- Matches spec intent: "In-memory singleton for session memory"
- Follows bake-tracker patterns: UI layer owns UI-related state
- Clear ownership: SessionState class owns session memory
- Testable: `state.reset()` provides clean test isolation
- Simple: No parameter passing, no global module state
- Explicit: Import and use, not hidden in service layer

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| Module-level global dict | Harder to test, implicit coupling |
| UI-owned state in dialog | Requires passing state through call chain |
| Database persistence | Over-engineering for session-only data |

**Evidence**: Planning discussion 2025-12-24, user confirmation

---

### RQ-002: Type-Ahead Widget Implementation

**Question**: How should type-ahead filtering be implemented for dropdowns?

**Decision**: Custom `TypeAheadComboBox` widget in `src/ui/widgets/type_ahead_combobox.py`

**Rationale**:
- Reusable: 3 dropdowns in F029, potential future use
- Testable: Widget isolated from dialog logic
- Maintainable: Filtering logic in one place
- Follows CTk patterns: Frame wrapper is standard approach
- Pragmatic: Focus on filtering algorithm, not dropdown UI

**Implementation Notes**:
- Subclass `CTkFrame`, wrap `CTkComboBox`
- Implement filtering logic (contains + word boundary prioritization)
- Do NOT override CTk's dropdown rendering (use built-in)
- Do NOT reimplement keyboard navigation (use CTk's native)
- Focus on filtering algorithm correctness

**Evidence**: Design document F029, planning discussion 2025-12-24

---

### RQ-003: Recency Query Location

**Question**: Where should recency intelligence queries live?

**Decision**: Extend `src/services/inventory_item_service.py` with recency query methods

**Rationale**:
- Recency queries fundamentally about inventory item history
- Co-located with existing inventory logic
- Avoids creating new service for 2-3 methods
- Consistent with existing service organization

**Methods to Add**:
- `get_recent_products(ingredient_id, days=30, min_frequency=3, frequency_days=90)`
- `get_recent_ingredients(category, days=30, min_frequency=3, frequency_days=90)`

**Evidence**: Planning discussion 2025-12-24, codebase analysis

---

### RQ-004: Recency Definition

**Question**: What constitutes a "recent" product or ingredient?

**Decision**: Hybrid temporal + frequency approach

**Criteria** (item is recent if EITHER condition is true):
1. **Temporal**: Added within last 30 days
2. **Frequency**: Added 3+ times in last 90 days

**Rationale**:
- Temporal alone misses frequently-used items from 45 days ago
- Frequency alone misses new items used only once
- Hybrid captures both "recent purchase" and "regular purchase" patterns

**Evidence**: Feature spec FR-006, design document

---

### RQ-005: Inline Product Creation UI Pattern

**Question**: How should inline product creation be implemented?

**Decision**: Collapsible accordion form within AddInventoryDialog

**Behavior**:
- [+ New Product] button triggers accordion expansion
- Form appears inline, no separate modal
- Pre-fills: Ingredient (read-only), Supplier (from session), Unit (smart default)
- On Create: Collapses, adds product to dropdown, auto-selects
- On Cancel: Collapses, returns focus to Product dropdown

**Rationale**:
- Maintains workflow continuity (no modal switching)
- Clear visual hierarchy (accordion clearly subordinate)
- Reversible action (Cancel collapses without changes)

**Evidence**: Design document wireframe, spec FR-016 through FR-021

---

### RQ-006: Category-to-Unit Default Mapping

**Question**: What default package units should apply to each category?

**Decision**: Configurable mapping dictionary

| Category | Default Unit | Rationale |
|----------|--------------|-----------|
| Baking | lb | Flour, sugar sold by weight |
| Chocolate | oz | Chips, bars in smaller quantities |
| Dairy | lb | Butter by weight |
| Spices | oz | Small quantities |
| Liquids | fl oz | Extracts, oils by volume |
| Nuts | lb | Sold by weight |
| Fruits | lb | Dried fruits by weight |
| Sweeteners | lb | Honey, syrups by weight |
| Leavening | oz | Baking powder/soda small qty |
| Oils | fl oz | By volume |
| Grains | lb | Oats, specialty flours |
| Default | lb | Fallback for unknown categories |

**Evidence**: Design document, user workflow analysis

---

### RQ-007: Price Suggestion Behavior

**Question**: How should price suggestions work?

**Decision**: Two-tier fallback with inline hints

**Behavior**:
1. **Primary**: Query last purchase price at selected supplier
   - Display: Pre-fill price, show "(last paid: $X.XX on MM/DD)"
2. **Fallback**: If no price at selected supplier, query any supplier
   - Display: Pre-fill price, show "(last paid: $X.XX at [Supplier] on MM/DD)"
3. **No History**: Leave price blank, show "(no purchase history)"

**Rationale**:
- Primary gives exact supplier context
- Fallback provides useful reference even for new supplier
- Inline hints non-intrusive but informative

**Evidence**: Spec FR-024 through FR-026, design document

---

## Codebase Analysis

### Existing Patterns Discovered

**Service Layer Organization** (`src/services/`):
- Services follow `operation_name()` with optional `session=None` parameter
- Implementation pattern: public function wraps `_impl()` for session handling
- Example: `inventory_item_service.py` follows this pattern

**UI Widget Patterns** (`src/ui/`):
- CustomTkinter widgets use Frame wrappers for composition
- Dialogs extend `CTkToplevel`
- No existing type-ahead implementation found

**Purchase History** (from F028):
- `Purchase` model tracks product/supplier/price/date
- `purchase_service.py` provides history queries
- Already supports `get_last_purchase_price()` queries

### Files to Modify

| File | Changes |
|------|---------|
| `src/services/inventory_item_service.py` | Add recency query methods |
| `src/ui/session_state.py` | **NEW** - SessionState singleton |
| `src/ui/widgets/type_ahead_combobox.py` | **NEW** - TypeAheadComboBox widget |
| `src/ui/widgets/dropdown_builders.py` | **NEW** - Recency-aware dropdown builders |
| `src/ui/dialogs/add_inventory_dialog.py` | Major refactor for new workflow |
| `src/utils/category_defaults.py` | **NEW** - Category-to-unit mapping |

### Files to Reference (Read-Only)

| File | Purpose |
|------|---------|
| `src/models/inventory_item.py` | InventoryItem model structure |
| `src/models/product.py` | Product model structure |
| `src/services/purchase_service.py` | Price query patterns |
| `src/ui/dialogs/` | Dialog implementation patterns |

---

## Open Questions

### OQ-001: Recency Cache Strategy (RESOLVED)

**Question**: Should recency results be cached during session?

**Resolution**: Yes, cache per-dialog-open. Refresh on successful Add to pick up new entries.

### OQ-002: Type-Ahead Debouncing (RESOLVED)

**Question**: Should keystroke filtering be debounced?

**Resolution**: Start without debouncing. Client-side filtering of <500 items should be instant. Add 200ms debounce if performance issues observed.

### OQ-003: Separator Rendering (RESOLVED)

**Question**: How to render separator in CTkComboBox dropdown?

**Resolution**: Use Unicode line character "─────────────────────────────" as dropdown value. Non-selectable behavior handled by ignoring separator selection.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Type-ahead performance lag | Low | Medium | Client-side filtering, limit results to 20 |
| Session state loss on crash | Medium | Low | Documented as expected behavior |
| Smart defaults don't match products | Low | Low | All defaults editable by user |
| Recency query performance | Low | Medium | Index on addition_date, cache results |
| UI complexity overwhelming | Medium | Medium | Progressive disclosure, user testing |

---

## References

- Feature Specification: `kitty-specs/029-streamlined-inventory-entry/spec.md`
- Design Document: `docs/design/F029_streamlined_inventory_entry.md`
- Constitution: `.kittify/memory/constitution.md`
- F027 (Products): `kitty-specs/027-product-catalog-management/`
- F028 (Purchases): `kitty-specs/028-purchase-tracking-enhanced/`
