# F051: Import/Export UI Rationalization

**Version**: 1.1
**Priority**: HIGH
**Type**: UI Enhancement + Service Integration

---

## Executive Summary

The import/export UI has accumulated redundancy and confusion after multiple feature iterations. Users face three different import entry points with unclear distinctions, suppliers cannot be imported through the UI despite F050 implementing backend support, and AI-assisted workflows will require robust validation and error logging.

Current gaps:
- ❌ File > Import Catalog redundant with Import Data dialog
- ❌ File > Import Context-Rich could be consolidated into Import Data
- ❌ Supplier import not accessible through UI (F050 backend complete)
- ❌ Export Catalog tab missing suppliers checkbox
- ❌ No pre-import schema validation (AI will generate malformed JSON)
- ❌ Import logs hardcoded location, insufficient detail for troubleshooting
- ❌ No configurable default directories (repetitive navigation)

This spec consolidates import/export UI into a single streamlined workflow, adds missing supplier UI integration, implements pre-import validation for AI-generated files, and adds comprehensive error logging for troubleshooting.

---

## Problem Statement

**Current State (CONFUSING):**
```
File Menu
├─ Import Data (ImportDialog)
│  ├─ ✅ 4 purpose types with auto-detection
│  └─ ❌ Missing supplier handling
├─ Import Catalog (CatalogImportDialog) ← REDUNDANT
│  └─ ❌ Duplicates Import Data functionality
├─ Import Context-Rich (ImportViewDialog) ← COULD CONSOLIDATE
│  └─ ✅ Context-rich imports (separate entry point)
└─ Export Data (ExportDialog)
   └─ ❌ Catalog tab missing suppliers checkbox

Supplier Support (F050 backend complete)
├─ ✅ coordinated_export exports suppliers with slugs
├─ ✅ Import resolves supplier slugs
└─ ❌ No UI to trigger supplier import/export

Validation & Logging
├─ ❌ No schema validation before import (AI will break this)
├─ ❌ Logs hardcoded to docs/user_testing
├─ ❌ Insufficient error detail for troubleshooting
└─ ❌ No configurable directories
```

