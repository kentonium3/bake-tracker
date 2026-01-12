# Import/Export System Requirements

**Document Version**: 2.0
**Date**: 2026-01-11
**Status**: Draft
**Document Type**: Requirements (WHAT the system must do)

---

## Executive Summary

The import/export system must enable:
- Complete backup and restoration of system state
- AI-assisted catalog augmentation with maximum context
- Mobile app integration for transactional data entry
- External data analysis capabilities
- Flexible schema migration through external transformation

This document defines **what** the system must do, not **how** it will be implemented.

---

## Stakeholders

**Primary Users:**
- Marianne (baker) - Needs backup before risky changes, wants AI help expanding catalogs
- Kent (developer) - Needs test data preservation, schema migration flexibility

**Secondary Systems:**
- AI agents (Claude, mobile app AI) - Need rich context for augmentation
- External analysis tools - Need structured data exports
- Mobile prototype app - Needs batch data sync

---

## Business Context

### Problem Statement

**Current Pain Points:**
1. No reliable backup/restore mechanism
2. Manual data entry is time-consuming (catalog expansion, purchases)
3. AI augmentation requires data in specific formats
4. Schema changes risk data loss
5. No way to bootstrap initial inventory without fake purchases

### Business Value

**Enabling backup/restore:**
- Safety net for risky operations (schema changes, bulk edits)
- Preserves realistic test data from user sessions
- Reduces fear of data loss, encourages experimentation

**Enabling AI augmentation:**
- Faster catalog expansion (ingredients, materials)
- Better product categorization (industry codes, attributes)
- Reduced manual data entry burden

**Enabling mobile sync:**
- Capture purchases during shopping (faster, more accurate)
- Record inventory adjustments in real-time
- Create recipes using voice/photos

**Enabling schema migration:**
- Transform exported JSON externally before re-import
- More flexible than maintaining backward-compatibility code
- Appropriate for current development phase (frequent schema changes)

---

## Functional Requirements

### FR-1: Full Backup and Restore

**Description**: System must export complete state and restore to exact prior state.

**Must Support:**
- Export all catalog entities (ingredients, products, materials, recipes, finished goods, suppliers, material units)
- Export all transactional data (purchases, material purchases, inventory items, events, production runs, consumption records)
- Export all relationships and foreign keys
- Create self-contained backup folder with manifest
- Validate backup before restoration
- Restore exact state (all counts, relationships, history)

**Must NOT:**
- Lose data during export
- Create partial backups (all-or-nothing)
- Allow restoration from corrupted backup

**Success Criteria:**
- After restore, system state identical to export time
- All relationships intact (no orphaned records)
- Inventory counts match exactly
- Transaction history preserved

**Example Scenario:**
> Marianne completes user testing session with realistic data. Kent exports full backup before schema migration. Migration fails. Kent imports backup and restores exact state. No data lost.

---

### FR-2: Initial Inventory Setup

**Description**: System must allow one-time inventory creation without purchase records.

**Must Support:**
- Import existing pantry/materials inventory on day 1
- Set initial cost basis for COGS tracking
- Flag inventory as "initial" source (not from purchases)
- Prevent repeated initial imports for same product

**Must NOT:**
- Create fake purchase records to bootstrap inventory
- Allow initial import after purchases exist
- Allow inventory increases via initial import after setup

**Success Criteria:**
- New user can bootstrap inventory from existing stock
- Cost basis set for accurate COGS calculations
- Clear distinction between initial inventory and purchased inventory

**Example Scenario:**
> Marianne starts using app with existing pantry: 5 bags flour, 3 jars vanilla, etc. She creates initial_inventory file with estimates ($18.99/bag flour). System creates inventory without fake purchases. Cost basis set. Future increases only via purchases.

---

### FR-3: Catalog Import (Batch Operations)

**Description**: System must import catalog definitions in batch for efficiency.

**Must Support:**
- Import ingredients (with hierarchy)
- Import products (linked to ingredients)
- Import materials (with hierarchy)
- Import material products (linked to materials)
- Import material units
- Import recipes (base + variants)
- Import suppliers
- Resolve slug-based references to database IDs
- Two modes: ADD_ONLY (skip existing), AUGMENT (update existing)
- Validation before commit
- Detailed error reporting (which records failed, why)

**Must NOT:**
- Use database IDs as references (must use slugs)
- Allow duplicate slugs
- Break referential integrity
- Silently skip failures

**Success Criteria:**
- Batch import of 100+ catalog items works reliably
- Slug references resolve correctly
- ADD_ONLY mode safe for incremental additions
- AUGMENT mode updates existing without creating duplicates

