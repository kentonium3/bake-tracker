# Technical Debt Register

This document tracks known technical debt items in the Bake Tracker codebase. Items are prioritized and addressed as part of regular maintenance or when they become blocking issues.

## Status Legend

| Status | Description |
|--------|-------------|
| Open | Identified but not yet addressed |
| In Progress | Currently being worked on |
| Deferred | Intentionally postponed |
| Resolved | Fixed and verified |

## Priority Legend

| Priority | Description |
|----------|-------------|
| High | Causes confusion, bugs, or blocks features |
| Medium | Should be addressed in next major version |
| Low | Nice to have, address opportunistically |

---

## Open Items

### TD-001: Misleading `unit_price` Field Name in Purchase Model

| Attribute | Value |
|-----------|-------|
| **Status** | Deferred |
| **Priority** | Low |
| **Created** | 2025-12-28 |
| **Location** | `src/models/purchase.py`, export views |

**Description:**

The `unit_price` field in the Purchase model and related exports (e.g., `view_purchases.json`) is named misleadingly. In grocery store terminology, "unit price" refers to the normalized cost per standardized unit (e.g., $0.36/oz or $5.75/lb as shown on shelf tags).

In this codebase, `unit_price` actually means **package price** - the price paid for one package/unit at checkout.

**Current Behavior:**
- `unit_price` = price paid for one package (e.g., $8.99 for a 5lb bag)
- `total_cost` = `unit_price * quantity_purchased`

**Suggested Fix:**

Rename `unit_price` to `package_price` or `item_price` across:
- `src/models/purchase.py`
- All service functions that reference it
- Export/import schemas
- Test files
- UI components

**Migration Required:** Yes - database column rename + data export format change

**Reason for Deferral:**

Low user impact (field behaves correctly, just named confusingly). Rename would require database migration and breaking changes to export formats.

---

### TD-004: Hierarchy Path Cache N+1 Query Performance

| Attribute | Value |
|-----------|-------|
| **Status** | Open |
| **Priority** | Low |
| **Created** | 2026-01-02 |
| **Feature** | F033 |
| **Location** | `src/ui/ingredients_tab.py:285-334` |

**Description:**

The `_build_hierarchy_path_cache()` method makes a separate `get_ancestors()` DB call for each non-L0 ingredient. For large ingredient lists, this N+1 pattern could cause noticeable UI lag on refresh.

**Suggested Fix:**

Build paths in-memory using already-loaded ingredient data with `parent_ingredient_id`, or add a bulk service function that returns all ingredients with precomputed paths.

See: `docs/technical-debt/TD-004_hierarchy_path_cache_n_plus_1.md`

---

### TD-005: can_change_parent() new_level Edge Case

| Attribute | Value |
|-----------|-------|
| **Status** | Open |
| **Priority** | Very Low |
| **Created** | 2026-01-02 |
| **Feature** | F033 |
| **Location** | `src/services/ingredient_hierarchy_service.py:683-706` |

**Description:**

When `can_change_parent()` is called with an invalid `new_parent_id`, the returned `new_level` defaults to `0` instead of indicating the level is unknown. This is cosmetic - the `allowed` field will be `False` so the invalid level won't be acted upon.

**Suggested Fix:**

Return `new_level: None` when parent lookup fails, and update UI to display "(Invalid parent)" for unknown levels.

See: `docs/technical-debt/TD-005_can_change_parent_new_level_edge_case.md`

---

## Resolved Items

*No resolved items yet.*