**Target State (STREAMLINED):**
```
File Menu
├─ Import Data (Enhanced)
│  ├─ ✅ 5 purpose types (adds Context-Rich)
│  ├─ ✅ Supplier auto-detection and import
│  ├─ ✅ Schema validation before import
│  └─ ✅ Comprehensive error logging
├─ ❌ Import Catalog REMOVED (deprecated)
├─ ❌ Import Context-Rich REMOVED (consolidated)
├─ Export Data (Enhanced)
│  └─ ✅ Catalog tab includes suppliers checkbox
└─ Preferences (New)
   └─ ✅ Configure import/export/logs directories

Validation & Logging
├─ ✅ Pre-import schema validation (catch AI mistakes)
├─ ✅ Configurable logs directory
├─ ✅ Detailed error logs with context and resolution hints
└─ ✅ Structured logs for human and machine parsing
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Import Dialog Structure**
   - Find `src/ui/import_export_dialog.py` - study ImportDialog class
   - Note 4 purpose types with auto-detection workflow
   - Study `_detect_format()` method and mode-specific options panels
   - Understand how `_setup_catalog_options()` and similar methods work

2. **Catalog Import Dialog (to deprecate)**
   - Find `src/ui/catalog_import_dialog.py` - study CatalogImportDialog
   - Note entity checkboxes functionality (not needed - auto-detection replaces this)
   - Understand mode selection (Add/Augment)
   - This dialog will be deprecated, not deleted

3. **Import Context-Rich Dialog (to consolidate)**
   - Find ImportViewDialog class in `src/ui/import_export_dialog.py`
   - Understand context-rich import workflow
   - Note this becomes 5th purpose type in main Import dialog

4. **F050 Supplier Import/Export**
   - Find `src/services/coordinated_export_service.py` - study `_export_suppliers()`
   - Note suppliers export format with slug field
   - Study `_import_entity_records()` for supplier import pattern
   - Understand F050 implemented slug-based resolution

5. **Export Dialog Structure**
   - Study ExportDialog class in `src/ui/import_export_dialog.py`
   - Note Catalog tab entity checkbox list
   - Understand how `self.entity_vars` dictionary works
   - See how `export_all_to_json(entities=selected)` is called

6. **Auto-Detection Service**
   - Find `src/services/enhanced_import_service.py` - study `detect_format()` function
   - Understand format detection logic
   - Note how entity_count and format_type are determined

7. **Existing Logging**
   - Study `_write_import_log()` function in `src/ui/import_export_dialog.py`
   - Note current log format and hardcoded directory
   - Understand result.get_summary() pattern

---

## Requirements Reference

This specification implements:
- **REQ-SUP-025 through REQ-SUP-031**: Supplier import requirements
- **REQ-SUP-032 through REQ-SUP-035**: Supplier export requirements
- **UI consolidation**: Addresses user confusion from multiple import entry points
- **AI-assisted workflows**: Validation and logging for external data generation

From: `docs/requirements/req_suppliers.md` (v2.0)

---

## Functional Requirements

### FR-1: Add Suppliers to Export Catalog Tab

**What it must do:**
- Add "Suppliers" checkbox to Catalog tab entity selection list
- Include suppliers in export when checkbox selected
- Export uses F050 format (with slug field)

**Pattern reference:** Study how other entity checkboxes work in ExportDialog Catalog tab - add suppliers following same pattern

**Success criteria:**
- [ ] Catalog tab shows "Suppliers" checkbox
- [ ] Selecting "Suppliers" includes suppliers.json in export
- [ ] Exported suppliers include slug field (F050 format)
- [ ] Checkbox position alphabetical with other entities

---

### FR-2: Enhance Import Auto-Detection for Suppliers

**What it must do:**
- Recognize suppliers.json files during auto-detection
- Recognize multi-entity files containing suppliers array
- Display detected entities clearly (e.g., "Suppliers (6 records)" or "Multiple entities: Suppliers (6), Ingredients (45)")
- Auto-select "Catalog" purpose when supplier files detected

**Pattern reference:** Study `_detect_format()` in ImportDialog and `detect_format()` service - add supplier format recognition

**Detection logic:**
- Check for "suppliers" array at root level
- Check for "entity_type": "suppliers" metadata
- For multi-entity files, list all detected entities with counts

**Success criteria:**
- [ ] suppliers.json auto-detected correctly
- [ ] Multi-entity files show all entities detected
- [ ] Detection message clear (entity names + counts)
- [ ] Auto-selects "Catalog" purpose for supplier files

---

### FR-3: Consolidate Context-Rich Import into Import Data (5th Purpose)

**What it must do:**
- Add "Context-Rich" as 5th purpose type in Import Data dialog
- Purpose labeled: "Context-Rich" with description
- Mode options: "Update Existing" | "Add New Only"
- Auto-detection recognizes context-rich format (aug_*.json) and auto-selects "Context-Rich"
- Import uses existing enhanced_import_service with preprocessing

**Pattern reference:** Study existing purpose type structure (backup, catalog, purchases, adjustments) - add "context-rich" following same pattern

**Purpose description:**
```
"Context-Rich - Import AI-augmented data with full context (hierarchy paths, computed values)"
```

**File naming convention:**
- Context-rich files use `aug_*.json` pattern (e.g., `aug_ingredients.json`, `aug_products.json`)
- "aug" prefix signals "augmented by AI"

**Success criteria:**
- [ ] Import Data dialog shows 5th purpose: "Context-Rich"
- [ ] Context-Rich purpose has mode selection panel (merge/skip)
- [ ] Auto-detection recognizes aug_*.json files
- [ ] Import triggers preprocessing then standard import
- [ ] FK resolution works as before

---

### FR-4: Deprecate Import Catalog Menu Command

**What it must do:**
- Remove "Import Catalog" from File menu OR show deprecation message
- Direct users to File > Import Data for catalog imports
- Keep CatalogImportDialog code (don't delete)

**Deprecation message (if keeping menu item temporarily):**
```
"Import Catalog has been consolidated into Import Data.
Please use File > Import Data and select 'Catalog' purpose."
```

**Success criteria:**
- [ ] File > Import Catalog menu item removed or deprecated
- [ ] Users directed to Import Data dialog
- [ ] No broken references to CatalogImportDialog

---

### FR-5: Deprecate Import Context-Rich Menu Command

**What it must do:**
- Remove "Import Context-Rich" from File menu OR show deprecation message
- Direct users to File > Import Data with "Context-Rich" purpose
- Keep ImportViewDialog code as reference

**Deprecation message (if keeping menu item temporarily):**
```
"Import Context-Rich has been consolidated into Import Data.
Please use File > Import Data and select 'Context-Rich' purpose."
```

**Success criteria:**
- [ ] File > Import Context-Rich menu item removed or deprecated
- [ ] Users directed to Import Data > Context-Rich purpose
- [ ] No broken references to ImportViewDialog

---

### FR-6: Simplified Catalog Import (Auto-Detection, No Entity Filtering)

**What it must do:**
- Catalog purpose shows mode selection only (no entity checkboxes)
- Two modes: "Update Existing" (merge), "Add New Only" (skip_existing)
- Auto-detection determines entity types from file structure
- Support multi-entity files (e.g., sample_data_all.json)
- Import delegates to entity-specific services automatically

**Mode descriptions:**
- **"Update Existing"**: Updates existing records, adds new records
- **"Add New Only"**: Adds new records only, skips existing

**Multi-entity handling:**
- File contains `{"suppliers": [...], "ingredients": [...], "products": [...]}`
- Detection shows: "Multiple entities: Suppliers (6), Ingredients (45), Products (12)"
- Import processes each entity in dependency order

**Success criteria:**
- [ ] Catalog purpose shows mode selection (2 radio buttons)
- [ ] NO entity checkboxes shown
- [ ] Multi-entity files detected and listed clearly
- [ ] Import processes all detected entities automatically
- [ ] Entity import order respects dependencies

---

### FR-7: Context-Rich Import Preprocessing with Blocking Anomaly UX

**What it must do:**
- Context-Rich purpose preprocesses context-rich files to normalized format
- Preprocessing validates FK references before import
- Seamless flow if no errors (user doesn't see preprocessing)
- Blocking error dialog if FK references missing
- Error dialog shows missing entities and resolution suggestions

**Pattern reference:** Create preprocessing service following existing service patterns, study FK validation in enhanced_import_service

**Seamless flow (no errors):**
```
User selects aug_ingredients.json → Auto-detect → Select mode → Import
  ↓ (background)
