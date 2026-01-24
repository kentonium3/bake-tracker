# Instantiation Pattern Research Brief

**Research Type:** Architecture Analysis  
**Scope:** Cross-Service Pattern Investigation  
**Priority:** BLOCKING - Required before FinishedGoods implementation  
**Date:** 2025-01-23  
**Requestor:** Kent Gale

---

## Primary Research Question

**How does bake-tracker currently implement the definition-to-instantiation pattern across catalog services (Recipe, Ingredient, Material, FinishedUnit, FinishedGood), and what universal architecture should be adopted for planning snapshots?**

---

## Context & Motivation

### The Problem

The application follows a three-layer architecture for catalog entities:

1. **Catalog Layer (Definitions):** Mutable templates (Recipe, Ingredient, FinishedGood definitions)
2. **Planning Layer (Snapshots):** Immutable copies created when events are planned
3. **Production/Assembly Layer (Instances):** Records of actual work with cost snapshots

**Current State Unknown:**
- We don't know which services implement snapshots and how
- We don't know if snapshot patterns are consistent across services
- We don't know who owns snapshot creation (catalog service vs planning service)
- We don't know if the existing pattern is the right architecture

**Why This Matters:**
- FinishedGoods implementation is blocked until we know the pattern
- Recipe/Ingredient/Material services may need refactoring for consistency
- Planning and Assembly services depend on reliable snapshot architecture
- Wrong pattern choice will require expensive refactoring later

### Constitutional Principles at Stake

- **Data Integrity (Constitution II):** Snapshots must be truly immutable
- **Layered Architecture (Constitution V):** Clear service boundaries required
- **Definition/Instantiation Separation:** Core to cost accuracy and historical records
- **Pragmatic Aspiration (Constitution VII):** Pattern must support web migration

---

## Research Areas

### 1. Current Implementation Discovery

**Inventory existing snapshot support:**
- Which models have snapshot variants? (RecipeSnapshot, IngredientSnapshot, etc.)
- What fields do snapshot models contain? (full copy, references, deltas)
- What services manage snapshots? (dedicated service, catalog service methods)
- Where are snapshots stored? (tables, JSON columns, embedded in Event/Planning tables)

**Understand snapshot lifecycle:**
- When are snapshots created? (event creation, planning finalization, production start)
- Who triggers creation? (Event service, Planning service, catalog services, user action)
- How are snapshots referenced? (foreign keys from Assembly/Production records)
- Can snapshots be deleted? (cascade rules, orphan prevention)

**Trace snapshot usage:**
- Which services consume snapshots? (Assembly, Production, Cost Reporting)
- How do they access snapshot data? (direct queries, service methods)
- Are live definitions ever accessed after planning? (architecture violation check)

### 2. Pattern Consistency Analysis

**Cross-service comparison:**
- Is Recipe snapshot pattern identical to Ingredient snapshot pattern?
- Do all snapshot models use same base structure/mixin?
- Are there competing or conflicting patterns?

**Completeness assessment:**
- Which services have full snapshot support?
- Which have partial implementations?
- Which have none?

**Quality evaluation:**
- Are existing snapshots truly immutable?
- Do catalog changes properly isolate from snapshots?
- Are there bugs or gaps in current implementations?

### 3. Service Boundary Determination

**Ownership options:**

**Option A - Catalog Service Ownership:**
- Recipe service provides `create_snapshot(recipe_id, event_id)` primitive
- Each catalog service manages its own snapshots
- Planning service orchestrates by calling each catalog service

**Option B - Planning Service Ownership:**
- Planning service contains all snapshot creation logic
- Catalog services just provide data access
- Planning service directly creates snapshot records

**Option C - Dedicated Snapshot Service:**
- Separate SnapshotService handles all snapshot creation
- Generic pattern works across all entity types
- Catalog services provide read-only access

**Recommendation criteria:**
- Which option best respects service boundaries?
- Which is most maintainable?
- Which supports future requirements (web migration, API exposure)?

### 4. Data Model Architecture

**Snapshot storage patterns:**

**Pattern A - Mirrored Tables:**
```
Recipe (catalog)
RecipeSnapshot (full copy of recipe at planning time)
  - Includes all fields from Recipe
  - Includes snapshot metadata (event_id, created_at)
  - Includes embedded/linked component snapshots
```

