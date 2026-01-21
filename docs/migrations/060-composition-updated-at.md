# Schema Change: Composition.updated_at

**Feature**: F060 - Architecture Hardening Service Boundaries
**Work Package**: WP05 - Staleness Detection Enhancements
**Date**: 2026-01-21

## Change Summary

Added `updated_at` column to the `compositions` table to enable tracking of composition modifications for staleness detection.

### New Column

| Column | Type | Nullable | Default | On Update |
|--------|------|----------|---------|-----------|
| `updated_at` | DateTime | No | `utc_now()` | `utc_now()` |

## Purpose

Previously, staleness detection only checked `Composition.created_at`, which meant that modifications to existing compositions (e.g., changing the quantity of cookies in a gift box) would not trigger a plan recalculation. This could lead to incorrect production plans.

With `updated_at`, the planning service now detects when:
- A new composition is added (via `created_at`)
- An existing composition is modified (via `updated_at`)

## Migration Required

Per constitution principle VI (Desktop Phase), schema changes use export/reset/import:

1. **Export data**: Use the app's Export function to save all data to JSON
2. **Close the application**
3. **Delete the database**: Remove `bake_tracker.db` file from the data directory
4. **Restart the application**: Database will be recreated with the new schema
5. **Import data**: Use the app's Import function to restore data

## Impact

- Existing compositions will have `updated_at = created_at` after import
- No data loss expected
- Staleness detection will now properly track composition modifications
- Plans will be marked stale when bundle compositions change

## Related Changes

This schema change also includes enhanced staleness detection for:
- `FinishedUnit.updated_at` - already existed, now checked for yield changes

## Testing

Verify staleness detection works correctly:
1. Create an event with assembly targets
2. Calculate a production plan
3. Modify a composition's quantity
4. Verify the plan is marked as stale
