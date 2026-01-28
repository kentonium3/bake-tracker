# F081: Snapshot Export Coverage

**Version**: 1.0
**Date**: 2026-01-28
**Priority**: CRITICAL
**Type**: Export/Import Enhancement

---

## Executive Summary

Cost snapshot entities (RecipeSnapshot, FinishedGoodSnapshot, MaterialUnitSnapshot, FinishedUnitSnapshot) are not currently exported, causing loss of cost history audit trail during data migrations.

Current gaps:
- ❌ RecipeSnapshot not exported (production cost history lost)
- ❌ FinishedGoodSnapshot not exported (assembly cost history lost)
- ❌ MaterialUnitSnapshot not exported (material pricing history lost)
- ❌ FinishedUnitSnapshot not exported (unit cost history lost)
- ❌ No way to preserve cost calculations across export/import cycles

This spec adds comprehensive export/import support for all snapshot entities, preserving cost audit trails and ensuring data portability for future web migration.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Snapshot Entities
├─ RecipeSnapshot (F065) - captures production costs
│  └─ ❌ NOT exported
├─ FinishedGoodSnapshot (F064) - captures assembly costs  
│  └─ ❌ NOT exported
├─ MaterialUnitSnapshot (F064) - captures material unit pricing
│  └─ ❌ NOT exported
└─ FinishedUnitSnapshot (F064) - captures finished unit costs
   └─ ❌ NOT exported

coordinated_export_service.py
├─ ✅ Exports recipes
├─ ✅ Exports finished_goods
├─ ✅ Exports material_units
├─ ✅ Exports finished_units
└─ ❌ Does NOT export any snapshots

Impact:
├─ Export → Reset → Import cycle loses all cost history
├─ Cannot recreate historical cost calculations
└─ Violates Constitution Principle II (Data Integrity)
```

**Target State (COMPLETE):**
```
Snapshot Entities
├─ RecipeSnapshot
│  └─ ✅ Exported with full cost data
├─ FinishedGoodSnapshot
│  └─ ✅ Exported with full cost data
├─ MaterialUnitSnapshot
│  └─ ✅ Exported with unit pricing data
└─ FinishedUnitSnapshot
   └─ ✅ Exported with unit cost data

coordinated_export_service.py
├─ ✅ _export_recipe_snapshots()
├─ ✅ _export_finished_good_snapshots()
├─ ✅ _export_material_unit_snapshots()
└─ ✅ _export_finished_unit_snapshots()

enhanced_import_service.py
├─ ✅ _import_recipe_snapshots()
├─ ✅ _import_finished_good_snapshots()
├─ ✅ _import_material_unit_snapshots()
└─ ✅ _import_finished_unit_snapshots()

Benefit:
├─ Full export/import of cost audit trail
├─ Historical cost accuracy preserved
└─ Constitution Principle II compliance restored
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Snapshot Model Definitions**
   - Find: `src/models/recipe_snapshot.py` - Study RecipeSnapshot structure
   - Find: `src/models/finished_good_snapshot.py` - Study FinishedGoodSnapshot structure
   - Find: `src/models/material_unit_snapshot.py` - Study MaterialUnitSnapshot structure
   - Find: `src/models/finished_unit_snapshot.py` - Study FinishedUnitSnapshot structure
   - Note: All snapshots have UUID, timestamps, parent FK, and cost/data JSON blob

2. **Existing Snapshot Export Pattern** (if any)
   - Search: coordinated_export_service.py for any snapshot export methods
   - Note: Currently NO snapshot export exists - we're creating new pattern

3. **Parent Entity Export Patterns**
   - Find: `_export_recipes()` method - Study how recipes are exported
   - Find: `_export_finished_goods()` method - Study how finished goods are exported
   - Note: Pattern of UUID, FK references, timestamps, data fields

4. **Parent Entity Import Patterns**
   - Find: `_import_recipes()` method - Study how recipes are imported
   - Find: `_import_finished_goods()` method - Study how finished goods are imported
   - Note: Pattern of FK resolution, UUID handling, data preservation

5. **Export/Import Service Architecture**
   - Find: `src/services/coordinated_export_service.py` - Study export_all() orchestration
   - Find: `src/services/enhanced_import_service.py` - Study import_all() orchestration
   - Note: Order dependencies (parents before children)

---

## Requirements Reference

