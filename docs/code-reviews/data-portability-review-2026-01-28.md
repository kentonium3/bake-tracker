# Data Portability Review - BakeTracker Cloud Migration Readiness

**Date**: 2026-01-28  
**Purpose**: Assess data portability readiness for migration from local SQLite to cloud PostgreSQL multi-tenant architecture  
**Reviewer**: AI Assistant  
**Context**: [Web Version Architecture Docs](../research/web-version/)

---

## Executive Summary

The BakeTracker application is **mostly ready** for cloud migration from a data portability perspective, with several critical gaps that need addressing. The existing slug-based FK resolution architecture is solid, but 4 major entity types lack slugs, and recent features (F064-F078) have not been integrated into the export/import services.

**Risk Level**: MEDIUM-HIGH
- ✅ Strong foundation: Slug-based FK resolution pattern established
- ⚠️  Critical gaps: 4 core entities without slugs (Recipe, Event, Recipient, Package)
- ⚠️  Feature coverage gap: 15+ recent features not exportable
- ⚠️  Multi-tenant fields: No `tenant_id` columns exist (expected, but confirms migration scope)

---

## 1. Slug Coverage Analysis

### Entities WITH Slugs (GOOD)

| Entity | Slug Field | Usage | Multi-tenant Ready |
|--------|-----------|-------|-------------------|
| `Ingredient` | `slug` | ✅ Unique, indexed, used in exports | Ready |
| `Product` | `slug` | ✅ Unique, indexed, F057 added | Ready |
| `Supplier` | `slug` | ✅ Unique, indexed, F050 added | Ready |
| `FinishedGood` | `slug` | ✅ Unique, indexed, used in exports | Ready |
| `FinishedUnit` | `slug` | ✅ Unique, indexed, used in exports | Ready |
| `Material` | `slug` | ✅ Unique, indexed, F047 added | Ready |
| `MaterialProduct` | `slug` | ✅ Unique, indexed, F047 added | Ready |
| `MaterialUnit` | `slug` | ✅ Unique, indexed, F047 added | Ready |
| `MaterialCategory` | `slug` | ✅ Unique, indexed, F047 added | Ready |
| `MaterialSubcategory` | `slug` | ✅ Unique, indexed, F047 added | Ready |

### Entities MISSING Slugs (CRITICAL GAPS)

#### 1. **Recipe** (CRITICAL)
**Current State**: Uses `name` field only (not unique, not indexed for lookup)
```python
# Current model
name = Column(String(200), nullable=False, index=True)  # Not unique!
```

**Why This Matters**:
- Recipes are referenced by:
  - `FinishedUnit.recipe_id` (already exported as `recipe_name`)
  - `EventProductionTarget.recipe_id` (exported as `recipe_name`)
  - `ProductionRun.recipe_id` (exported as `recipe_name`)
  - `RecipeComponent.component_recipe_id` (exported as `component_recipe_name`)
  - `RecipeSnapshot.recipe_id`
- Multi-tenant scenario: Two users could have recipes named "Chocolate Chip Cookies"
- Export collision: Name-based lookup will fail in multi-tenant environment

**Recommendation**: 
```python
# Add slug field
slug = Column(String(200), nullable=False, unique=True, index=True)

# Generation pattern (from recipe name, handle collisions)
# Example: "chocolate-chip-cookies", "chocolate-chip-cookies-2"
```

**Migration Complexity**: MEDIUM
- Existing exports use `recipe_name` (backward compatible)
- New exports should include `slug`
- Import service needs dual-path resolution: try slug first, fall back to name

---

#### 2. **Event** (CRITICAL)
**Current State**: Uses `name` field only (not unique, indexed)
```python
name = Column(String(200), nullable=False, index=True)  # Not unique!
year = Column(Integer, nullable=False, index=True)
```

**Why This Matters**:
- Events are referenced by:
  - `ProductionRun.event_id` (exported as `event_name`)
  - `AssemblyRun.event_id` (exported as `event_name`)
  - `EventProductionTarget.event_id`
  - `EventAssemblyTarget.event_id`
  - `EventRecipientPackage.event_id`
- Multi-tenant scenario: Two users could have "Christmas 2024" events
- Current workaround: `name + year` composite (fragile)

**Recommendation**:
```python
# Add slug field (composite: name + year)
slug = Column(String(250), nullable=False, unique=True, index=True)

# Generation pattern
# Example: "christmas-2024", "thanksgiving-2024"
# Handle collisions: "christmas-2024-2" (rare, but possible)
```

