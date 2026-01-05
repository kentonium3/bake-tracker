# Recipes - Requirements Document

**Component:** Recipes (Template & Instance Management)  
**Version:** 0.1 (DRAFT - SEEDED)  
**Last Updated:** 2025-01-04  
**Status:** Draft - Awaiting Extension  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Recipes are a **catalog entity** within the bake-tracker application that define how to transform ingredients into finished goods. The recipe system supports both template management (reusable recipes) and instance tracking (actual production batches).

### 1.2 Business Purpose

The Recipe system serves multiple business functions:

1. **Production Planning:** Defines what ingredients and quantities are needed to produce finished goods
2. **Inventory Management:** Enables ingredient depletion tracking when recipes are executed
3. **Yield Scaling:** Supports production quantity adjustments through batch multipliers
4. **Loss Tracking:** Records production losses as normal operations with automatic remake workflows
5. **Event Fulfillment:** Links recipes to events with quantity planning and production status

### 1.3 Design Rationale

**Template vs Instance Distinction:** Phase 1 implemented a flat recipe model where each recipe was essentially an instance. Real-world testing revealed the need for template recipes (reusable patterns) separate from production instances (specific batches made for events).

**Catalog Data Classification:** Recipes are catalog data (like ingredients and products), not transactional data. This allows safe catalog expansion and AI-assisted recipe generation without risking user production history.

---

## 2. Recipe Structure

### 2.1 Core Components

**Recipe Entity:**
- Recipe metadata (name, description, yield, unit)
- Ingredient list with quantities
- Production instructions
- Loss tracking configuration
- Yield scaling rules

**Recipe Ingredients:**
- Link to L2 ingredient (via foreign key)
- Quantity and unit specification
- Automatic hierarchy propagation from ingredient

**Recipe Production (Future - Instance Tracking):**
- Links template recipe to specific production event
- Tracks batch multiplier for yield scaling
- Records actual losses during production
- Manages remake workflows for event fulfillment

### 2.2 Key Relationships

```
Recipe (Template)
  ├─ recipe_ingredients (many)
  │    └─ ingredient_id → Ingredient (L2 only)
  └─ recipe_production (many) [FUTURE]
       ├─ event_id → Event
       ├─ inventory_depletion → InventoryDepletion
       └─ production_loss → ProductionLoss
```

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Recipe Management:**
- ✅ Create recipes with ingredient lists
- ✅ Edit recipe metadata and ingredient quantities
- ✅ Link recipes to L2 ingredients only (via cascading selectors)
- ✅ Yield specification with unit
- ✅ Recipe import/export for AI-assisted catalog expansion

**Ingredient Integration:**
- ✅ Automatic L0/L1 propagation from selected L2 ingredient
- ✅ Cascading ingredient selectors (L0 → L1 → L2)
- ✅ Validation preventing use of non-leaf ingredients

**Production Support (Current):**
- ✅ Basic recipe execution concept
- ✅ Loss tracking integration
- ✅ Event linkage

### 3.2 Out of Scope (Phase 2)

**Explicitly NOT Yet Supported:**
- ❌ Template vs instance distinction (Phase 2 redesign needed)
- ❌ Batch multiplier / yield scaling UI
- ❌ Remake workflow automation
- ❌ Recipe versioning
- ❌ Nutrition calculation
- ❌ Cost calculation per recipe

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Create recipe templates that I can reuse across multiple events
2. Scale recipe yields up or down using batch multipliers
3. See which ingredients I need and in what quantities
4. Track production losses as normal operations
5. Have the system automatically suggest remakes when losses occur

**As an event planner, I want to:**
1. Select recipes for an event and specify quantities needed
2. See ingredient requirements aggregated across all event recipes
3. Track which recipes have been produced and which are pending
4. Record losses during production without manual inventory adjustment

**As a recipe manager, I want to:**
1. Import recipe templates from external sources (AI-assisted)
2. Edit recipe metadata without affecting historical production
3. Organize recipes by category or product type
4. Export recipes for sharing or backup

