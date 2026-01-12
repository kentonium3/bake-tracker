# Implementation Plan: Import/Export System Phase 1

**Branch**: `049-import-export-phase1` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/049-import-export-phase1/spec.md`

## Summary

Implement Phase 1 of the Import/Export System upgrade to:
1. Complete full backup capability (all 16 entities with manifest)
2. Add materials catalog import (matching ingredient import pattern)
3. Expand context-rich exports to ingredients, materials, recipes
4. Add transaction imports (purchases and inventory adjustments)
5. Auto-detect import format (normalized vs context-rich)
6. Redesign UI to distinguish export types and import purposes

**Technical Approach**: Extend existing service architecture (coordinated_export_service, catalog_import_service, denormalized_export_service) rather than creating new services. Leverage existing patterns for consistency and maintainability.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service coverage
**Target Platform**: Desktop (macOS, Windows)
**Project Type**: Single desktop application
**Performance Goals**: Import/export operations complete within 30-60 seconds for typical data volumes
**Constraints**: Must support round-trip export/import without data loss; slug-based FK references only
**Scale/Scope**: Single-user desktop app with ~500 recipes, ~300 ingredients, ~200 products

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| **I. User-Centric Design** | Feature addresses real user needs (backup safety, AI workflows, mobile companion) | PASS |
| **II. Data Integrity** | Slug-based references preserve referential integrity; no database IDs in exports | PASS |
| **III. Future-Proof Schema** | Export format supports future schema expansion via optional nullable fields | PASS |
| **IV. Test-Driven Development** | All new service methods require unit tests | REQUIRED |
| **V. Layered Architecture** | All business logic in services layer; UI layer only calls services | REQUIRED |
| **VI. Schema Change Strategy** | Full backup enables reset/re-import workflow for schema changes | PASS |
| **VII. AI-Forward Foundation** | Purchase and inventory imports support BT Mobile AI workflows | PASS |

**Desktop Phase Checks (Current)**:
- Does this design block web deployment? **NO** - Service layer is UI-independent
- Is the service layer UI-independent? **YES** - All logic in services
- Does this support AI-assisted JSON import? **YES** - Core purpose
- Web migration cost: **LOW** - Same services, just API wrapper needed

## Project Structure

### Documentation (this feature)

```
kitty-specs/049-import-export-phase1/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── tasks/               # Work packages
│   ├── planned/
│   ├── doing/
│   └── done/
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
src/
├── models/              # No changes - existing models sufficient
├── services/
│   ├── coordinated_export_service.py   # EXTEND - Add 8 missing entities
│   ├── catalog_import_service.py       # EXTEND - Add materials support
│   ├── denormalized_export_service.py  # EXTEND - Add context-rich views
│   ├── enhanced_import_service.py      # EXTEND - Add format auto-detection
│   └── transaction_import_service.py   # NEW - Purchase/adjustment imports
└── ui/
    └── dialogs/
        └── import_export_dialog.py     # EXTEND - Redesigned UI

src/tests/
├── services/
│   ├── test_coordinated_export_service.py    # EXTEND
│   ├── test_catalog_import_service.py        # EXTEND
│   ├── test_denormalized_export_service.py   # EXTEND
│   ├── test_transaction_import_service.py    # NEW
│   └── test_enhanced_import_service.py       # EXTEND
└── integration/
    └── test_import_export_roundtrip.py       # NEW
```

**Structure Decision**: Extend existing services rather than creating parallel services. This maintains consistency with established patterns and reduces maintenance burden.

## Complexity Tracking

*No constitution violations - standard service extension pattern.*

## Parallel Work Analysis

### Dependency Graph

```
Foundation (WP1) ─────────────────────────────────────────────────────────┐
    │                                                                      │
    ├── Wave 1 (Parallel) ─────────────────────────────────────────┐      │
    │   ├── WP2: Materials Import (Gemini)                         │      │
    │   ├── WP3: Context-Rich Export (Gemini)                      │      │
    │   └── WP7: UI Redesign (Gemini)                              │      │
    │                                                               │      │
    ├── Wave 2 (Parallel, after Wave 1) ───────────────────────────┼──────┤
    │   ├── WP4: Purchase Import (Gemini)                          │      │
    │   ├── WP5: Adjustment Import (Gemini)                        │      │
    │   ├── WP9: Documentation (Gemini)                            │      │
    │   └── WP6: Context-Rich Import (Claude - depends on WP3)     │      │
    │                                                               │      │
    └── Integration (WP8) ─────────────────────────────────────────┘      │
        └── Final testing and validation ──────────────────────────────────┘
