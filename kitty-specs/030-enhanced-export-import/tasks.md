# Work Packages: Enhanced Export/Import System

**Inputs**: Design documents from `/kitty-specs/030-enhanced-export-import/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md

**Tests**: Include tests per Constitution Principle IV (>70% service layer coverage).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Parallel Strategy**:
- Track A (Gemini): WP01 → WP02 → WP03 (Export services)
- Track B (Claude): WP04 → WP05 → WP06 → WP07 → WP08 (Import services + UI)
- Tracks A and B can run in parallel until WP08 integration.

---

## Work Package WP01: Coordinated Export Service (Priority: P0) - Gemini

**Goal**: Export complete database to individual entity files with manifest, checksums, and dependency ordering.
**Owner**: Gemini (Track A)
**Independent Test**: Export database, verify manifest.json contains correct checksums and import order.
**Prompt**: `tasks/planned/WP01-coordinated-export-service.md`

### Included Subtasks
- [ ] T001 Create ExportManifest and FileEntry dataclasses in `src/services/coordinated_export_service.py`
- [ ] T002 [P] Implement per-entity export functions with FK resolution fields (id + slug/name)
- [ ] T003 Implement manifest generation with SHA256 checksums
- [ ] T004 Implement dependency ordering logic for import order
- [ ] T005 Implement ZIP archive creation
- [ ] T006 Write unit tests in `src/tests/services/test_coordinated_export.py`

### Implementation Notes
1. Follow session=None pattern from `catalog_import_service.py`
2. Entity order: suppliers → ingredients → products → recipes → purchases → inventory
3. Each entity file includes both ID and slug/name for FK fields
4. Use `hashlib.sha256` for checksums

### Parallel Opportunities
- T002 can proceed per-entity in parallel once dataclasses exist

### Dependencies
- None (starting package for Track A)

### Risks & Mitigations
- Large entity counts → Use streaming JSON if >10k records (defer to post-MVP)

---

## Work Package WP02: Denormalized Export Service (Priority: P0) - Gemini

**Goal**: Export AI-friendly views with context (view_products.json, view_inventory.json, view_purchases.json).
**Owner**: Gemini (Track A)
**Independent Test**: Export products view, verify it includes ingredient name, supplier name, and editable field metadata.
**Prompt**: `tasks/planned/WP02-denormalized-export-service.md`

### Included Subtasks
- [ ] T007 [P] Implement `export_products_view()` with ingredient/supplier context in `src/services/denormalized_export_service.py`
- [ ] T008 [P] Implement `export_inventory_view()` with product/purchase context
- [ ] T009 [P] Implement `export_purchases_view()` with product/supplier context
- [ ] T010 Add `_meta.editable_fields` and `_meta.readonly_fields` to all view exports
- [ ] T011 Write unit tests in `src/tests/services/test_denormalized_export.py`

### Implementation Notes
1. Views are read-only aggregations - no session modifications
2. Include last_purchase_price, inventory_quantity as context fields
3. Editable fields per spec: brand, product_name, package_size, package_unit, upc_code, notes

### Parallel Opportunities
- T007, T008, T009 can proceed in parallel (different view types)

### Dependencies
- None (can start parallel to WP01)

### Risks & Mitigations
- Query performance with many joins → Use eager loading with joinedload

---

## Work Package WP03: Export CLI Commands (Priority: P1) - Gemini

**Goal**: Add CLI commands for export operations: export-complete, export-view, validate-export.
**Owner**: Gemini (Track A)
**Independent Test**: Run `python -m src.utils.import_export_cli export-complete test_export/` and verify output.
**Prompt**: `tasks/planned/WP03-export-cli-commands.md`

### Included Subtasks
- [ ] T012 Add `export-complete` command with --output and --zip flags to `src/utils/import_export_cli.py`
- [ ] T013 Add `export-view` command with --type flag (products, inventory, purchases)
- [ ] T014 Add `validate-export` command for manifest checksum verification
- [ ] T015 Write CLI smoke tests

### Implementation Notes
1. Follow existing argparse patterns in import_export_cli.py
2. Commands print summary and return exit codes (0 success, 1 failure)
3. --output defaults to timestamped directory

### Parallel Opportunities
- None (sequential after WP01/WP02)

### Dependencies
- Depends on WP01 (coordinated export) and WP02 (denormalized export)

### Risks & Mitigations
- None significant

---

## Work Package WP04: FK Resolver Service (Priority: P0) - Claude 🎯 MVP

**Goal**: Create shared FK resolution logic for CLI and UI with create/map/skip options.
**Owner**: Claude (Track B)
**Independent Test**: Call resolver with missing supplier, verify all three resolution paths work.
**Prompt**: `tasks/planned/WP04-fk-resolver-service.md`

### Included Subtasks
- [ ] T016 Create ResolutionChoice enum and MissingFK/Resolution dataclasses in `src/services/fk_resolver_service.py`
- [ ] T017 Define FKResolverCallback protocol for pluggable resolution strategies
- [ ] T018 Implement `resolve_missing_fks()` core logic with dependency ordering
- [ ] T019 Implement entity creation support (Supplier, Ingredient, Product)
- [ ] T020 Implement fuzzy search for "map to existing" option using existing entity lookups
- [ ] T021 Write unit tests in `src/tests/services/test_fk_resolver.py`

### Implementation Notes
1. Use session=None pattern for transactional composition
2. Dependency order: Supplier/Ingredient before Product
3. Fuzzy search can use simple case-insensitive substring match initially
4. Entity creation must validate required fields per model

### Parallel Opportunities
- T019 and T020 can proceed in parallel once protocol defined

### Dependencies
- None (starting package for Track B)

### Risks & Mitigations
- Session detachment → Follow session=None pattern strictly per CLAUDE.md

---

## Work Package WP05: Enhanced Import Service (Priority: P1) - Claude 🎯 MVP

**Goal**: Import denormalized views with FK resolution, merge/skip modes, dry-run, and skip-on-error.
**Owner**: Claude (Track B)
**Independent Test**: Import modified products view, verify only editable fields updated via merge mode.
**Prompt**: `tasks/planned/WP05-enhanced-import-service.md`

### Included Subtasks
- [ ] T022 Create EnhancedImportResult extending ImportResult in `src/services/enhanced_import_service.py`
- [ ] T023 Implement FK resolution via slug/name matching (not ID)
- [ ] T024 Implement merge mode (update existing, add new)
- [ ] T025 Implement skip_existing mode (only add new records)
- [ ] T026 Implement dry_run mode via session rollback
- [ ] T027 Implement skip-on-error mode with logging to `import_skipped_{timestamp}.json`
- [ ] T028 Integrate FK resolver for missing reference handling
- [ ] T029 Write unit tests in `src/tests/services/test_enhanced_import.py`

### Implementation Notes
1. Follow patterns from catalog_import_service.py
2. Only update editable fields from view metadata, ignore readonly
3. Log all errors, warnings, and resolutions per FR-026
4. Handle duplicate slugs per clarification: first occurrence wins for entities

### Parallel Opportunities
- T024/T025/T026/T027 can be developed as separate mode handlers

### Dependencies
- Depends on WP04 (FK resolver)

### Risks & Mitigations
- Product ambiguity → Warn on multiple matches, skip with logged warning

---

## Work Package WP06: Import CLI Commands (Priority: P2) - Claude

**Goal**: Add CLI commands for import operations with interactive FK resolution support.
**Owner**: Claude (Track B)
**Independent Test**: Run import-view with --dry-run flag, verify no DB changes.
**Prompt**: `tasks/planned/WP06-import-cli-commands.md`

### Included Subtasks
- [ ] T030 Add `import-view` command with --mode, --interactive, --skip-on-error, --dry-run flags to `src/utils/import_export_cli.py`
- [ ] T031 Implement CLI interactive FK resolution prompts (text-based menu)
- [ ] T032 Write CLI smoke tests

### Implementation Notes
1. --interactive shows text prompts: "Missing supplier 'X'. [C]reate, [M]ap, [S]kip?"
2. CLI default is fail-fast (no --interactive = error on missing FK)
3. Use input() for interactive prompts in CLI mode

### Parallel Opportunities
- None (sequential)

### Dependencies
- Depends on WP05 (enhanced import)

### Risks & Mitigations
- None significant

---

## Work Package WP07: FK Resolution Dialog (Priority: P2) - Claude

**Goal**: Create UI dialog for interactive FK resolution during import.
**Owner**: Claude (Track B)
**Independent Test**: Trigger missing FK during UI import, verify dialog appears with all options.
**Prompt**: `tasks/planned/WP07-fk-resolution-dialog.md`

### Included Subtasks
- [ ] T033 Create FKResolutionDialog with create/map/skip options in `src/ui/fk_resolution_dialog.py`
- [ ] T034 Implement fuzzy search dropdown for "map to existing" option
- [ ] T035 Implement entity creation form for "create new" (Supplier: name, city, state, zip)
- [ ] T036 Handle user cancellation with keep/rollback confirmation per clarification

### Implementation Notes
1. Follow modal dialog patterns from import_export_dialog.py
2. Use CTkInputDialog or custom form for entity creation
3. Cancellation prompts: "Keep X imported records, or rollback all?"

### Parallel Opportunities
- None (requires FK resolver from WP04)

### Dependencies
- Depends on WP04 (FK resolver service for shared logic)

### Risks & Mitigations
- UI complexity → Reuse existing dialog patterns

---

## Work Package WP08: UI Integration (Priority: P2) - Claude

**Goal**: Integrate import view functionality into main application UI.
**Owner**: Claude (Track B)
**Independent Test**: Use File > Import > Import View menu, complete full import flow.
**Prompt**: `tasks/planned/WP08-ui-integration.md`

### Included Subtasks
- [ ] T037 Add File > Import > Import View menu item in `src/ui/main_window.py`
- [ ] T038 Create import view dialog with file chooser and mode selection in `src/ui/import_export_dialog.py`
- [ ] T039 Integrate FK resolution wizard into import flow
- [ ] T040 Show results summary dialog after import (reuse ImportResultsDialog)
- [ ] T041 Manual UI testing of complete import flow

### Implementation Notes
1. Wire menu item to new import view dialog
2. Mode selection: merge (default), skip_existing
3. Results dialog shows: added, updated, skipped, failed counts

### Parallel Opportunities
- None (integration work)

### Dependencies
- Depends on WP05 (enhanced import), WP07 (FK resolution dialog)

### Risks & Mitigations
- None significant

---

## Dependency & Execution Summary

```
Track A (Gemini - Export):     WP01 ──→ WP02 ──→ WP03
                                 ↓ (parallel)  ↓