This specification addresses critical gaps identified in:
- Data Portability Review (2026-01-28) Section 2: "Missing Export Coverage (CRITICAL GAPS)"
  - F064: FinishedGoodSnapshot, MaterialUnitSnapshot, FinishedUnitSnapshot
  - F065: RecipeSnapshot

Implements recommendations for:
- Export/import support for all snapshot entities
- Preserving cost history audit trail
- Enabling full data portability for web migration

---

## Functional Requirements

### FR-1: Export RecipeSnapshot Entities

**What it must do:**
- Add `_export_recipe_snapshots()` method to coordinated_export_service.py
- Export all RecipeSnapshot records to recipe_snapshots.json
- Include: snapshot_uuid, recipe_id (resolved to recipe_slug), snapshot_at timestamp, cost_data JSON
- Export snapshots in chronological order (oldest first)
- Include snapshot count in manifest.json

**Pattern reference:** Study _export_recipes() - copy structure for snapshot export

**Export JSON Structure:**
```json
{
  "snapshot_uuid": "uuid-string",
  "recipe_slug": "chocolate-chip-cookies",
  "snapshot_at": "2025-12-01T10:30:00Z",
  "cost_data": {
    "total_ingredient_cost": 12.50,
    "ingredient_costs": [...],
    "component_costs": [...]
  }
}
```

**Success criteria:**
- [ ] _export_recipe_snapshots() method exists
- [ ] recipe_snapshots.json created with all snapshots
- [ ] recipe_id resolved to recipe_slug in export
- [ ] Snapshots ordered chronologically
- [ ] Manifest includes snapshot count
- [ ] Export tests verify snapshot data completeness

---

### FR-2: Import RecipeSnapshot Entities

**What it must do:**
- Add `_import_recipe_snapshots()` method to enhanced_import_service.py
- Import recipe_snapshots.json
- Resolve recipe_slug back to recipe_id
- Preserve snapshot_uuid, snapshot_at, cost_data
- Import after recipes are imported (FK dependency)
- Handle missing parent recipe gracefully (log warning, skip snapshot)

**Pattern reference:** Study _import_recipes() - copy structure for snapshot import

**Business rules:**
- Import snapshots AFTER parent recipes imported
- Skip snapshots with unresolvable recipe_slug (log warning)
- Preserve original snapshot UUIDs
- Preserve original snapshot timestamps
- Preserve cost_data JSON exactly as exported

**Success criteria:**
- [ ] _import_recipe_snapshots() method exists
- [ ] Snapshots imported after recipes
- [ ] recipe_slug resolved to recipe_id correctly
- [ ] Snapshot UUIDs, timestamps, cost_data preserved
- [ ] Missing parent recipes logged but don't fail import
- [ ] Import tests verify snapshot restoration

---

### FR-3: Export FinishedGoodSnapshot Entities

**What it must do:**
- Add `_export_finished_good_snapshots()` method to coordinated_export_service.py
- Export all FinishedGoodSnapshot records to finished_good_snapshots.json
- Include: snapshot_uuid, finished_good_id (resolved to slug), snapshot_at, cost_data JSON
- Export in chronological order
- Include snapshot count in manifest

**Pattern reference:** Copy _export_recipe_snapshots() structure exactly

**Success criteria:**
- [ ] _export_finished_good_snapshots() method exists
- [ ] finished_good_snapshots.json created
- [ ] finished_good_id resolved to slug
- [ ] Snapshots ordered chronologically
- [ ] Manifest includes count
- [ ] Export tests pass

---

### FR-4: Import FinishedGoodSnapshot Entities

**What it must do:**
- Add `_import_finished_good_snapshots()` method to enhanced_import_service.py
- Import finished_good_snapshots.json
- Resolve finished_good_slug back to finished_good_id
- Preserve snapshot_uuid, snapshot_at, cost_data
- Import after finished_goods imported (FK dependency)

**Pattern reference:** Copy _import_recipe_snapshots() structure exactly

**Success criteria:**
- [ ] _import_finished_good_snapshots() method exists
- [ ] Snapshots imported after finished_goods
- [ ] Slug resolution works correctly
- [ ] Data preserved exactly
- [ ] Import tests pass

---

### FR-5: Export MaterialUnitSnapshot Entities

**What it must do:**
- Add `_export_material_unit_snapshots()` method to coordinated_export_service.py
- Export all MaterialUnitSnapshot records to material_unit_snapshots.json
- Include: snapshot_uuid, material_unit_id (resolved to slug), snapshot_at, pricing_data JSON
- Export in chronological order
- Include snapshot count in manifest