```

### Work Distribution

**Sequential work (Lead Agent - Claude)**:
- WP1: Complete System Backup - Foundation that others depend on
- WP6: Context-Rich Import - Complex auto-detection, depends on WP3
- WP8: Integration testing - Final validation across all WPs

**Parallel streams (Gemini delegation)**:
- WP2: Materials Import - Independent, follows existing ingredient pattern
- WP3: Context-Rich Export - Independent, extends existing views
- WP4: Purchase Import - Independent transaction handling
- WP5: Adjustment Import - Independent transaction handling
- WP7: UI Redesign - Independent UI layer work
- WP9: Documentation - Update spec_import_export.md with new schemas

### Agent Assignments

| Work Package | Agent | Files Modified |
|--------------|-------|----------------|
| WP1: Full Backup | Claude | `coordinated_export_service.py`, tests |
| WP2: Materials Import | Gemini | `catalog_import_service.py`, tests |
| WP3: Context-Rich Export | Gemini | `denormalized_export_service.py`, tests |
| WP4: Purchase Import | Gemini | `transaction_import_service.py` (NEW), tests |
| WP5: Adjustment Import | Gemini | `transaction_import_service.py` (NEW), tests |
| WP6: Context-Rich Import | Claude | `enhanced_import_service.py`, tests |
| WP7: UI Redesign | Gemini | `ui/dialogs/import_export_dialog.py` |
| WP8: Integration | Claude | Integration tests |
| WP9: Documentation | Gemini | `docs/design/spec_import_export.md` |

### Coordination Points

- **After Wave 1**: Merge all Gemini PRs, run full test suite
- **After Wave 2**: Merge remaining work, integration testing
- **File boundaries**: Strictly enforced - each WP owns specific files
- **Shared interfaces**: ImportResult, ExportResult classes unchanged

## Work Packages Summary

### WP1: Complete System Backup (16 Entities)
**Priority**: P1 | **Agent**: Claude | **Est**: 3-4 hours

Extend `coordinated_export_service.py` to export all 16 entity types:
- Currently exports: suppliers, ingredients, products, purchases, inventory_items, recipes, material_categories, material_subcategories, materials, material_products, material_units, material_purchases
- Add: finished_goods, events, production_runs, inventory_depletions

**Acceptance**: Full backup folder contains 16 entity files + manifest.json with accurate counts.

### WP2: Materials Catalog Import
**Priority**: P2 | **Agent**: Gemini | **Est**: 2-3 hours

Extend `catalog_import_service.py` to support materials and material_products:
- Match existing ingredient import pattern exactly
- Support ADD_ONLY and AUGMENT modes
- Resolve material_slug references

**Acceptance**: Materials JSON imports correctly, visible in Materials tab.

### WP3: Context-Rich Export
**Priority**: P3 | **Agent**: Gemini | **Est**: 3-4 hours

Extend `denormalized_export_service.py` with new view exports:
- `export_ingredients_view()` - hierarchy paths, related products, inventory totals
- `export_materials_view()` - hierarchy paths, related products
- `export_recipes_view()` - embedded ingredients, computed costs

**Acceptance**: Exports include full hierarchy paths and computed values.

### WP4: Purchase Transaction Import
**Priority**: P4 | **Agent**: Gemini | **Est**: 3-4 hours

Create `transaction_import_service.py` with purchase import:
- Validate positive quantities
- Create Purchase + InventoryItem records
- Recalculate weighted average costs
- Detect and skip duplicate purchases

**Acceptance**: Purchase import increases inventory correctly.

### WP5: Inventory Adjustment Import
**Priority**: P5 | **Agent**: Gemini | **Est**: 3-4 hours

Extend `transaction_import_service.py` with adjustment import:
- Validate negative quantities only
- Require reason codes (spoilage, waste, correction, other)
- Prevent negative inventory results
- Create adjustment records

**Acceptance**: Adjustment import decreases inventory correctly.

### WP6: Context-Rich Import with Auto-Detection
**Priority**: P6 | **Agent**: Claude | **Est**: 2-3 hours

Extend `enhanced_import_service.py`:
- Auto-detect format based on `_meta` field presence
- Extract only editable fields from context-rich imports
- Ignore computed fields (inventory, hierarchy paths)

**Acceptance**: Format auto-detected correctly; editable fields merged.

### WP7: Redesigned Import/Export UI
**Priority**: P7 | **Agent**: Gemini | **Est**: 3-4 hours

Redesign `ui/dialogs/import_export_dialog.py`:
- Export: 3 types (Full Backup, Catalog, Context-Rich) with purpose explanations
- Import: 4 purposes (Backup Restore, Catalog, Purchases, Adjustments)
- Display auto-detected format for confirmation

**Acceptance**: Clear UI distinguishing export types and import purposes.

### WP8: Integration Testing
**Priority**: P8 | **Agent**: Claude | **Est**: 2-3 hours

Create comprehensive integration tests:
- Round-trip: export → reset → import → verify counts
- Cross-entity validation
- Error handling and rollback verification

**Acceptance**: All integration tests pass; >70% service coverage.

### WP9: Documentation Update
**Priority**: P9 | **Agent**: Gemini | **Est**: 2-3 hours

Update `docs/design/spec_import_export.md` to document all new capabilities:
- Full backup with 14 entities and manifest format
- Materials and material_products import schemas
- Context-rich export schemas for ingredients, materials, recipes
- Purchase transaction import schema
- Inventory adjustment import schema
- Format auto-detection rules
- Updated Appendix sections as needed

**Acceptance**: spec_import_export.md accurately documents all new import/export formats for AI system reference.

## Implementation Order

1. **WP1** (Claude): Complete backup - enables testing of all other WPs
2. **Wave 1** (Gemini parallel): WP2, WP3, WP7 - independent work
3. **Wave 2** (Gemini parallel): WP4, WP5, WP9 - can start after WP1
4. **WP6** (Claude): Context-rich import - depends on WP3
5. **WP8** (Claude): Integration - final validation

## Success Criteria (from Spec)

- [ ] SC-001: Full backup includes all 16 entity types with accurate manifest
- [ ] SC-002: Complete system state restored from backup (round-trip)
- [ ] SC-003: Context-rich export for ingredients, materials, recipes with hierarchy
- [ ] SC-004: Materials import visible in Materials tab within 5 seconds
- [ ] SC-005: Material products slug resolution 100% accurate
- [ ] SC-006: Purchase import increases inventory correctly
- [ ] SC-007: Adjustment import decreases inventory correctly
- [ ] SC-008: Positive adjustment attempts rejected 100%
- [ ] SC-009: Format auto-detection 100% accurate
- [ ] SC-010: Export workflow completes in under 30 seconds
- [ ] SC-011: Import workflow completes in under 60 seconds
- [ ] SC-012: All exports use slug references (zero database IDs)
- [ ] SC-013: Materials import pattern matches ingredients import exactly