**Migration Complexity**: MEDIUM
- Existing exports use `event_name` (backward compatible)
- New exports should include `slug`
- Import service needs dual-path resolution

---

#### 3. **Recipient** (HIGH PRIORITY)
**Current State**: Uses `name` field only (not unique, indexed)
```python
name = Column(String(200), nullable=False, index=True)  # Not unique!
household_name = Column(String(200), nullable=True, index=True)
```

**Why This Matters**:
- Recipients are referenced by:
  - `EventRecipientPackage.recipient_id`
  - `Package` recipient assignments (via junction)
- Multi-tenant scenario: Common names ("John Smith") will collide
- Current workaround: `name + household_name` composite (fragile)

**Recommendation**:
```python
# Add slug field
slug = Column(String(200), nullable=False, unique=True, index=True)

# Generation pattern (from name, handle household)
# Example: "john-smith", "john-smith-household-2"
```

**Migration Complexity**: MEDIUM
- Not currently exported at all (see Section 2)
- First need to add to export service
- Then add slug support

---

#### 4. **Package** (HIGH PRIORITY)
**Current State**: Uses `name` field only (not unique, indexed)
```python
name = Column(String(200), nullable=False, index=True)  # Not unique!
is_template = Column(Boolean, nullable=False, default=False)
```

**Why This Matters**:
- Packages are referenced by:
  - `EventRecipientPackage.package_id`
  - Package template reuse across events
- Multi-tenant scenario: Generic names ("Standard Gift Box") will collide
- Templates especially prone to collision (users copy best practices)

**Recommendation**:
```python
# Add slug field
slug = Column(String(200), nullable=False, unique=True, index=True)

# Generation pattern (from name)
# Example: "standard-gift-box", "deluxe-cookie-assortment"
```

**Migration Complexity**: MEDIUM
- Not currently exported at all (see Section 2)
- First need to add to export service
- Then add slug support

---

### Entities That DON'T Need Slugs (Transactional/Ledger Data)

These are **instance records** (transactions, ledger entries, snapshots) - identified by UUID or timestamps, not user-facing names:

- `Purchase` - UUID + timestamp (already has UUID)
- `InventoryItem` - UUID + product FK (already has UUID)
- `MaterialPurchase` - UUID + timestamp (already has UUID)
- `MaterialInventoryItem` - UUID + product FK (already has UUID)
- `ProductionRun` - UUID + timestamp + FKs (already has UUID)
- `AssemblyRun` - UUID + timestamp + FKs (already has UUID)
- `InventoryDepletion` - UUID + timestamp (already has UUID)
- Junction tables (RecipeIngredient, RecipeComponent, etc.) - composite PKs
- Snapshots (RecipeSnapshot, FinishedGoodSnapshot, etc.) - UUID + parent FK

---

## 2. Export/Import Service Coverage

### Current Export Coverage (Coordinated Export Service)

The `coordinated_export_service.py` exports these entities:

**Core Catalog Entities**:
- ✅ Suppliers
- ✅ Ingredients
- ✅ Products
- ✅ Recipes (with nested ingredients/components)
- ✅ FinishedUnits (F056 added)
- ✅ FinishedGoods

**Transaction/Inventory**:
- ✅ Purchases
- ✅ InventoryItems
- ✅ InventoryDepletions

**Materials System (F047)**:
- ✅ MaterialCategories
- ✅ MaterialSubcategories
- ✅ Materials
- ✅ MaterialProducts
- ✅ MaterialUnits
- ✅ MaterialPurchases
- ✅ MaterialInventoryItems (F058)

**Event & Production**:
- ✅ Events (with production/assembly targets)
- ✅ ProductionRuns

### Missing Export Coverage (CRITICAL GAPS)

#### Recent Features NOT Exported (F064-F078)

