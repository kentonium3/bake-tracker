# F055: CLI Import/Export Parity

**Version**: 1.0
**Priority**: HIGH
**Type**: CLI Enhancement + Service Integration

---

## Executive Summary

The CLI import/export functionality (`import_export_cli.py`) has fallen behind UI capabilities after F047-F051 refactoring. Materials entities, supplier support, catalog imports, and context-rich exports (now "aug" files) are all missing or incomplete in CLI. This creates a critical gap for AI-assisted workflows and mobile JSON ingestion that depend on CLI as a first-class interface.

Current gaps:
- ❌ Materials entities (Material, MaterialProduct, MaterialCategory, MaterialSubcategory) not exposed in CLI
- ❌ Suppliers not accessible despite F050/F051 backend support
- ❌ Catalog import functionality incomplete (only legacy entity-specific exports exist)
- ❌ Context-rich "aug" exports not exposed (F053 renamed view→aug)
- ❌ Context-rich imports not exposed (Products, Material Products now supported per F053)
- ❌ No backup/restore commands (16-entity coordinated export from F049)
- ❌ Purchase tracking exports missing (F043)
- ❌ CLI documentation outdated with incorrect examples

This spec brings CLI to full parity with UI import/export capabilities, ensuring AI-assisted workflows and mobile JSON ingestion work seamlessly through command-line interface.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
CLI Commands (import_export_cli.py)
├─ Legacy Commands (v3.2 format - OUTDATED)
│  ├─ export - all data (old format)
│  ├─ export-ingredients
│  ├─ export-recipes
│  ├─ export-finished-goods
│  ├─ export-bundles
│  ├─ export-packages
│  ├─ export-recipients
│  ├─ export-events
│  ├─ ❌ Missing: products, suppliers, materials, purchases
│  └─ import - v3.2 format only
│
├─ F030 Commands (partial)
│  ├─ export-complete (16 entities - MISSING materials)
│  ├─ export-view (products, inventory, purchases)
│  ├─ ❌ Missing: materials, suppliers view exports
│  ├─ ❌ Missing: context-rich "aug" exports (F053)
│  ├─ validate-export
│  └─ import-view (generic, MISSING entity-specific support)
│
└─ ❌ No backup/restore commands
   ❌ No catalog import commands
   ❌ No materials CLI support
   ❌ No supplier CLI support

UI Capabilities (F047-F053)
├─ ✅ 16-entity coordinated export (backup)
├─ ✅ Catalog import (ingredients, products, recipes, materials, suppliers)
├─ ✅ Context-rich "aug" exports (7 entity types)
├─ ✅ Context-rich imports with FK resolution
├─ ✅ Materials full CRUD
├─ ✅ Suppliers full CRUD
└─ ✅ Purchase tracking

Gap: CLI cannot perform operations that UI can perform
```

**Target State (PARITY ACHIEVED):**
```
CLI Commands (import_export_cli.py)
├─ Backup/Restore (F049 coordinated export)
│  ├─ backup - create timestamped 16-entity backup
│  ├─ restore - restore from backup directory
│  ├─ backup-list - show available backups
│  └─ backup-validate - verify backup integrity
│
├─ Catalog Operations
│  ├─ catalog-export - export catalog (7 entity types)
│  ├─ catalog-import - import catalog with mode selection
│  └─ catalog-validate - pre-import validation
│
├─ Context-Rich Operations (F053 "aug" files)
│  ├─ aug-export - export aug files (7 entity types + "all")
│  ├─ aug-import - import aug files with FK resolution
│  └─ aug-validate - validate aug file format
│
├─ Entity-Specific Exports (comprehensive)
│  ├─ All 16 entities exposed:
│  │  ├─ ingredients, products, recipes
│  │  ├─ finished-units, finished-goods, packages
│  │  ├─ materials, material-products
│  │  ├─ suppliers, purchases
│  │  ├─ inventory, events, recipients
│  │  └─ production-runs, assembly-runs, consumption-records
│  │
│  └─ Materials entities:
│     ├─ export-materials
│     ├─ export-material-products
│     ├─ export-material-categories
│     └─ export-material-subcategories
│
└─ Legacy Commands (deprecated but functional)
   ├─ export (old v3.2 format)
   ├─ import (v3.2 format compatibility)
   └─ export-view (F030 view format)