**Pattern B - JSON Blob Storage:**
```
Snapshot (universal table)
  - entity_type (recipe, ingredient, etc.)
  - entity_id (original definition ID)
  - snapshot_data (JSON blob of entity state)
  - event_id, created_at
```

**Pattern C - Hybrid:**
```
RecipeSnapshot (structure)
  - recipe_id (reference to original)
  - snapshot_data (JSON for flexibility)
  - event_id, created_at
```

**Recommendation criteria:**
- Query performance for cost calculations
- Schema evolution flexibility
- Referential integrity enforcement
- Storage efficiency

### 5. Nested Relationship Handling

**Complexity:**
- Recipe can contain RecipeComponents (nested recipes)
- FinishedGood can contain nested FinishedGoods
- Snapshots must capture full tree, not just top level

**Questions:**
- Are nested snapshots created recursively?
- Are nested snapshots stored inline or separately linked?
- How deep can nesting go before performance degrades?
- Are circular references prevented at snapshot time?

### 6. Migration Strategy

**Gap filling:**
- Which services need new snapshot implementations?
- Which need refactoring to match universal pattern?
- What's the implementation order? (dependencies, risk)

**Backward compatibility:**
- Do existing snapshots need migration?
- Can old and new patterns coexist during transition?
- What's the rollback plan if pattern fails?

---

## Expected Deliverable

### Research Findings Document

**Section 1: Current State Assessment**
- Inventory of all snapshot-related models and services
- Code examples showing existing patterns (with file paths)
- Table mapping: which catalog services have snapshot support
- Inconsistencies and gaps identified

**Section 2: Architecture Recommendation**
- Recommended universal pattern with clear rationale
- Service responsibility assignment (who creates snapshots)
- Data model specification (tables, fields, relationships)
- Primitive method signatures for each service type

**Section 3: Implementation Guidance**
- Snapshot creation flow diagram (sequence diagram or pseudocode)
- Example implementations for each catalog service type
- Nested relationship handling pattern
- Error handling and validation requirements

**Section 4: Migration Plan**
- Services requiring new implementations (priority order)
- Services requiring refactoring (scope and risk)
- Backward compatibility strategy
- Testing strategy for snapshot correctness

**Section 5: FinishedGoods Integration**
- How FinishedGoods should implement snapshots (specific guidance)
- What primitives FinishedGoods service must provide
- Integration points with Planning/Event/Assembly services
- Example: snapshot creation for FinishedGood with nested components

---

## Success Criteria

Research is complete when we can answer:

1. ✅ What snapshot pattern exists today? (models, services, storage)
2. ✅ Is the existing pattern consistent and correct?
3. ✅ What is the recommended universal pattern?
4. ✅ Which service owns snapshot creation?
5. ✅ What primitives should catalog services provide?
6. ✅ How should FinishedGoods implement snapshots?
7. ✅ What is the migration path from current to recommended state?

---

## Constraints

- **Research only:** Do not implement changes, only document findings
- **Code-based:** Examine actual implementation, not just documentation
- **Comprehensive:** Cover Recipe, Ingredient, Material, FinishedUnit, FinishedGood
- **Practical:** Recommendations must be implementable in desktop single-user phase
- **Forward-looking:** Note implications for web/multi-user phase

---

## Out of Scope

- Implementing the recommended pattern
- Fixing bugs in existing snapshot code
- Performance optimization
- UI design for snapshot management
- Detailed cost calculation algorithms
- Event/Planning service redesign (focus on snapshot interaction only)

---

## Background Documents

- **Requirements:** `/docs/requirements/req_finished_goods.md` (v2.1, Section 5.6 - Planning Snapshot Creation)
- **Constitution:** `/.kittify/memory/constitution.md` (Principles II, V, VII)
- **Models:** `/src/models/recipe_snapshot.py`, `/src/models/recipe.py`, `/src/models/finished_unit.py`
- **Services:** `/src/services/recipe_snapshot_service.py`

---

## Output Format Preference

- Markdown document with code examples
- Clear section headings for easy navigation
- Diagrams (sequence, entity-relationship) if helpful
- Table summaries for cross-service comparisons
- Specific file paths for all code references

---

**END OF RESEARCH BRIEF**