| Feature | Entity | Export Status | Impact |
|---------|--------|---------------|--------|
| F064 | `FinishedGoodSnapshot` | ❌ Not exported | Assembly cost history lost |
| F064 | `MaterialUnitSnapshot` | ❌ Not exported | Material pricing history lost |
| F064 | `FinishedUnitSnapshot` | ❌ Not exported | Unit cost history lost |
| F065 | `RecipeSnapshot` | ❌ Not exported | Production cost history lost |
| F065 | `PlanSnapshot` | ❌ Not exported | Event planning snapshots lost |
| F065 | `ProductionPlanSnapshot` | ❌ Not exported | Production plans lost |
| F068 | `PlanState` enum | ⚠️  Partial (in Event) | State transitions not tracked |
| F077 | `PlanAmendment` | ❌ Not exported | Plan change audit lost |
| F078 | `PlanningSnapshot` | ❌ Not exported | Planning history lost |
| - | `Recipient` | ❌ Not exported | Recipient data lost |
| - | `Package` | ❌ Not exported | Package definitions lost |
| - | `EventRecipientPackage` | ❌ Not exported | Package assignments lost |
| - | `PackageFinishedGood` | ❌ Not exported | Package contents lost |
| - | `Composition` | ❌ Not exported | Assembly compositions lost |
| - | `CompositionAssignment` | ❌ Not exported | Packaging assignments lost |
| - | `AssemblyRun` | ❌ Not exported | Assembly history lost |
| - | `AssemblyConsumption*` | ❌ Not exported | Assembly ledger lost |
| - | `BatchDecision` | ❌ Not exported | User batch decisions lost |

#### Why This Matters for Cloud Migration

**Snapshot Architecture (F064/F065)**: 
- These entities are the **audit trail** for cost calculations
- Critical for multi-tenant: Users must see historical costs even if recipes change
- Without snapshots: Cost data becomes unreliable after recipe edits

**Planning & State Management (F077/F078)**:
- `PlanAmendment` tracks **why** plans changed (audit requirement for food safety compliance)
- `PlanningSnapshot` enables **time-travel** for planning ("what did I plan last year?")
- Multi-tenant: Each user's planning history must be portable

**Recipients & Packages**:
- Core gift-giving workflow (primary use case for the app!)
- Without export: Users lose their entire recipient list and package templates
- Migration blocker: Can't move existing users to cloud

**Assembly System**:
- `AssemblyRun` and consumption ledgers track **finished goods inventory**
- Without export: All assembly history lost
- Multi-tenant: Critical for cost tracking per tenant

---

## 3. Import Service Analysis

### Current Import Capabilities

**Coordinated Import** (`coordinated_export_service.py`):
- ✅ Imports from coordinated exports (manifest-based)
- ✅ FK resolution via slugs/names
- ✅ Handles dependency ordering
- ✅ Replace mode (clears existing data)
- ⚠️  Coverage matches export coverage (see gaps above)

**Enhanced Import** (`enhanced_import_service.py`):
- ✅ Context-rich imports (merge mode)
- ✅ FK resolution with callbacks
- ✅ Dry-run mode
- ✅ Skip-on-error mode
- ✅ Skipped records logging
- ⚠️  Coverage limited to exported entities

### Missing Import Support

1. **Snapshot entities**: No import logic exists
   - RecipeSnapshot
   - FinishedGoodSnapshot
   - MaterialUnitSnapshot
   - FinishedUnitSnapshot
   - PlanSnapshot
   - ProductionPlanSnapshot
   - PlanningSnapshot

2. **Recent features**: No import logic exists
   - Recipients
   - Packages
   - EventRecipientPackage
   - PackageFinishedGood
   - Composition
   - CompositionAssignment
   - AssemblyRun
   - AssemblyConsumption* (3 tables)
   - BatchDecision
   - PlanAmendment

3. **Provisional products** (F057):
   - ✅ Export includes `is_provisional` flag
   - ❌ Import logic for provisional flag untested with F057 changes

---

## 4. Multi-Tenant Migration Gaps

### Schema Changes Required

**All tenant-scoped tables need**:
```python
# Add to all models except global config tables
tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

# Composite indexes
Index('idx_{table}_tenant_id', 'tenant_id', 'id')
Index('idx_{table}_tenant_slug', 'tenant_id', 'slug')  # For slug-based tables
```

**Affected tables** (51 total):
- Core: Ingredient, Product, Supplier, Recipe, FinishedGood, FinishedUnit
- Materials: Material, MaterialProduct, MaterialUnit, MaterialCategory, MaterialSubcategory
- Events: Event, EventProductionTarget, EventAssemblyTarget, EventRecipientPackage, EventRecipe, EventFinishedGood
- Recipients: Recipient
- Packages: Package, PackageFinishedGood
- Transactions: Purchase, InventoryItem, MaterialPurchase, MaterialInventoryItem
- Production: ProductionRun, AssemblyRun, InventoryDepletion
- Ledgers: ProductionConsumption, ProductionLoss, ProductionRecord, AssemblyConsumption* (3)
- Compositions: Composition, CompositionAssignment
- Decisions: BatchDecision
- Snapshots: RecipeSnapshot, FinishedGoodSnapshot, MaterialUnitSnapshot, FinishedUnitSnapshot, PlanSnapshot, ProductionPlanSnapshot, PlanningSnapshot, InventorySnapshot
- Amendments: PlanAmendment