### 4.2 Use Case: Create Recipe Template

**Actor:** Baker  
**Preconditions:** Ingredient hierarchy exists  
**Main Flow:**
1. User opens Recipes tab
2. Clicks "Add Recipe"
3. Enters recipe name: "Chocolate Chip Cookies"
4. Enters yield: 24 cookies
5. Adds ingredients:
   - Flour (AP) → L2: King Arthur AP → 2 cups
   - Sugar → L2: White Sugar → 1 cup
   - Chocolate → L2: Semi-Sweet Chips → 2 cups
6. System validates all ingredients are L2
7. User saves

**Postconditions:**
- Recipe template created
- Available for event planning
- Ingredient quantities stored with L0/L1 propagated

### 4.3 Use Case: Execute Recipe with Loss Tracking

**Actor:** Baker  
**Preconditions:** Recipe "Chocolate Chip Cookies" exists, ingredients in inventory  
**Main Flow:**
1. User produces batch for an event (batch multiplier: 2x)
2. Target yield: 48 cookies
3. During production, 6 cookies burn
4. User records loss: 6 cookies, reason: "burned"
5. System calculates actual yield: 42 cookies
6. System suggests remake for 6 cookies to meet event requirement
7. User accepts remake
8. System creates new production instance with 0.25x batch multiplier

**Postconditions:**
- Original production recorded with loss
- Remake production scheduled
- Event fulfillment quantity maintained

---

## 5. Functional Requirements

### 5.1 Recipe Management

**REQ-RCP-001:** System shall support recipe creation with name, description, yield, and unit  
**REQ-RCP-002:** System shall allow ingredient addition with quantities and units  
**REQ-RCP-003:** System shall restrict recipe ingredients to L2 ingredients only  
**REQ-RCP-004:** System shall propagate L0/L1 from selected L2 ingredient automatically  
**REQ-RCP-005:** System shall validate unique recipe names  
**REQ-RCP-006:** System shall support recipe editing (metadata and ingredients)  
**REQ-RCP-007:** System shall support recipe deletion with validation (no active productions)

### 5.2 Ingredient Selection

**REQ-RCP-008:** Recipe creation shall use cascading ingredient selectors (L0 → L1 → L2)  
**REQ-RCP-009:** System shall prevent selection of L0 or L1 ingredients in recipes  
**REQ-RCP-010:** System shall allow multiple ingredients per recipe  
**REQ-RCP-011:** System shall validate ingredient quantities are positive numbers

### 5.3 Yield Management

**REQ-RCP-012:** System shall store recipe base yield with unit  
**REQ-RCP-013:** System shall support yield units (pieces, dozen, batch, weight, volume)  
**REQ-RCP-014:** System shall calculate scaled ingredient quantities based on batch multiplier  
**REQ-RCP-015:** Batch multiplier shall support fractional values (e.g., 0.5x, 1.5x, 2x)

### 5.4 Production Integration

**REQ-RCP-016:** System shall link recipe instances to events  
**REQ-RCP-017:** System shall track production status (planned, in-progress, completed)  
**REQ-RCP-018:** System shall record production losses with reasons  
**REQ-RCP-019:** System shall suggest remakes when losses reduce yield below event requirement  
**REQ-RCP-020:** System shall deplete inventory based on scaled ingredient quantities

### 5.5 Import/Export

**REQ-RCP-021:** System shall export recipes in JSON format (normalized and denormalized)  
**REQ-RCP-022:** System shall import recipes with automatic ingredient resolution  
**REQ-RCP-023:** System shall handle missing ingredients during import with user prompt  
**REQ-RCP-024:** System shall validate recipe integrity after import (all ingredients exist)

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-RCP-NFR-001:** Recipe creation shall require max 5 clicks for single-ingredient recipe  
**REQ-RCP-NFR-002:** Ingredient quantity entry shall support common units (cup, tbsp, oz, lb, g)  
**REQ-RCP-NFR-003:** Yield scaling calculations shall be transparent to user  
**REQ-RCP-NFR-004:** Error messages shall clearly explain validation failures