Preprocessing: validate FKs → convert to normalized → import → success
```

**Blocking anomaly flow:**
```
User selects aug_products.json → Auto-detect → Select mode → Import
  ↓ (background)
Preprocessing: validate FKs → MISSING SUPPLIER REFERENCES → HALT
  ↓ (foreground)
Error Dialog: "Import Blocked: Missing References"
  - List missing entities (e.g., "whole_foods_bedford_ma")
  - Show which records reference missing entities
  - Suggest resolution actions
  - [Context-Rich Details] button for full context
```

**Error dialog content:**
- Clear title: "Import Blocked: Missing References"
- List missing entity slugs
- Show which records reference each missing entity
- Suggest actions: "Import suppliers first" or "Edit file to remove refs"
- [View Details] for expanded view
- [Copy to Clipboard] for easy sharing

**Success criteria:**
- [ ] Context-Rich import preprocesses aug_*.json files
- [ ] FK validation runs before import
- [ ] Missing FK errors block import with clear message
- [ ] Error dialog shows actionable information
- [ ] Valid files import seamlessly without preprocessing visibility
- [ ] Details view shows record-level FK references

---

### FR-8: Configurable Import/Export/Logs Directories

**What it must do:**
- Add Preferences dialog (File > Preferences or Edit > Preferences)
- Configure three directories: Import, Export, Logs
- Store settings in app_config table (survives DB reset)
- Import/Export dialogs use configured directories as initial location
- Default logs location outside repo (e.g., Documents/bake-tracker-logs)

**Pattern reference:** Study desktop app preferences patterns - keep dialog simple and clear

**Preferences dialog structure:**
```
File > Preferences
  Import/Export Settings section
    - Import Directory [path] [Browse...]
    - Export Directory [path] [Browse...]
    - Logs Directory [path] [Browse...]
  [Restore Defaults] [Cancel] [Save]
