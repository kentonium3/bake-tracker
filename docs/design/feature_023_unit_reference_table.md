# Feature 023: Unit Reference Table & UI Constraints

## Problem Statement

Units are stored as free-form strings with application-level validation only. While TD-002 added import validation, the UI still allows arbitrary unit entry. This creates risk of typos, inconsistent representations, and blocks future UN/CEFACT code adoption.

## Goals

1. Create a database-backed unit reference table as the single source of truth for valid units
2. Enforce unit selection in UI via dropdowns/comboboxes (no free-form entry)
3. Maintain backward compatibility with existing data
4. Prepare for future UN/CEFACT code adoption without requiring it now

## Proposed Solution

### Schema: `units` Reference Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `code` | String(10) UNIQUE | Short code (e.g., "oz", "cup", "lb") |
| `name` | String(50) | Full name (e.g., "ounce", "cup", "pound") |
| `symbol` | String(20) | Display symbol (e.g., "oz", "cup", "lb") |
| `category` | String(20) | "weight", "volume", "count", "package" |
| `uncefact_code` | String(10) NULL | Future: UN/CEFACT code (e.g., "ONZ", "G94", "LBR") |

### Seed Data

Populate from `src/utils/constants.py`:
- Weight: oz, lb, g, kg
- Volume: tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
- Count: each, count, piece, dozen
- Package: bag, box, bar, bottle, can, jar, packet, container, package, case

### UI Changes

Replace free-form text entry with dropdowns for:
- Product: `package_unit` field
- Ingredient: `density_volume_unit`, `density_weight_unit` fields
- Recipe Ingredient: `unit` field
- Recipe: `yield_unit` field (may need combined list or "other" option)

Dropdown behavior:
- Searchable/filterable for quick selection
- Grouped by category (Weight, Volume, Count, Package)
- Show symbol as display, store code in database

### Validation

- Application-level validation against units table (replaces constants.py lookups)
- Import validation unchanged (already validates against constants.py)
- Consider: Should constants.py be deprecated in favor of DB queries?

## Reference Documents

- `docs/design/unit_codes_reference.md` — UN/CEFACT standard reference
- `docs/research/unit_handling_analysis_report.md` — Current state analysis
- `docs/technical-debt/TD-002_unit_standardization.md` — Completed prerequisite

## Non-Scope

- Full UN/CEFACT code enforcement (codes stored but aliases used in UI)
- Unit conversion logic changes (stays in unit_converter.py)
- Import format changes (already standardized in TD-002)
- Localization/internationalization

## Acceptance Criteria

1. `units` table exists with all valid units seeded
2. All UI unit inputs use dropdowns populated from the units table
3. No free-form unit entry possible in UI
4. Existing data with valid units continues to work
5. All tests pass
6. Export/import round-trips preserve unit values