**Pattern reference:** Copy _export_recipe_snapshots() structure, adapt for MaterialUnit

**Success criteria:**
- [ ] _export_material_unit_snapshots() method exists
- [ ] material_unit_snapshots.json created
- [ ] material_unit_id resolved to slug
- [ ] Snapshots ordered chronologically
- [ ] Manifest includes count
- [ ] Export tests pass

---

### FR-6: Import MaterialUnitSnapshot Entities

**What it must do:**
- Add `_import_material_unit_snapshots()` method to enhanced_import_service.py
- Import material_unit_snapshots.json
- Resolve material_unit_slug back to material_unit_id
- Preserve snapshot_uuid, snapshot_at, pricing_data
- Import after material_units imported (FK dependency)

**Pattern reference:** Copy _import_recipe_snapshots() structure, adapt for MaterialUnit

**Success criteria:**
- [ ] _import_material_unit_snapshots() method exists
- [ ] Snapshots imported after material_units
- [ ] Slug resolution works correctly
- [ ] Data preserved exactly
- [ ] Import tests pass

---

### FR-7: Export FinishedUnitSnapshot Entities

**What it must do:**
- Add `_export_finished_unit_snapshots()` method to coordinated_export_service.py
- Export all FinishedUnitSnapshot records to finished_unit_snapshots.json
- Include: snapshot_uuid, finished_unit_id (resolved to slug), snapshot_at, cost_data JSON
- Export in chronological order
- Include snapshot count in manifest

**Pattern reference:** Copy _export_recipe_snapshots() structure, adapt for FinishedUnit

**Success criteria:**
- [ ] _export_finished_unit_snapshots() method exists
- [ ] finished_unit_snapshots.json created
- [ ] finished_unit_id resolved to slug
- [ ] Snapshots ordered chronologically
- [ ] Manifest includes count
- [ ] Export tests pass

---

### FR-8: Import FinishedUnitSnapshot Entities

**What it must do:**
- Add `_import_finished_unit_snapshots()` method to enhanced_import_service.py
- Import finished_unit_snapshots.json
- Resolve finished_unit_slug back to finished_unit_id
- Preserve snapshot_uuid, snapshot_at, cost_data
- Import after finished_units imported (FK dependency)

**Pattern reference:** Copy _import_recipe_snapshots() structure, adapt for FinishedUnit

**Success criteria:**
- [ ] _import_finished_unit_snapshots() method exists
- [ ] Snapshots imported after finished_units
- [ ] Slug resolution works correctly
- [ ] Data preserved exactly
- [ ] Import tests pass

---

### FR-9: Update Export Orchestration

**What it must do:**
- Update `export_all()` method in coordinated_export_service.py
- Add snapshot exports AFTER parent entity exports:
  - Export recipes → Export recipe_snapshots
  - Export finished_goods → Export finished_good_snapshots
  - Export material_units → Export material_unit_snapshots
  - Export finished_units → Export finished_unit_snapshots
- Update manifest.json with snapshot file paths and counts
- Update export progress indicators

**Pattern reference:** Study existing export_all() orchestration

**Success criteria:**
- [ ] export_all() includes all snapshot exports
- [ ] Snapshots exported after parent entities
- [ ] Manifest includes all snapshot files
- [ ] Progress indicators work correctly
- [ ] Full export completes without errors

---

### FR-10: Update Import Orchestration

**What it must do:**
- Update `import_all()` method in enhanced_import_service.py
- Add snapshot imports AFTER parent entity imports:
  - Import recipes → Import recipe_snapshots
  - Import finished_goods → Import finished_good_snapshots
  - Import material_units → Import material_unit_snapshots
  - Import finished_units → Import finished_unit_snapshots
- Update import validation
- Update import progress indicators

**Pattern reference:** Study existing import_all() orchestration

**Success criteria:**
- [ ] import_all() includes all snapshot imports
- [ ] Snapshots imported after parent entities
- [ ] Import validation checks snapshot files
- [ ] Progress indicators work correctly
- [ ] Full import completes without errors

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ PlanSnapshot export/import (separate feature, lower priority)
- ❌ ProductionPlanSnapshot export/import (separate feature, lower priority)
- ❌ PlanAmendment export/import (separate feature, lower priority)
- ❌ PlanningSnapshot export/import (separate feature, lower priority)
- ❌ Snapshot data transformation or migration (preserve exactly as-is)
- ❌ Snapshot cleanup or archival (out of scope)
- ❌ Snapshot compression (preserve full data)