Full UI Parity Achieved:
✅ All UI import/export operations available via CLI
✅ AI-assisted workflows fully supported
✅ Mobile JSON ingestion enabled
✅ Comprehensive entity coverage (16 types)
✅ Materials management complete
✅ Supplier management complete
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current CLI Implementation**
   - File: `src/utils/import_export_cli.py`
   - Study existing command structure (subparsers pattern)
   - Note F030 commands (export-complete, export-view, import-view)
   - Understand CLIFKResolver for interactive FK resolution
   - Note legacy commands (export, export-ingredients, etc.)

2. **Coordinated Export Service (F049)**
   - File: `src/services/coordinated_export_service.py`
   - Study `export_complete()` function (16-entity backup)
   - Note `validate_export()` for backup verification
   - Understand manifest.json structure with checksums
   - Study how materials/suppliers are exported

3. **Import Service (F051)**
   - File: `src/services/import_service.py` or `enhanced_import_service.py`
   - Study catalog import functions
   - Note mode handling (ADD_ONLY, AUGMENT, REPLACE)
   - Understand entity type detection
   - Study FK resolution patterns

4. **Context-Rich Export Service**
   - Find context-rich export functions (likely in coordinated_export_service.py or separate)
   - Study "aug_" prefix exports (F053 renamed from "view_")
   - Note 7 entity types: ingredients, products, recipes, finished-units, finished-goods, materials, material-products
   - Understand context field enrichment

5. **UI Export Dialog (F051)**
   - File: `src/ui/file_menu/export_dialog.py` or `import_export_dialog.py`
   - Study 3 export types: Catalog, Backup, Context-Rich
   - Note how entity selection works (checkboxes)
   - Understand how services are called from UI

6. **UI Import Dialog (F051)**
   - Study 5 import purposes: Catalog, Backup, Context-Rich, Purchase Transaction, Coordinated
   - Note auto-detection logic
   - Understand mode selection UI
   - Study FK resolution callback pattern

7. **Materials Service (F047)**
   - File: `src/services/material_service.py` or similar
   - Study material catalog export/import functions
   - Note material product handling
   - Understand material category/subcategory patterns

8. **Purchase Service (F043)**
   - File: `src/services/purchase_service.py`
   - Study purchase export format
   - Note supplier integration
   - Understand purchase history tracking

---

## Requirements Reference

This specification addresses:
- **AI-Assisted Workflows**: CLI must support full import/export for external data generation
- **Mobile JSON Ingestion**: CLI enables BT Mobile and other apps to exchange data
- **First-Class CLI**: CLI should match UI capabilities, not be second-tier interface
- **Developer Experience**: CLI needed for testing, automation, CI/CD
- **Materials Management (F047-F048)**: CLI must expose materials entities
- **Supplier Support (F050-F051)**: CLI must expose supplier operations
- **Context-Rich Exports (F053)**: CLI must support "aug" file workflows

From: Project constitution principle of "pragmatic aspiration" - build for today (CLI parity) while architecting for tomorrow (API future)

---

## Functional Requirements

### FR-1: Add Backup/Restore Commands

**What it must do:**
- Add `backup` command - creates timestamped 16-entity coordinated export
- Add `restore` command - imports from backup directory (validates manifest first)
- Add `backup-list` command - shows available backups with metadata
- Add `backup-validate` command - verifies backup integrity (checksums)

**Command signatures:**
```bash
# Create backup
python -m src.utils.import_export_cli backup [-o OUTPUT_DIR] [--zip]

# Restore from backup
python -m src.utils.import_export_cli restore BACKUP_DIR [--mode MODE] [--interactive]

# List backups
python -m src.utils.import_export_cli backup-list [--dir BACKUPS_DIR]

# Validate backup
python -m src.utils.import_export_cli backup-validate BACKUP_DIR
```

**Pattern reference:** Study `export-complete` command implementation, extend for backup/restore workflow

**Success criteria:**
- [ ] `backup` command creates coordinated export with manifest
- [ ] `restore` command validates manifest and imports all entities
- [ ] `backup-list` shows available backups with entity counts
- [ ] `backup-validate` verifies all checksums match
- [ ] Backup operations work identically to UI File > Export Data > Backup

---

### FR-2: Add Catalog Import/Export Commands

**What it must do:**
- Add `catalog-export` command - exports catalog entities (7 types)
- Add `catalog-import` command - imports catalog with mode selection
- Add `catalog-validate` command - pre-import schema validation

**Catalog entities (7 types):**
1. Ingredients (with hierarchy)
2. Products (food products)
3. Recipes (with components, yield types)
4. Finished Units
5. Finished Goods
6. Materials (with hierarchy)
7. Material Products