**Example Scenario:**
> Kent creates ingredient catalog with 50 new items. Uses ADD_ONLY mode. System skips 10 existing, creates 40 new. Reports: "40 created, 10 skipped (already exist)". No duplicates created.

---

### FR-4: AI-Friendly Catalog Export

**Description**: System must export catalog with maximum context for AI augmentation.

**Must Support:**
- Include full hierarchy paths (not just parent IDs)
- Include descriptions and usage notes
- Include current inventory/cost information (as context, not for import)
- Include relationships (ingredient → products)
- Include computed values (e.g., "90 cups per 25 lb bag")
- Self-documenting field names
- Human-readable format
- Support for AI adding: descriptions, categories, industry codes, attributes, images, alternative names

**Must NOT:**
- Include database IDs
- Include internal implementation details
- Require AI to know database schema

**Success Criteria:**
- AI can understand catalog without schema knowledge
- AI can add enrichment without breaking import
- Human can review/edit exported data
- Augmented data imports correctly

**Example Scenario:**
> Kent exports ingredients for AI augmentation. Claude reads export, sees "Flour, all-purpose" with context: hierarchy path, density, current products, usage notes. Claude adds: description, alternative names ("AP flour", "plain flour"), typical uses, shelf life, storage tips. Kent imports augmented data. System updates existing records with new fields.

**Context Requirements:**
- Hierarchy: Full path (e.g., "Flours & Starches > Wheat Flours > All-Purpose")
- Relationships: Nested objects (ingredient contains its products)
- Computed values: "1 cup = 4.42 oz", "25 lb = 90 cups (approx)"
- Current state: Inventory levels, average costs (for context only)
- Descriptive fields: Labels like "full_description", "common_names", "usage_notes"

---

### FR-5: Transactional Import (Purchases)

**Description**: System must import purchase transactions from mobile app or batch entry.

**Must Support:**
- Import food purchases (products)
- Import material purchases (material products)
- Create purchase records
- Update inventory (increase quantities)
- Recalculate weighted average costs
- Validate product references (slug → ID)
- Prevent duplicate detection (same product, date, cost)

**Must NOT:**
- Allow negative purchase quantities
- Create inventory without purchase records (except initial setup)
- Break inventory calculations

**Success Criteria:**
- Mobile app can sync purchases in batch
- Inventory increased correctly
- Weighted average costs updated
- Duplicate prevention works

**Example Scenario:**
> Marianne shops at Costco. Mobile app captures 5 purchases. Exports JSON. Kent imports. System creates 5 purchase records, increases inventory by correct amounts, recalculates costs. No duplicates even if imported twice.

---

### FR-6: Inventory Adjustments (Decreases Only)

**Description**: System must record inventory decreases for waste, spoilage, corrections.

**Must Support:**
- Import inventory decreases only (negative quantities)
- Require reason code (spoilage, waste, correction, other)
- Create adjustment records with notes
- Update inventory (decrease quantities)
- Validate sufficient inventory exists

**Must NOT:**
- Allow positive quantity adjustments (increases only via purchases)
- Allow adjustments that create negative inventory

**Success Criteria:**
- Waste/spoilage properly recorded
- Inventory counts accurate after adjustments
- Positive adjustments rejected with clear error

**Example Scenario:**
> Flour bag torn, contents contaminated. Marianne creates adjustment: -0.5 bag, reason: "waste", notes: "torn bag". System decreases inventory, creates adjustment record. Later tries positive adjustment, system rejects: "Inventory increases only via purchases."

---

### FR-7: Recipe Import

**Description**: System must import recipes and recipe variants.

**Must Support:**
- Import base recipes
- Import recipe variants (linked to base)
- Resolve ingredient slug references
- Preserve yield calculations
- Prevent duplicate recipe slugs

**Must NOT:**
- Create orphaned variants (base must exist)
- Break ingredient references
- Duplicate recipes

**Success Criteria:**
- AI can create recipe variants
- Mobile app can sync new recipes
- Variants correctly linked to base recipes

**Example Scenario:**
> Mobile app creates chocolate chip cookie recipe with 3 variants. Exports JSON. System imports base recipe first, then 3 variants. All linked correctly. Ingredient references resolved.

---

## Business Rules

### BR-1: Inventory Increase Control

**Rule**: Inventory increases are tightly controlled to maintain data integrity and accurate cost basis.