```

**Storage (app_config table):**
```sql
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);
```

**Default behavior:**
- Import/Export default: User's Documents folder or last used location
- Logs default: Documents/bake-tracker-logs (NOT in repo)
- NULL config = use system defaults

**Success criteria:**
- [ ] Preferences dialog accessible from File menu
- [ ] Three directory settings configurable
- [ ] Settings persist in app_config table
- [ ] Settings survive DB reset
- [ ] Import dialog starts in configured import directory
- [ ] Export dialog starts in configured export directory
- [ ] Logs written to configured logs directory
- [ ] [Restore Defaults] resets to sensible defaults

---

### FR-9: Pre-Import Schema Validation

**What it must do:**
- Validate JSON structure before attempting import
- Check required fields present for detected entity types
- Check field types match expected (string, bool, array, number)
- Show clear validation errors if structure invalid
- Allow import if structure valid (silent validation)

**Pattern reference:** Simple validation service, not full JSON Schema library - just check structure basics

**Validation checks:**
- Entity data is array (not object or primitive)
- Required fields present in sample records (first 5)
- Field types correct for known fields
- Detect common AI mistakes (nested structures, wrong types, missing required fields)

**Validation error dialog:**
```
"Invalid File Format"
  - List structural problems by entity and record
  - Show what was expected vs what was found
  - Note: "This file was likely generated incorrectly"
  - [Copy Errors] [Cancel]
```

**Success criteria:**
- [ ] Validation runs after detection, before import
- [ ] Missing required fields detected
- [ ] Wrong field types detected
- [ ] Nested structures detected (should be flat)
- [ ] Clear error messages with record numbers
- [ ] Valid files pass through silently
- [ ] Validation covers all entity types
- [ ] Unexpected fields generate warnings (not errors)

---

### FR-10: Comprehensive Import Error Logging

**What it must do:**
- Log all import operations to timestamped files in configured logs directory
- Include structured sections: SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY
- Log errors with context: timestamp, error type, affected record, resolution suggestion
- Log warnings: unexpected fields, optional FK not found, skipped records
- Format for human readability AND machine parsing

**Pattern reference:** Enhance existing `_write_import_log()` with structured sections and detailed error context

**Log file naming:**
```
import_{timestamp}.log
Example: import_2026-01-13_142345.log
```

**Log structure (required sections):**
1. **SOURCE**: File path, size, detected format, entity counts
2. **OPERATION**: Purpose type, mode, timestamps, duration
3. **PREPROCESSING**: (if applicable) Denormalization results, FK validation status
4. **SCHEMA VALIDATION**: Structural validation results, warnings count
5. **IMPORT RESULTS**: Total/successful/skipped/failed counts, per-entity breakdown
6. **ERRORS**: Detailed error entries with record context and resolution suggestions
7. **WARNINGS**: Non-blocking issues with actions taken
8. **SUMMARY**: Overall status, success rate, next steps
9. **METADATA**: Log file path

**Error entry format:**
```
[HH:MM:SS.mmm] ERROR_TYPE: Brief description
  Entity: entity_name
  Record: {json snippet or identifier}
  Expected: what was expected
  Actual: what was found
  Resolution: suggested fix