**Command signatures:**
```bash
# Export catalog (all 7 entity types)
python -m src.utils.import_export_cli catalog-export -o OUTPUT_DIR [--entities TYPES]

# Export specific entities only
python -m src.utils.import_export_cli catalog-export -o OUTPUT_DIR --entities ingredients,products

# Import catalog
python -m src.utils.import_export_cli catalog-import INPUT_DIR [--mode MODE] [--interactive]

# Validate catalog before import
python -m src.utils.import_export_cli catalog-validate INPUT_DIR
```

**Modes:**
- `add` - Add new records only (skip existing)
- `augment` - Update existing records, add new (default)
- `replace` - Clear existing, import all (dangerous)

**Pattern reference:** Study UI ImportDialog catalog workflow, F051 mode selection

**Success criteria:**
- [ ] `catalog-export` creates separate JSON files for each entity type
- [ ] `catalog-import` supports all 3 modes (add/augment/replace)
- [ ] `catalog-validate` catches schema errors before import
- [ ] Entity selection via `--entities` flag works correctly
- [ ] Default exports all 7 catalog entity types

---

### FR-3: Add Context-Rich "Aug" Commands

**What it must do:**
- Add `aug-export` command - exports context-rich "aug_" files (F053 format)
- Add `aug-import` command - imports aug files with FK resolution
- Add `aug-validate` command - validates aug file format
- Support 7 entity types + "all" option

**Entity types (7 + all):**
1. ingredients
2. products
3. recipes
4. finished-units
5. finished-goods
6. materials
7. material-products
8. all (exports all 7)

**Command signatures:**
```bash
# Export aug files
python -m src.utils.import_export_cli aug-export -t TYPE -o OUTPUT_FILE

# Export all aug files
python -m src.utils.import_export_cli aug-export -t all -o OUTPUT_DIR

# Import aug file
python -m src.utils.import_export_cli aug-import INPUT_FILE [--interactive] [--skip-on-error]

# Validate aug file
python -m src.utils.import_export_cli aug-validate INPUT_FILE
```

**File naming (F053):**
- Prefix: `aug_` (not `view_` - F053 fix)
- Examples: `aug_ingredients.json`, `aug_products.json`

**Pattern reference:** Study F053 context-rich export format, copy CLIFKResolver pattern from existing import-view command

**Success criteria:**
- [ ] `aug-export` creates files with `aug_` prefix (not `view_`)
- [ ] `aug-export -t all` creates all 7 entity aug files
- [ ] `aug-import` handles FK resolution (interactive mode available)
- [ ] `aug-validate` checks schema and context field completeness
- [ ] Aug operations match UI File > Export Data > Context-Rich

---

### FR-4: Add Materials CLI Commands

**What it must do:**
- Add CLI commands for all materials entities (4 types)
- Support materials catalog export
- Support materials aug export
- Include in backup/restore operations

**Materials entities (4 types):**
1. Materials (material catalog)
2. Material Products (material items with brands/suppliers)
3. Material Categories
4. Material Subcategories

**Command signatures:**
```bash
# Export materials entities
python -m src.utils.import_export_cli export-materials OUTPUT_FILE
python -m src.utils.import_export_cli export-material-products OUTPUT_FILE
python -m src.utils.import_export_cli export-material-categories OUTPUT_FILE
python -m src.utils.import_export_cli export-material-subcategories OUTPUT_FILE

# Import materials (via catalog-import)
python -m src.utils.import_export_cli catalog-import INPUT_DIR --entities materials,material-products

# Aug export for materials
python -m src.utils.import_export_cli aug-export -t materials -o aug_materials.json
python -m src.utils.import_export_cli aug-export -t material-products -o aug_material_products.json
```

**Pattern reference:** Study ingredient export commands, copy pattern for materials

**Success criteria:**
- [ ] All 4 materials entities exportable individually
- [ ] Materials included in `catalog-export`
- [ ] Materials included in `backup` command
- [ ] Materials aug export works (`-t materials`, `-t material-products`)
- [ ] Materials import via `catalog-import` works

---

### FR-5: Add Supplier CLI Commands

**What it must do:**
- Add CLI command for supplier export
- Include suppliers in catalog operations
- Support supplier aug export
- Include in backup/restore

**Command signatures:**
```bash
# Export suppliers
python -m src.utils.import_export_cli export-suppliers OUTPUT_FILE

# Import suppliers (via catalog-import)
python -m src.utils.import_export_cli catalog-import INPUT_DIR --entities suppliers

# Suppliers included in backup
python -m src.utils.import_export_cli backup  # includes suppliers

# Aug export (if needed for AI workflows)
python -m src.utils.import_export_cli aug-export -t suppliers -o aug_suppliers.json
```