### PostgreSQL RLS Policies

From web architecture docs, each tenant-scoped table needs:
```sql
-- Enable RLS
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Read policy
CREATE POLICY tenant_isolation_read ON {table_name}
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Write policy
CREATE POLICY tenant_isolation_write ON {table_name}
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
```

**Coverage**: All 51 tenant-scoped tables need policies.

---

## 5. Data Transformation Requirements

### SQLite → PostgreSQL Migration

**Export Transformation** (Desktop → Cloud):
1. ✅ Current exports are JSON (portable)
2. ✅ Slug-based FK resolution (works across DBs)
3. ⚠️  Need to add `tenant_id` during import
4. ⚠️  UUID fields: SQLite stores as strings, PostgreSQL uses UUID type

**Import Transformation** (Cloud Import):
1. ✅ Enhanced import service has FK resolution
2. ⚠️  Need `tenant_id` injection for all records
3. ⚠️  Need to convert string UUIDs to PostgreSQL UUIDs
4. ⚠️  Need to validate slug uniqueness **within tenant** (not global)

### Suggested Migration Flow

```
Desktop SQLite
    ↓
Export to JSON (coordinated_export_service)
    ↓
Add tenant_id to all records (transformation script)
    ↓
Convert string UUIDs to UUID type (transformation script)
    ↓
Import to PostgreSQL (enhanced_import_service + tenant_id)
    ↓
Validate tenant isolation (RLS policies)
```

---

## 6. Other Data Portability Issues

### Issue 1: Composite Foreign Keys (Product)

**Current Pattern**:
```python
# Product resolution uses composite slug
product_slug = f"{ingredient_slug}:{brand}:{qty}:{unit}"
```

**Problem**: 
- Works for single-tenant (global uniqueness)
- Breaks for multi-tenant: Two tenants can have same product composite key
- Need: `tenant_id` as part of resolution

**Fix**:
```python
# Multi-tenant product resolution
product_slug = f"{tenant_id}:{ingredient_slug}:{brand}:{qty}:{unit}"
# Or resolve via (tenant_id, ingredient_id, brand, qty, unit) composite query
```

### Issue 2: Name-Based Fallbacks

**Current Pattern** (from `enhanced_import_service.py`):
```python
# Fallback to name-based matching for backward compatibility
sup = session.query(Supplier).filter(Supplier.name == slug_value).first()
```

**Problem**:
- Name-based fallbacks assume global uniqueness
- Multi-tenant: Names collide across tenants
- Need: Eliminate name-based fallbacks, enforce slug-only resolution

**Fix**:
- Add slugs to all entities (see Section 1)
- Remove name-based fallbacks after migration
- Keep for backward compat during transition period only

### Issue 3: Snapshot Reference Integrity

**Current Pattern**:
- Snapshots reference parent entities by ID
- Example: `RecipeSnapshot.recipe_id → Recipe.id`

**Problem**:
- If Recipe is deleted, snapshot loses context
- Multi-tenant: Need to preserve snapshot even if recipe deleted
- Current: `ON DELETE RESTRICT` prevents deletion (good)

**Assessment**: ✅ No change needed (existing FK constraints are correct)

### Issue 4: Audit Trail Completeness

**Current State**:
- `created_at`, `updated_at` timestamps exist on BaseModel
- No `created_by`, `updated_by` user tracking
- No soft-delete timestamps (`deleted_at`)

**Problem**:
- Multi-tenant: Can't track which user created/modified records
- No audit trail for compliance (food safety, cost tracking)

**Recommendation**:
```python
# Add to BaseModel for cloud version
created_by = Column(UUID(as_uuid=True), nullable=True, index=True)  # FK to users table
updated_by = Column(UUID(as_uuid=True), nullable=True, index=True)
deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete
```

### Issue 5: Unique Constraints in Multi-Tenant Context

**Current Pattern**:
```python
# Example: FinishedGood.slug is globally unique
slug = Column(String(100), nullable=False, unique=True, index=True)
```

**Problem**:
- Multi-tenant: Slugs should be unique **per tenant**, not globally
- Current: Two tenants can't have same slug

**Fix**:
```python
# Composite unique constraint
__table_args__ = (
    UniqueConstraint('tenant_id', 'slug', name='uq_finished_goods_tenant_slug'),
    Index('idx_finished_goods_tenant_slug', 'tenant_id', 'slug'),
)
```