### 6.2 Data Integrity

**REQ-RCP-NFR-005:** No orphaned recipe ingredients (all must link to valid L2 ingredient)  
**REQ-RCP-NFR-006:** Recipe deletion shall prevent orphaning of production instances  
**REQ-RCP-NFR-007:** Ingredient hierarchy changes shall not break existing recipes

### 6.3 Performance

**REQ-RCP-NFR-008:** Recipe list loading shall complete in <100ms for 100+ recipes  
**REQ-RCP-NFR-009:** Yield scaling calculations shall feel instant (<50ms)

---

## 7. Data Model Summary

### 7.1 Recipe Table Structure

```
Recipe
├─ id (PK)
├─ uuid (unique)
├─ name (unique)
├─ description (optional)
├─ yield_quantity (decimal)
├─ yield_unit (enum or text)
├─ instructions (text, optional)
└─ timestamps
```

### 7.2 Recipe Ingredient Structure

```
RecipeIngredient
├─ id (PK)
├─ recipe_id (FK → Recipe)
├─ ingredient_id (FK → Ingredient, L2 only)
├─ ingredient_l0_id (FK → Ingredient, propagated)
├─ ingredient_l1_id (FK → Ingredient, propagated)
├─ quantity (decimal)
├─ unit (text)
└─ sort_order (int, optional)
```

### 7.3 Production Instance (Future)

```
RecipeProduction
├─ id (PK)
├─ recipe_id (FK → Recipe)
├─ event_id (FK → Event)
├─ batch_multiplier (decimal, default 1.0)
├─ target_yield (computed)
├─ actual_yield (recorded after production)
├─ status (planned, in_progress, completed)
├─ production_date
└─ timestamps
```

---

## 8. UI Requirements

### 8.1 Recipes Tab

**Display:**
- List view: Recipe Name | Yield | Ingredients Count | Actions
- Filter: Search by name, filter by yield unit
- Sort: Alphabetical, recently updated

**Actions:**
- Add Recipe
- Edit Recipe
- View Recipe Details
- Delete Recipe (with validation)

### 8.2 Recipe Edit Form

**Layout:**
```
┌─ Edit Recipe ──────────────────────┐
│ Name: [_______________]            │
│ Description: [_______________]     │
│                                    │
│ Yield: [24] [cookies ▼]            │
│                                    │
│ Ingredients:                       │
│ ┌────────────────────────────────┐ │
│ │ L0 [Flour ▼] → L1 [AP ▼] →     │ │
│ │ L2 [King Arthur AP ▼]          │ │
│ │ Qty: [2] Unit: [cups ▼]        │ │
│ │                        [Remove]│ │
│ └────────────────────────────────┘ │
│ [+ Add Ingredient]                 │
│                                    │
│ [Cancel] [Save]                    │
└────────────────────────────────────┘
```

**Behavior:**
- Cascading ingredient selectors per ingredient row
- Dynamic ingredient row add/remove
- Yield unit dropdown or free text
- Validation on save (all ingredients L2, quantities positive)

---

## 9. Validation Rules

### 9.1 Creation Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-001 | Recipe name required | "Recipe name cannot be empty" |
| VAL-RCP-002 | Recipe name must be unique | "A recipe with this name already exists" |
| VAL-RCP-003 | Yield quantity must be positive | "Yield must be greater than zero" |
| VAL-RCP-004 | At least one ingredient required | "Recipe must have at least one ingredient" |
| VAL-RCP-005 | All ingredients must be L2 | "Only leaf ingredients can be used in recipes" |
| VAL-RCP-006 | Ingredient quantities must be positive | "Ingredient quantity must be greater than zero" |

### 9.2 Edit Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-007 | Cannot remove ingredient if used in active production | "Cannot remove: ingredient used in active production" |
| VAL-RCP-008 | Cannot change ingredient if would orphan production | "Cannot change: would affect active production" |