---

## Success Criteria

**Complete when:**

### Export Functionality
- [ ] All 4 snapshot types exported to separate JSON files
- [ ] recipe_snapshots.json, finished_good_snapshots.json, material_unit_snapshots.json, finished_unit_snapshots.json created
- [ ] Parent entity slugs resolved in all snapshot exports
- [ ] Snapshots ordered chronologically
- [ ] Manifest includes all snapshot files and counts
- [ ] Export completes without errors

### Import Functionality
- [ ] All 4 snapshot types imported from JSON files
- [ ] Slugs resolved back to parent entity IDs correctly
- [ ] Snapshot UUIDs, timestamps, data preserved exactly
- [ ] Snapshots imported after parent entities (dependency order)
- [ ] Missing parent entities logged but don't fail import
- [ ] Import completes without errors

### Round-Trip Testing
- [ ] Export → Import → Export produces identical snapshot data
- [ ] Snapshot UUIDs preserved across round-trip
- [ ] Snapshot timestamps preserved across round-trip
- [ ] cost_data/pricing_data JSON preserved exactly
- [ ] Parent entity FK references restored correctly

### Quality
- [ ] Zero failing tests
- [ ] Export performance acceptable (<5 seconds for 1000 snapshots)
- [ ] Import performance acceptable (<10 seconds for 1000 snapshots)
- [ ] Error messages clear and actionable
- [ ] Progress indicators accurate

---

## Architecture Principles

### Snapshot Export Pattern

**Consistent Structure Across All Snapshots:**
- UUID field (preserve original)
- Parent entity FK → slug resolution
- timestamp field (preserve original)
- data JSON blob (preserve exactly)
- Chronological ordering

### Import Dependency Ordering

**Parents Before Snapshots:**
- Recipes imported → Then recipe_snapshots
- FinishedGoods imported → Then finished_good_snapshots
- MaterialUnits imported → Then material_unit_snapshots
- FinishedUnits imported → Then finished_unit_snapshots

### Data Preservation

**Zero Data Loss:**
- Preserve original UUIDs (don't regenerate)
- Preserve original timestamps (don't modify)
- Preserve cost_data/pricing_data JSON exactly (no transformation)
- Skip snapshots with missing parents (log, don't fail)

---

## Constitutional Compliance

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Preserves complete cost history audit trail
- Enables accurate cost calculations across migrations
- Protects historical financial data

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Snapshot export structure supports future enhancements
- JSON format allows schema evolution
- Slug-based FK resolution ready for multi-tenant

✅ **Principle VII: Pragmatic Aspiration**
- Desktop phase: Complete snapshot export/import
- Web phase: Same export format, add tenant filtering
- Migration cost: Medium effort now, prevents data loss

---

## Risk Considerations

**Risk: Large snapshot datasets slow export/import**
- Context: Production systems may have thousands of snapshots
- Mitigation: Profile performance with 1000+ snapshot test dataset

**Risk: Missing parent entities break snapshot import**
- Context: Snapshots reference recipes, finished_goods, etc.
- Mitigation: Skip snapshots with unresolved parents, log warnings, don't fail import

**Risk: cost_data JSON schema changes break import**
- Context: cost_data structure evolved in F064/F065
- Mitigation: Import cost_data as-is, no validation or transformation

**Risk: Snapshot timestamps timezone issues**
- Context: Timestamps must preserve timezone information
- Mitigation: Use ISO 8601 format with timezone (existing pattern)

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study _export_recipes() → create _export_recipe_snapshots()
- Study _import_recipes() → create _import_recipe_snapshots()
- Copy pattern 3 more times for other snapshot types

**Key Patterns to Copy:**
- Parent entity export structure → Snapshot export structure
- Parent entity slug resolution → Snapshot slug resolution
- Parent entity import FK resolution → Snapshot FK resolution

**Focus Areas:**
- Snapshot import MUST happen after parent entity import
- FK resolution MUST use slug-based lookup (not name fallback)
- UUID preservation critical (don't regenerate)
- Timestamp preservation critical (don't modify)
- cost_data/pricing_data JSON must be preserved exactly

**Critical Files to Modify:**
- `src/services/coordinated_export_service.py` - Add 4 snapshot export methods
- `src/services/enhanced_import_service.py` - Add 4 snapshot import methods
- Update export_all() and import_all() orchestration
- Add comprehensive tests for all 4 snapshot types

---

**END OF SPECIFICATION**