**Export format (F050):**
- Must include `supplier_slug` field
- Format matches UI export (F051)

**Pattern reference:** Study F050 supplier export service, copy ingredient export CLI pattern

**Success criteria:**
- [ ] `export-suppliers` command works
- [ ] Suppliers included in `catalog-export`
- [ ] Suppliers included in `backup` command
- [ ] Supplier import via `catalog-import` resolves slugs correctly
- [ ] Aug export for suppliers (if needed)

---

### FR-6: Add Purchase Tracking Commands

**What it must do:**
- Add CLI command for purchase export
- Support purchase history tracking
- Include purchases in backup

**Command signatures:**
```bash
# Export purchases
python -m src.utils.import_export_cli export-purchases OUTPUT_FILE

# Purchases included in backup
python -m src.utils.import_export_cli backup  # includes purchases
```

**Pattern reference:** Study F043 purchase service, copy export pattern

**Success criteria:**
- [ ] `export-purchases` command works
- [ ] Purchases included in `backup` command
- [ ] Purchase export includes supplier references
- [ ] Export format matches UI export

---

### FR-7: Update Documentation and Examples

**What it must do:**
- Update module docstring with current command list
- Add examples for all new commands
- Deprecate outdated examples
- Document AI workflow patterns
- Add mobile JSON ingestion examples

**Documentation sections:**
- Backup/restore workflows
- Catalog import/export workflows
- Context-rich "aug" workflows for AI
- Materials management CLI examples
- Supplier management CLI examples
- Complete command reference

**Pattern reference:** Study existing module docstring, expand with new commands

**Success criteria:**
- [ ] Module docstring shows all current commands
- [ ] Examples demonstrate common workflows
- [ ] AI-assisted workflow documented
- [ ] Mobile JSON ingestion examples present
- [ ] Deprecated commands marked clearly

---

## Out of Scope

**Explicitly NOT included in F055:**
- ❌ New export formats (use existing service formats)
- ❌ GraphQL or REST API (CLI wraps services, not new interfaces)
- ❌ Export scheduling/automation (future feature)
- ❌ Cloud backup integration (future feature)
- ❌ CLI interactive mode improvements beyond FK resolution
- ❌ Progress bars or spinners (keep simple)
- ❌ Color output or fancy formatting
- ❌ Configuration file for defaults (future enhancement)

---

## Success Criteria

**Complete when:**

### Backup/Restore
- [ ] `backup` command creates 16-entity coordinated export
- [ ] `restore` command imports from backup with validation
- [ ] `backup-list` shows available backups
- [ ] `backup-validate` verifies integrity
- [ ] Operations match UI backup workflow exactly

### Catalog Operations
- [ ] `catalog-export` exports 7 entity types
- [ ] `catalog-import` supports add/augment/replace modes
- [ ] `catalog-validate` catches schema errors
- [ ] Entity selection via `--entities` flag works
- [ ] Operations match UI catalog workflow exactly

### Context-Rich Operations
- [ ] `aug-export` creates files with `aug_` prefix (F053)
- [ ] `aug-export -t all` exports all 7 entity types
- [ ] `aug-import` handles FK resolution
- [ ] `aug-validate` checks schema
- [ ] Operations match UI context-rich workflow exactly

### Materials Support
- [ ] All 4 materials entities exportable individually
- [ ] Materials in `catalog-export`
- [ ] Materials in `backup`
- [ ] Materials aug export works
- [ ] Full parity with UI materials operations

### Supplier Support
- [ ] `export-suppliers` command works
- [ ] Suppliers in `catalog-export`
- [ ] Suppliers in `backup`
- [ ] Supplier slug resolution works
- [ ] Full parity with UI supplier operations

### Purchase Support
- [ ] `export-purchases` command works
- [ ] Purchases in `backup`
- [ ] Purchase export includes supplier references
- [ ] Full parity with UI purchase operations

### Documentation
- [ ] Module docstring updated
- [ ] All commands documented with examples
- [ ] AI workflow patterns documented
- [ ] Mobile JSON ingestion documented
- [ ] Help text accurate and complete

### Quality
- [ ] No errors when running all commands
- [ ] CLI output matches UI export formats exactly
- [ ] FK resolution works identically to UI
- [ ] Error messages clear and actionable
- [ ] All service functions called correctly

---

## Architecture Principles

### CLI as First-Class Interface