### 9.3 Deletion Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-009 | Cannot delete if has active productions | "Cannot delete: recipe has X active productions" |
| VAL-RCP-010 | Cannot delete if linked to future events | "Cannot delete: recipe is planned for X future events" |

---

## 10. Acceptance Criteria

### 10.1 Phase 2 (Current) Acceptance

**Must Have:**
- [ ] Recipe creation with ingredient selection via cascading selectors
- [ ] Recipe editing (metadata and ingredients)
- [ ] Validation preventing non-L2 ingredient use
- [ ] Recipe list view with search and filter
- [ ] Import/export supporting recipe catalog expansion

**Should Have:**
- [ ] Template vs instance distinction (redesign needed)
- [ ] Batch multiplier UI for yield scaling
- [ ] Loss tracking integration
- [ ] Remake workflow automation

**Nice to Have:**
- [ ] Recipe cloning (duplicate with new name)
- [ ] Recipe categories/tags
- [ ] Recipe instructions text area
- [ ] Recipe cost calculation

---

## 11. Dependencies

### 11.1 Upstream Dependencies (Blocks This)

- ✅ Ingredient hierarchy (recipes require L2 ingredients)
- ✅ Import/export system
- ⏳ Event system (for production instance linking)
- ⏳ Loss tracking system (for production workflows)

### 11.2 Downstream Dependencies (This Blocks)

- Production planning (requires recipes for ingredient aggregation)
- Shopping list generation (requires recipes for purchase planning)
- Finished goods inventory (requires recipes for production tracking)
- Event management (requires recipes for fulfillment planning)

---

## 12. Testing Requirements

### 12.1 Test Coverage

**Unit Tests:**
- Recipe validation logic
- Yield scaling calculations
- Ingredient quantity computations
- L0/L1 propagation from L2 ingredient

**Integration Tests:**
- Recipe creation workflow
- Cascading selector behavior
- Import/export round-trip
- Production instance creation (future)

**User Acceptance Tests:**
- Create recipe with multiple ingredients
- Edit recipe and update quantities
- Scale recipe yield and verify ingredient quantities
- Track production loss and verify remake suggestion

---

## 13. Open Questions & Future Considerations

### 13.1 Open Questions

**Q1:** Should recipe templates support versioning (v1, v2)?  
**A1:** Deferred to Phase 3. Phase 2 uses single-version templates.

**Q2:** How to handle recipe template changes when active productions exist?  
**A2:** Phase 2 redesign required. Template changes should not affect production instances.

**Q3:** Should recipes support sub-recipes (nested recipes)?  
**A3:** Not required for Phase 2. Consider for Phase 3.

**Q4:** Should recipe units be standardized or free text?  
**A4:** Phase 2 uses free text. UN/CEFACT standardization deferred.

### 13.2 Future Enhancements

**Phase 3 Candidates:**
- Recipe versioning
- Recipe categories/tags
- Recipe cost calculation (ingredient cost aggregation)
- Recipe nutrition calculation (ingredient nutrition aggregation)
- Recipe scaling with unit conversion (e.g., scale from cups to oz)

**Phase 4 Candidates:**
- AI-suggested recipe creation
- Recipe import from external sources (URLs, PDFs)
- Recipe sharing across users
- Recipe rating/feedback system

---

## 14. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-04 | Kent Gale | Initial seeded draft from documented knowledge |

---

## 15. Approval & Sign-off

**Document Owner:** Kent Gale  
**Last Review Date:** 2025-01-04  
**Next Review Date:** TBD (after extension and refinement)  
**Status:** 📝 DRAFT - SEEDED

---

## 16. Related Documents

- **Design Specs:** TBD (Recipe redesign spec needed for Phase 2)
- **Bug Reports:** TBD (Recipe-related bugs to be cataloged)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)
- **Data Model:** `/docs/design/architecture.md` (database schema)
- **Requirements:** `/docs/requirements/req_ingredients.md` (ingredient dependency)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT - SEEDED)**