Track B (Claude - Import):     WP04 ──→ WP05 ──→ WP06 ──→ WP07 ──→ WP08
```

- **Sequence**: WP01/WP04 start parallel → WP02/WP05 → WP03/WP06 → WP07 → WP08
- **Parallelization**: Tracks A and B are fully independent until WP08 integration testing
- **MVP Scope**: WP01, WP02, WP04, WP05 constitute minimal viable export-import cycle

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | ExportManifest dataclasses | WP01 | P0 | No |
| T002 | Per-entity export with FK fields | WP01 | P0 | Yes |
| T003 | Manifest generation with checksums | WP01 | P0 | No |
| T004 | Dependency ordering logic | WP01 | P0 | No |
| T005 | ZIP archive creation | WP01 | P0 | No |
| T006 | Coordinated export tests | WP01 | P0 | No |
| T007 | export_products_view | WP02 | P0 | Yes |
| T008 | export_inventory_view | WP02 | P0 | Yes |
| T009 | export_purchases_view | WP02 | P0 | Yes |
| T010 | Editable/readonly metadata | WP02 | P0 | No |
| T011 | Denormalized export tests | WP02 | P0 | No |
| T012 | export-complete CLI command | WP03 | P1 | No |
| T013 | export-view CLI command | WP03 | P1 | No |
| T014 | validate-export CLI command | WP03 | P1 | No |
| T015 | Export CLI tests | WP03 | P1 | No |
| T016 | Resolution dataclasses | WP04 | P0 | No |
| T017 | FKResolverCallback protocol | WP04 | P0 | No |
| T018 | resolve_missing_fks logic | WP04 | P0 | No |
| T019 | Entity creation support | WP04 | P0 | Yes |
| T020 | Fuzzy search for mapping | WP04 | P0 | Yes |
| T021 | FK resolver tests | WP04 | P0 | No |
| T022 | EnhancedImportResult | WP05 | P1 | No |
| T023 | FK resolution via slug | WP05 | P1 | No |
| T024 | Merge mode | WP05 | P1 | Yes |
| T025 | Skip_existing mode | WP05 | P1 | Yes |
| T026 | Dry_run mode | WP05 | P1 | Yes |
| T027 | Skip-on-error mode | WP05 | P1 | Yes |
| T028 | FK resolver integration | WP05 | P1 | No |
| T029 | Enhanced import tests | WP05 | P1 | No |
| T030 | import-view CLI command | WP06 | P2 | No |
| T031 | CLI interactive prompts | WP06 | P2 | No |
| T032 | Import CLI tests | WP06 | P2 | No |
| T033 | FKResolutionDialog | WP07 | P2 | No |
| T034 | Fuzzy search dropdown | WP07 | P2 | No |
| T035 | Entity creation form | WP07 | P2 | No |
| T036 | Cancellation handling | WP07 | P2 | No |
| T037 | Menu item in main_window | WP08 | P2 | No |
| T038 | Import view dialog | WP08 | P2 | No |
| T039 | FK wizard integration | WP08 | P2 | No |
| T040 | Results summary dialog | WP08 | P2 | No |
| T041 | Manual UI testing | WP08 | P2 | No |
