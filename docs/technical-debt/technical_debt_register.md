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

## Resolved Items

*No resolved items yet.*