**Allowed Operations:**
1. **Initial Setup** (one-time per product): Direct inventory creation with estimated costs
2. **Purchases** (ongoing): All purchases increase inventory and update costs
3. **Admin Correction** (future, rare): Manual override with approval

**Prohibited Operations:**
- Direct inventory increases after initial setup
- Positive inventory adjustments
- Backdating inventory without purchase record

**Rationale:**
- Maintains purchase history integrity
- Ensures accurate cost basis for COGS
- Creates clear audit trail
- Prevents accidental inventory inflation

**Validation:**
- Initial inventory import: Check no existing inventory for product
- Inventory adjustment import: Reject positive values
- Purchase import: Standard mechanism for increases

---

### BR-2: Reference Stability (Slug-Based)

**Rule**: All import/export operations use immutable slug-based references, never database IDs.

**Requirements:**
- Catalog entities must have unique slugs
- Slugs are immutable after creation (display_name can change)
- Import service resolves slugs to database IDs
- Export service uses slugs (never IDs)

**Rationale:**
- Database IDs not portable across databases
- Slugs human-readable (easier debugging, manual editing)
- Slugs enable merge from different database instances
- Slugs stable across export/import cycles

**Examples:**
- ✅ Correct: `"ingredient_slug": "flour_all_purpose"`
- ❌ Wrong: `"ingredient_id": 42`

---

### BR-3: Import Modes

**Rule**: Catalog imports support two distinct modes with clear semantics.

**ADD_ONLY Mode** (default, safe):
- Creates new records only
- Skips existing records (matched by slug)
- Safe for incremental additions
- No updates, no deletes

**AUGMENT Mode** (requires confirmation):
- Creates new records
- Updates existing records (matched by slug)
- Merges data (preserves unspecified fields)
- No deletes

**Intentionally Not Supported:**
- REPLACE mode (too destructive, use backup/restore)
- DELETE operations via import (use UI)

**Rationale:**
- ADD_ONLY is safe default for batch additions
- AUGMENT enables AI-assisted enhancement
- REPLACE too risky (accidental data loss)

---

### BR-4: Format Types

**Rule**: System supports two export formats for different purposes.

**Normalized Format** (machine-optimized):
- **Purpose**: Machine processing, import operations, backup
- **Characteristics**: Compact, slug references, no redundancy
- **Use Cases**: Batch operations, mobile sync, backup/restore

**Context-Rich Format** (human/AI-optimized):
- **Purpose**: Human review, AI augmentation, external analysis
- **Characteristics**: Verbose, nested objects, full context, computed values
- **Use Cases**: AI workflows, data analysis, documentation
- **Context Includes**: Hierarchy paths, relationships, inventory levels, costs, descriptions

**Requirements:**
- Export clearly indicates format
- Import auto-detects format from structure
- Services convert between formats as needed

**Key Difference**: Context-rich format provides **maximum supporting information** to help AI systems perform their tasks effectively (search, categorization, enrichment) without knowing database schema.

---

### BR-5: Schema Migration Strategy

**Rule**: During development phase, schema changes handled via external JSON transformation, not code-based migration.

**Approach**:
1. Export data from old schema
2. Transform JSON externally (version-specific script)
3. Import to new schema

**Rationale:**
- Schema still evolving (frequent changes expected)
- Single user (can manually transform)
- Flexibility > automation (can inspect/edit transformations)
- Import service stays simple (handles current version only)
- Transform scripts are one-time (can discard after use)

**Future Transition**: Add automatic migration when schema stabilizes (v1.0+) and user base grows.

---

## Non-Functional Requirements

### NFR-1: Performance

**Requirements:**
- Export 1000 records: < 10 seconds
- Import 1000 records: < 30 seconds
- Full backup export: < 60 seconds (typical database)
- Full backup import: < 120 seconds

**Rationale:** Acceptable for desktop app, single user, occasional operations

---

### NFR-2: Reliability

**Requirements:**
- Export is atomic (all-or-nothing)
- Import validates before committing
- Import is idempotent (can re-run safely)
- Detailed error messages (which records failed, why)
- Backup folder self-contained (no external dependencies)

---

### NFR-3: Usability