**Principle**: CLI should have feature parity with UI
- Every UI import/export operation accessible via CLI
- Same service layer called by both interfaces
- Identical file formats and validation

**Rationale**: 
- AI-assisted workflows depend on CLI
- Mobile JSON ingestion requires CLI
- Testing and automation need CLI
- Future API can learn from CLI patterns

### Command Structure

**Hierarchical organization:**
- Backup/restore commands (high-level operations)
- Catalog commands (entity collections)
- Aug commands (context-rich workflows)
- Entity-specific commands (granular access)

**Rationale**: 
- Clear hierarchy aids discovery
- Common workflows at top level
- Granular control when needed
- Follows UI organization

### Service Layer Reuse

**Never duplicate service logic in CLI:**
- CLI calls existing service functions
- FK resolution uses existing resolver
- Validation uses existing validators
- Error handling uses existing patterns

**Rationale**:
- DRY principle
- Consistency guaranteed
- One place to fix bugs
- Reduces maintenance

### Backward Compatibility

**Preserve existing commands:**
- Legacy `export` and `import` still work
- F030 commands (`export-complete`, etc.) unchanged
- New commands don't break old workflows

**Rationale**:
- Users may have scripts using old commands
- Migration path should be gradual
- Document deprecation, don't remove

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- All imports validate data before DB writes
- Backup/restore preserves referential integrity
- FK resolution maintains relationships

✅ **Principle II: Future-Proof Architecture**
- CLI patterns will inform future API design
- Service layer separation enables multi-interface
- Command structure scales to new entity types

✅ **Principle III: Layered Architecture**
- CLI layer wraps service layer cleanly
- No business logic in CLI commands
- Services remain interface-agnostic

✅ **Principle IV: Separation of Concerns**
- CLI handles user interaction only
- Services handle data operations
- Validation separate from import/export

✅ **Principle V: User-Centric Design**
- Command names match user mental model
- Help text clear and actionable
- Error messages guide resolution

✅ **Principle VI: Pragmatic Aspiration**
- Build for today: CLI parity enables current workflows
- Architect for tomorrow: Patterns inform future API
- Don't over-engineer: Simple command structure

---

## Risk Considerations

**Risk: CLI testing coverage incomplete**
- CLI commands may not be tested as thoroughly as UI
- Mitigation: Planning phase identifies test patterns
- Add CLI tests parallel to service tests
- Manual testing of all new commands required

**Risk: Service function signatures changed**
- Recent refactoring may have changed function names/signatures
- Mitigation: Planning phase discovers current service API
- Update CLI to match current service patterns
- Verify each service call works

**Risk: Context-rich export format unclear**
- F053 renamed "view" to "aug" but implementation may lag
- Mitigation: Planning phase finds actual export functions
- Verify prefix is "aug_" not "view_"
- Test exported files match UI format

**Risk: Materials entities incomplete in coordinated export**
- F049 predates F047 materials - may not include materials
- Mitigation: Planning phase checks coordinated_export_service
- Add materials to entity list if missing
- Verify backup includes all 16 entity types

**Risk: Documentation drift**
- Examples may become outdated as commands change
- Mitigation: Update docstring in same PR as commands
- Include examples in commit message
- Test examples before merging

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study existing CLI command structure (subparsers) → copy for new commands
- Study coordinated export service → use for backup/restore
- Study catalog import service → use for catalog-import
- Study CLIFKResolver → reuse for aug-import
- Find current service function signatures → update CLI calls

**Key Implementation Areas:**

**New Command Groups:**
1. Backup/restore (4 commands)
2. Catalog operations (3 commands)
3. Aug operations (3 commands)
4. Materials exports (4 commands)
5. Supplier/purchase exports (2 commands)

**Service Integration:**
- `coordinated_export_service.export_complete()` → backup command
- `import_service.import_catalog()` → catalog-import command (verify function name)
- Context-rich export functions → aug-export command (find actual function names)
- Material export functions → export-materials commands (verify exists)
- Supplier export function → export-suppliers command (F050)

**Validation:**
- Schema validation before import (find validator functions)
- Manifest validation for backup (validate_export function)
- Aug file format validation (add if missing)

**Documentation:**
- Update module docstring with 15+ new commands
- Add workflow examples (backup/restore, catalog, aug)
- Document AI patterns (aug export → augment → aug import)
- Document mobile patterns (export → transfer → import)

**Focus Areas:**
- All commands follow existing CLI patterns
- Service calls verified against current API
- Error handling matches existing commands
- Help text clear and actionable
- Module docstring comprehensive

---

**END OF SPECIFICATION**