```

**Error types:**
- VALIDATION_ERROR (missing field, wrong type)
- FK_RESOLUTION_ERROR (referenced entity missing)
- BUSINESS_RULE_ERROR (duplicate slug, constraint violation)
- DATABASE_ERROR (DB constraint failure)
- PARSE_ERROR (malformed JSON)
- SCHEMA_ERROR (structure mismatch)

**Warning types:**
- UNEXPECTED_FIELD (will be ignored)
- FK_NOT_FOUND (optional FK missing)
- DUPLICATE_SKIPPED (existing record, skip mode)

**Success criteria:**
- [ ] Every import creates timestamped log file
- [ ] Log includes all required sections
- [ ] Errors include record context (JSON snippet)
- [ ] Errors include resolution suggestions
- [ ] Warnings include actions taken
- [ ] Log format human-readable
- [ ] Log structure allows programmatic parsing (sections clearly delimited)
- [ ] Failed imports log full error details
- [ ] Successful imports log summary stats
- [ ] Partial success logs both successes and failures

---

### FR-11: Preserve Existing Import/Export Behavior

**What it must do:**
- All existing workflows continue functioning identically
- No breaking changes to file formats
- No regressions in backup/restore, purchases, adjustments, exports

**Success criteria:**
- [ ] Backup restore workflow unchanged
- [ ] Purchase import workflow unchanged
- [ ] Adjustment import workflow unchanged (decrements only)
- [ ] Full Backup export unchanged
- [ ] Context-Rich export unchanged
- [ ] Existing export files still import correctly
- [ ] All file format versions supported

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Changes to import/export file formats (F050 already handled)
- ❌ New import/export services (use existing)
- ❌ Supplier CRUD UI changes (separate concern)
- ❌ Batch operations beyond import
- ❌ Supplier merge/deduplication tools
- ❌ Dry-run mode UI enhancements
- ❌ Log viewer UI (external text editor fine)
- ❌ Log rotation/cleanup automation
- ❌ Real-time log streaming during import
- ❌ Advanced preferences (timeout settings, etc.)
- ❌ Import history / recent files list

---

## Success Criteria

**Complete when:**

### UI Consolidation
- [ ] Import Data is single entry point (5 purpose types)
- [ ] Import Catalog deprecated or removed
- [ ] Import Context-Rich deprecated or removed
- [ ] User confusion eliminated (one clear workflow)

### Supplier Integration
- [ ] Export Catalog tab includes Suppliers checkbox
- [ ] Import auto-detects supplier files
- [ ] Supplier import works via Import Data > Catalog
- [ ] Round-trip test passes (export → import → verify)

### Validation & Logging
- [ ] Schema validation catches malformed files
- [ ] Error messages actionable and clear
- [ ] Comprehensive logs written for all imports
- [ ] Logs include full context for troubleshooting
- [ ] Claude can read logs and provide specific fixes

### Configuration
- [ ] Preferences dialog accessible
- [ ] Directory settings persist across restarts
- [ ] Settings survive DB reset
- [ ] Logs written to configured location (not repo)

### Preprocessing
- [ ] Context-Rich imports preprocess aug_*.json files
- [ ] FK validation runs before import
- [ ] Missing FK errors block with helpful message
- [ ] Valid files import seamlessly

### Multi-Entity Support
- [ ] sample_data_all.json pattern works (multiple entities in one file)
- [ ] Detection lists all entities clearly
- [ ] Import processes entities in dependency order

### Backward Compatibility
- [ ] All existing workflows unchanged
- [ ] No functional regressions
- [ ] Old export files still import correctly

### Testing
- [ ] Manual test all 5 import purpose types
- [ ] Test supplier export/import round-trip
- [ ] Test multi-entity catalog import
- [ ] Test context-rich import with FK errors (aug_*.json files)
- [ ] Test schema validation with AI-generated malformed JSON
- [ ] Test configurable directories
- [ ] Verify comprehensive logs written
- [ ] Test deprecation messages clear

### Quality
- [ ] Code follows existing dialog patterns
- [ ] Error handling consistent
- [ ] UI help text clear
- [ ] Deprecation messages helpful
- [ ] No code duplication

---

## Architecture Principles

### Single Entry Point Principle

**One Dialog to Rule Them All:**
- Import Data dialog handles all import workflows
- Purpose selection makes intent explicit
- Auto-detection helps but doesn't dictate
- Reduces cognitive load on users

**Rationale:** Multiple entry points create confusion. Purpose-based selection makes workflow intent clear upfront.

### Fail Fast, Fail Friendly

**Validation Layers:**
1. Schema validation (structural problems) - before import
2. FK validation (missing references) - during preprocessing
3. Entity validation (business rules) - during import

**Error Philosophy:**
- Catch problems early with actionable messages
- Don't touch database until file is valid
- Provide resolution suggestions, not just errors
- Log everything for post-mortem analysis

**Rationale:** AI will generate creative mistakes. Fast failure with helpful messages beats cryptic database errors.

### Pattern Consistency

**Import Purpose Structure:**
All 5 purpose types follow identical pattern:
- Radio button with label and description
- Purpose-specific options panel
- Consistent import workflow
- Same result dialog

**Export Tab Structure:**
All 3 tabs follow identical pattern:
- Entity/view selection
- Export button
- Progress indication
- Success message with path

**Rationale:** Consistency makes UI predictable and maintainable.

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Pre-import validation catches structural problems
- FK validation prevents orphaned references
- Comprehensive logging enables troubleshooting
- No changes to validated import services

✅ **Principle II: Layered Architecture**
- UI delegates to existing services
- No business logic in dialogs
- Clear separation: UI ↔ Service ↔ Data
- Preprocessing is service layer concern

✅ **Principle III: User Experience**
- Consolidation reduces confusion (one entry point)
- Auto-detection reduces cognitive load
- Clear error messages with resolution suggestions
- Configurable directories reduce repetitive navigation

✅ **Principle VII: Pragmatic Aspiration**
- Builds for today (desktop) while enabling tomorrow (AI workflows)
- Schema validation supports AI-assisted data generation
- Comprehensive logging enables external troubleshooting
- Preprocessing architecture reusable for future data sources

✅ **Principle VIII: Pattern Consistency**
- Import purposes follow established pattern
- Export entity checkboxes follow established pattern
- Validation and logging follow service patterns
- No new UI paradigms introduced

---

## Risk Considerations

**Risk: Users accustomed to old menu structure**
- Context: Import Catalog and Import Context-Rich have been available
- Mitigation: Show deprecation messages, preserve menu items temporarily with clear redirection

**Risk: Schema validation false positives**
- Context: Validation might reject valid files if schemas incomplete
- Mitigation: Focus on egregious errors only (missing required fields, wrong types), unexpected fields = warnings not errors

**Risk: Preprocessing adds complexity**
- Context: Context-rich import now has extra step
- Mitigation: Seamless if no errors (user doesn't see it), only surfaces when FK problems detected

**Risk: Log files accumulate**
- Context: No automatic cleanup
- Mitigation: Acceptable for now, logs in configurable directory (user can manage), defer rotation to future feature

**Risk: Breaking change to workflows**
- Context: Consolidating multiple dialogs
- Mitigation: Preserve all existing functionality, just different UI path, keep old dialogs for rollback

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study ImportDialog purpose type pattern → add "context-rich" as 5th type
- Study ExportDialog Catalog tab checkboxes → add "Suppliers"
- Study auto-detection logic → add supplier format recognition and aug_*.json pattern
- Study existing validation patterns → create schema validation service
- Study _write_import_log → enhance with structured sections

**Key Patterns to Copy:**
- Purpose type structure (ImportDialog) → "Context-Rich" purpose
- Entity checkbox pattern (ExportDialog) → "Suppliers" checkbox
- Mode selection panels → Catalog and Context-Rich purposes
- Error dialog patterns → Validation and FK resolution errors
- Service delegation → Preprocessing service

**Focus Areas:**
- Import Data dialog already structured for adding 5th purpose (follow existing pattern exactly)
- Catalog purpose simplified (remove entity checkboxes, rely on auto-detection)
- Preprocessing service is new component (follow existing service patterns)
- Schema validation is new component (keep lightweight, don't use JSON Schema library)
- Logging enhancement (structured sections, detailed context)
- Preferences dialog is new component (follow desktop app patterns)

**File Naming Convention:**
- Context-rich files use `aug_*.json` pattern
- Examples: `aug_ingredients.json`, `aug_products.json`, `aug_materials.json`
- Detection recognizes aug_ prefix OR context_rich metadata

**Multi-Entity File Handling:**
- Detection scans for all known entity keys ("suppliers", "ingredients", "products", etc.)
- Lists all detected with counts: "Multiple entities: Suppliers (6), Ingredients (45), Products (12)"
- Import loops through entities in dependency order (DEPENDENCY_ORDER in coordinated_export_service)
- Each entity imported by its specific service

**Testing Strategy:**
- Test each purpose type independently
- Test supplier round-trip (export → import → verify)
- Test multi-entity catalog import (sample_data_all.json)
- Test context-rich import with FK errors (aug_*.json with missing supplier references)
- Test schema validation with AI-generated malformed JSON
- Test configurable directories (set, restart, verify)
- Test comprehensive logging (read logs, verify all sections present)
- Regression test all existing workflows

**Deprecation Approach:**
- Option A: Remove menu items entirely (clean but abrupt)
- Option B: Keep menu items, show message boxes redirecting (gentle transition)
- Recommend: Option B initially, Option A in future release

---

**END OF SPECIFICATION**