**Requirements:**
- Clear operation type selection (backup vs catalog vs transactions)
- Format auto-detection (user doesn't choose)
- Dry-run preview available before import
- Progress indicators for long operations
- Success/failure summary with counts

---

### NFR-4: Data Integrity

**Requirements:**
- Referential integrity maintained (FKs resolve correctly)
- No data loss during export/import cycles
- Validation before commit (all-or-nothing)
- Slug uniqueness enforced
- Inventory calculations accurate after import

---

## Out of Scope
## Success Metrics

### User Satisfaction
- Marianne can backup/restore confidently
- Marianne can bootstrap inventory without confusion
- Kent can migrate schemas without data loss
- AI augmentation workflow "just works"

### Technical Validation
- Zero data loss in backup/restore cycles
- Slug references resolve 100% correctly
- Import validation catches errors before commit
- Inventory calculations accurate after imports

### Adoption
- Marianne uses backup before risky operations
- Marianne uses AI augmentation for catalog expansion
- Mobile app sync used for shopping trips

---

## Implementation Phases (Priority Order)

### Phase 1: Critical Foundation
**Priority**: HIGH  
**Requirements**: FR-1 (Full Backup), FR-3 (Catalog Import - materials support)  
**Business Value**: Safety net, fix materials import failure  
**Estimated Effort**: 4-6 hours

### Phase 2: Initial Setup
**Priority**: HIGH  
**Requirements**: FR-2 (Initial Inventory)  
**Business Value**: Enable realistic initial state without fake purchases  
**Estimated Effort**: 3-4 hours

### Phase 3: Batch Operations
**Priority**: MEDIUM  
**Requirements**: FR-3 (full catalog import support), ADD_ONLY/AUGMENT modes  
**Business Value**: Efficient batch operations  
**Estimated Effort**: 6-8 hours

### Phase 4: AI Augmentation
**Priority**: MEDIUM  
**Requirements**: FR-4 (Context-Rich Export/Import)  
**Business Value**: AI-assisted catalog expansion  
**Estimated Effort**: 8-10 hours

### Phase 5: Mobile Integration
**Priority**: LOW (future)  
**Requirements**: FR-5 (Purchase Import), FR-6 (Inventory Adjustments), FR-7 (Recipe Import)  
**Business Value**: Mobile app sync  
**Estimated Effort**: 12-16 hours

---

## Acceptance Criteria

### For Full Backup/Restore (FR-1)
- [ ] Export creates timestamped folder with all entity files
- [ ] Export includes manifest with entity counts
- [ ] Export includes all current entities (ingredients, products, materials, material_products, material_units, recipes, finished_goods, suppliers, inventory_items, purchases, material_purchases, events, production_runs, consumption_records)
- [ ] Import validates manifest before restoration
- [ ] Import restores exact state (verified by comparing entity counts)
- [ ] After restore, all relationships intact (spot-check FKs)

### For Initial Inventory (FR-2)
- [ ] Import creates inventory without purchase records
- [ ] Import sets cost basis from provided estimates
- [ ] Import rejects if inventory already exists for product
- [ ] Inventory flagged as "initial" source
- [ ] Cannot repeat initial import for same product

### For Catalog Import (FR-3)
- [ ] Import resolves ingredient_slug to ingredient_id
- [ ] Import resolves material_slug to material_id
- [ ] ADD_ONLY mode skips existing, creates new
- [ ] AUGMENT mode updates existing, creates new
- [ ] Import reports detailed errors (record number, field, reason)
- [ ] Import with materials checkbox works (UI fix)

### For AI-Friendly Export (FR-4)
- [ ] Export includes full hierarchy paths
- [ ] Export includes nested relationships
- [ ] Export includes computed values (inventory, costs) as context
- [ ] Export includes descriptive field names
- [ ] AI can read and understand without schema knowledge
- [ ] AI-augmented import updates existing records correctly

### For Purchase Import (FR-5)
- [ ] Import creates purchase records
- [ ] Import increases inventory correctly
- [ ] Import recalculates weighted average costs
- [ ] Import prevents duplicates (same product/date/cost)

### For Inventory Adjustments (FR-6)
- [ ] Import accepts negative quantities only
- [ ] Import rejects positive quantities with clear error
- [ ] Import requires reason code
- [ ] Import creates adjustment records
- [ ] Import validates sufficient inventory

### For Recipe Import (FR-7)
- [ ] Import creates base recipes
- [ ] Import creates variants linked to base
- [ ] Import resolves ingredient_slug references
- [ ] Import prevents duplicate recipe slugs

---

## Dependencies

**System Components:**
- Ingredient service (slug resolution)
- Product service (slug resolution)
- Material catalog service (slug resolution)
- Purchase service (inventory updates, cost calculations)
- Recipe service (variant relationships)
- Database (SQLite)

**External Systems:**
- Mobile prototype app (transaction exports)
- AI systems (catalog augmentation)
- External analysis tools (data exports)

**Data Requirements:**
- All catalog entities have unique slugs
- Slugs are immutable after creation
- Referential integrity maintained in database

---

## Risks and Mitigation

### Risk: Data Loss During Import
**Likelihood**: Medium  
**Impact**: HIGH  
**Mitigation**: Validate before commit, atomic transactions, encourage backup before import

### Risk: Slug Conflicts
**Likelihood**: Low  
**Impact**: Medium  
**Mitigation**: Unique constraint on slugs, clear error messages, manual resolution guide

### Risk: AI Augmentation Breaks Import
**Likelihood**: Medium  
**Impact**: Medium  
**Mitigation**: Ignore unknown fields, validate structure, provide examples

### Risk: Schema Migration Complexity
**Likelihood**: High (during development)  
**Impact**: Medium  
**Mitigation**: JSON transform approach, version-specific scripts, manual review

---

## Open Questions
## Glossary

**Catalog Data**: Definitions and templates (ingredients, products, materials, recipes)  
**Transactional Data**: Events and history (purchases, inventory adjustments, production runs)  
**Slug**: Immutable, human-readable identifier (e.g., "flour_all_purpose")  
**Normalized Format**: Compact, slug-based references, machine-optimized  
**Context-Rich Format**: Verbose, nested objects with maximum supporting information, human/AI-optimized  
**ADD_ONLY**: Import mode that creates new records, skips existing  
**AUGMENT**: Import mode that creates new records, updates existing  
**Initial Inventory**: One-time setup operation creating inventory without purchases

---

**END OF REQUIREMENTS DOCUMENT**

## Open Questions - RESOLVED

### 1. Transactional Export Format
**Question**: Should transactional export for analysis be context-rich or normalized?  
**DECISION**: Normalized  
**Rationale**: Transactional exports (if needed) will use normalized format. Not in scope for initial phases.

### 2. Finished Goods Import
**Question**: Should we support finished goods import with complex assembly hierarchies?  
**DECISION**: Defer indefinitely (not needed)  
**Rationale**: End-to-end workflow feature coverage is higher priority than finished goods import. Full backup includes finished goods if needed.

### 3. Production Runs Export
**Question**: Should production runs be exportable separately for analysis?  
**DECISION**: Defer indefinitely  
**Rationale**: Full backup includes production runs. Separate export not needed. No analysis requirements identified.

### 4. Schema Version Blocking
**Question**: Should we block import of incompatible schema versions?  
**DECISION**: Yes, block non-current schemas  
**Rationale**: Prevent data corruption and unpredictable behavior. Force users to run schema migration (JSON transform) first before importing old backups.

### 5. Admin Inventory Corrections
**Question**: Should we allow positive inventory adjustments with admin approval?  
**DECISION**: Defer  
**Rationale**: Purchase-only enforcement sufficient for current needs. Can add admin override later if legitimate use case emerges. Keeps rules simple.

---

## Glossary

## Out of Scope

**Explicitly NOT Requirements:**

### Current Phase Exclusions
- ❌ Real-time sync (batch operations only)
- ❌ Incremental backups (full backup sufficient)
- ❌ Cloud storage integration (local files only)
- ❌ Automatic backup scheduling (manual only)
- ❌ Multi-user conflict resolution (single user)

### Deferred Indefinitely (Not Needed)
- ❌ Finished goods import (end-to-end workflow coverage higher priority; full backup includes if needed)
- ❌ Production runs separate export (full backup includes; no separate analysis requirements)
- ❌ Admin inventory corrections (purchase-only enforcement sufficient; can add if legitimate use case emerges)

### Future Considerations (If Needed)
- ❌ Transactional export for analysis (normalized format; no current requirements)
- ❌ Backward-compatible schema import (use external JSON transform; block old schemas on import)

---

## Success Metrics

### NFR-5: Schema Version Compatibility

**Requirements:**
- Import must validate schema version from manifest
- Import must reject backups from incompatible schema versions
- Error message must indicate required migration steps
- Export must include current schema version in manifest

**Validation Rules:**
- Import current version: Allowed
- Import older version: Blocked with migration instructions
- Import newer version: Blocked with upgrade instructions

**Error Message Template**:
```
Backup schema version X.Y.Z is not compatible with current version A.B.C.

Please run schema migration before importing:
1. python scripts/migrations/transform_vXYZ_to_vABC.py backup_dir/ migrated_dir/
2. Import migrated_dir/ instead

See docs/migrations/vXYZ_to_vABC.md for details.
```

**Rationale**: Prevents data corruption and unpredictable behavior from schema mismatches. Forces explicit migration step for safety.

---

## Risks and Mitigation