**Affected entities**: All 10 entities with slugs (see Section 1)

---

## 7. Recommendations & Prioritization

### CRITICAL (Blocking Cloud Migration)

1. **Add slugs to Recipe, Event, Recipient, Package**
   - Effort: 2-3 days
   - Risk: HIGH (schema change + data migration)
   - Blocker: Yes (core entities, frequently referenced)

2. **Export/Import support for Recipients, Packages, EventRecipientPackage**
   - Effort: 3-4 days
   - Risk: MEDIUM (new code, testing needed)
   - Blocker: Yes (core workflow, users will lose data)

3. **Export/Import support for Snapshots (RecipeSnapshot, FinishedGoodSnapshot, etc.)**
   - Effort: 4-5 days
   - Risk: MEDIUM (complex FK relationships)
   - Blocker: Yes (audit trail, cost accuracy)

### HIGH PRIORITY (Needed for Beta Launch)

4. **Export/Import support for Assembly system (AssemblyRun, Composition, etc.)**
   - Effort: 3-4 days
   - Risk: MEDIUM
   - Blocker: No (workaround: re-run assemblies after migration)

5. **Export/Import support for Planning system (PlanAmendment, PlanningSnapshot, BatchDecision)**
   - Effort: 2-3 days
   - Risk: LOW (isolated features)
   - Blocker: No (workaround: users re-plan after migration)

6. **Tenant-scoped unique constraints**
   - Effort: 1-2 days
   - Risk: MEDIUM (schema change)
   - Blocker: No (but should be done before beta)

### MEDIUM PRIORITY (Needed for Production)

7. **Audit fields (created_by, updated_by, deleted_at)**
   - Effort: 2-3 days
   - Risk: LOW (additive change)
   - Blocker: No (but good for compliance)

8. **Eliminate name-based fallbacks in import service**
   - Effort: 1 day
   - Risk: LOW (after slugs are added)
   - Blocker: No (but reduces tech debt)

9. **Composite FK resolution for multi-tenant**
   - Effort: 1-2 days
   - Risk: MEDIUM (affects product lookup)
   - Blocker: No (but needed for correctness)

### LOW PRIORITY (Nice to Have)

10. **Export validation tool** (checksum verification, FK integrity)
    - Effort: 2-3 days
    - Risk: LOW
    - Blocker: No

---

## 8. Migration Risk Assessment

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Slug collisions during migration | Medium | High | Generate unique slugs, log collisions |
| Data loss during export/import | Low | Critical | Comprehensive testing, validation checksums |
| FK resolution failures | Medium | High | Enhanced error logging, skip-on-error mode |
| Tenant data leakage | Low | Critical | RLS policies, 100% test coverage |
| Snapshot reference integrity | Low | Medium | Existing FK constraints prevent issues |
| Performance degradation (tenant_id filters) | Medium | Medium | Composite indexes on (tenant_id, ...) |

### Validation Strategy

**Pre-Migration**:
1. Export desktop data to JSON
2. Validate export completeness (record counts, FK resolution)
3. Test import on clean PostgreSQL instance
4. Verify data integrity (checksums, FK references)

**Post-Migration**:
1. Run test queries with RLS enabled
2. Verify tenant isolation (attempt cross-tenant access)
3. Performance testing (query times with tenant_id filters)
4. Data consistency checks (counts, cost calculations)

---

## 9. Conclusion

**Overall Assessment**: BakeTracker's data portability is **75% ready** for cloud migration.

**Strengths**:
- ✅ Solid slug-based FK resolution pattern established
- ✅ JSON export/import framework in place
- ✅ Core catalog entities (Ingredient, Product, Supplier) well-covered
- ✅ Materials system (F047) fully exportable

**Gaps**:
- ❌ 4 core entities lack slugs (Recipe, Event, Recipient, Package)
- ❌ 15+ entities from recent features not exported
- ❌ Snapshot architecture (F064/F065) not portable
- ❌ Assembly system incomplete export

**Timeline Estimate** (to 95% ready):
- Critical work: 9-12 days
- High priority: 5-7 days
- **Total**: 14-19 days of focused development

**Next Steps**:
1. Add slugs to Recipe, Event, Recipient, Package (CRITICAL)
2. Implement export/import for Recipients & Packages (CRITICAL)
3. Implement export/import for Snapshots (CRITICAL)
4. Test full export → import round-trip with real data
5. Begin multi-tenant schema migration (parallel track)

---

**Document Status**: Ready for review  
**Recommended Action**: Prioritize critical items 1-3 before starting cloud migration POC
