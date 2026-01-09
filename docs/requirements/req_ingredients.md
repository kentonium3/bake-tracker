# Ingredients - Requirements Document

**Component:** Ingredients (Hierarchical Taxonomy)
**Version:** 1.2
**Last Updated:** 2026-01-08
**Status:** Current
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Ingredients are a **foundational ontology entity** within the bake-tracker application. The hierarchical taxonomy of ingredients provides organizational, navigational, classification, and reporting structure throughout the application.

### 1.2 Business Purpose

The Ingredient hierarchy serves multiple business functions:

1. **Ontological Bridge:** Connects generic recipe ingredients (e.g., "flour") to specific purchasable products (e.g., "King Arthur All-Purpose Flour 25lb")
2. **Universal Classification:** Provides root classification spanning brands, package sizes, and non-material variations
3. **Navigation Aid:** Enables progressive filtering and selection across large ingredient lists
4. **Organizational Structure:** Supports how bakers naturally think about ingredients in different contexts (recipes, purchasing, inventory)

### 1.3 Taxonomy Rationale

There does not appear to be a standard industry hierarchical taxonomy for cooking ingredients. This taxonomy was developed specifically for bake-tracker's purposes, designed to reflect as universally as possible how cooks (bakers, in this iteration) conceptualize ingredients across contexts.

---

## 2. Hierarchy Structure

### 2.1 Three-Tier Model

The ingredient taxonomy uses a three-level hierarchy:

| Level  | Name            | Purpose                              | Example                                          |
| ------ | --------------- | ------------------------------------ | ------------------------------------------------ |
| **L0** | Root Category   | High-level ingredient families       | Chocolate, Flour, Sugar                          |
| **L1** | Subcategory     | Functional groupings within families | Dark Chocolate, All-Purpose, White Sugar         |
| **L2** | Leaf Ingredient | Specific ingredients used in recipes | Semi-Sweet Chocolate Chips, King Arthur AP Flour |

### 2.2 Hierarchy Rules

1. **L0 (Root Categories):**
   - Cannot have products assigned
   - Cannot be used directly in recipes
   - Managed externally (not editable in-app)

2. **L1 (Subcategories):**
   - Cannot have products assigned
   - Cannot be used directly in recipes
   - Managed externally (not editable in-app)

3. **L2 (Leaf Ingredients):**
   - **Only level that can have products**
   - **Only level usable in recipes**
   - Editable in-app (name, parentage)

### 2.3 Key Principle

**Hierarchy level is computed from position, not assigned:**
- No parent → L0
- Parent is L0 → L1
- Parent is L1 → L2

Users set parent relationships; the system computes level.

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Hierarchy Management:**
- ✅ Externally developed structure in OPML format (via Dynalist)
- ✅ Externally managed L0 and L1 categories
- ✅ External transformation of DB content when schema/structure changes require re-import

**In-App Capabilities:**
- ✅ Create new L2 ingredients with automatic unique slug generation
- ✅ Edit L2 ingredient names and L0/L1 parentage
- ✅ Set optional shelf life on ingredients (F041)
- ✅ Auto-update related Product records when ingredient L0/L1 changes
- ✅ Auto-update related Recipe records when ingredient attributes change
- ✅ Safeguards ensuring no recipe has ingredients removed or materially changed

**Cross-Document Notes:**
- ✅ Products inherit shelf_life_days from Ingredient (immutable, no override - see req_products.md)
- ✅ Purchases have shelf_life_days field (see req_inventory.md) - can override Ingredient default
- ✅ Effective shelf life priority: Purchase > Ingredient (Product is pass-through, not override point)

**UI Integration:**
- ✅ Product edit form: Cascading ingredient selectors for product-ingredient association
- ✅ Product/Inventory tabs: Cascading ingredient filters for list views
- ✅ Recipe creation: Cascading ingredient selectors for ingredient selection

### 3.2 Out of Scope

**Explicitly NOT Supported:**
- ❌ In-app creation or editing of L0/L1 categories and relationships
- ❌ Taxonomy hierarchy versioning or backward hierarchy compatibility
- ❌ Flyout-style cascading menus (MS/Apple style cursor hover menus)

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Browse ingredients hierarchically so I can find specific ingredients faster than scrolling 400+ flat items
2. See products grouped under specific ingredients so I understand which product belongs to which ingredient type
3. Create new leaf ingredients when I discover a new ingredient type
4. Edit ingredient names to fix typos or improve clarity
5. Move ingredients between subcategories when I realize a better organizational fit

**As a recipe creator, I want to:**
1. Select ingredients using hierarchical navigation (Chocolate → Dark Chocolate → Semi-Sweet Chips)
2. Be restricted to leaf ingredients only so I don't accidentally add "Chocolate" when I mean "Semi-Sweet Chips"

**As a product manager, I want to:**
1. Assign products to leaf ingredients only so the product catalog stays organized
2. Filter products by ingredient hierarchy so I can quickly find products in a category

### 4.2 Use Case: Create New Leaf Ingredient

**Actor:** Baker
**Preconditions:** L0 and L1 hierarchy exists (e.g., Chocolate → Dark Chocolate)
**Main Flow:**
1. User opens Ingredients tab
2. Clicks "Add Ingredient"
3. Enters ingredient name: "Bittersweet Chocolate Chips"
4. Selects L0: "Chocolate"
5. Selects L1: "Dark Chocolate"
6. System computes level: L2 (Leaf)
7. Optionally sets shelf life: 1 year (converted to 365 days)
8. User saves
9. System creates ingredient with unique slug: `bittersweet-chocolate-chips`

**Postconditions:**
- New L2 ingredient exists
- Available for product assignment
- Available for recipe use
- Shelf life (if set) available for product/purchase inheritance

**Alternative Flow (Import):**
1. User exports data to JSON
2. User edits JSON to add new ingredient with shelf_life_days field
3. User imports JSON
4. System creates ingredient with shelf life from import

### 4.3 Use Case: Edit Ingredient Parentage

**Actor:** Baker
**Preconditions:** Ingredient "Cocoa Powder" exists under "Chocolate → Milk Chocolate" (incorrect)
**Main Flow:**
1. User opens Ingredient edit form for "Cocoa Powder"
2. Changes L1 from "Milk Chocolate" to "Baking Chocolate"
3. System validates: no products or recipes would be orphaned
4. User saves
5. System updates `parent_ingredient_id`, recomputes level (still L2)
6. System updates all related product records (if any)

**Postconditions:**
- Ingredient moved to correct subcategory
- Products remain linked
- Recipes remain valid

### 4.4 Use Case: Shelf Life Inheritance (F041)

**Actor:** System (automatic)
**Preconditions:**
- Ingredient "All-Purpose Flour" has shelf_life_days = 180 (6 months)
- Product "King Arthur AP Flour 25lb" is linked to this ingredient
- User creates purchase of this product

**Main Flow (Ingredient Default):**
1. User creates purchase without specifying shelf life override
2. System checks Purchase.shelf_life_days: NULL (not overridden)
3. System retrieves Ingredient.shelf_life_days via Product: 180 days
4. System uses 180 days as effective shelf life
5. System calculates expiration_date: purchase_date + 180 days
6. Purchase created with computed expiration

**Alternative Flow (Purchase Override):**
1. User creates purchase and manually sets shelf life: 60 days (opened package)
2. System uses Purchase.shelf_life_days (60) instead of Ingredient default (180)
3. Purchase expires 60 days after purchase_date

**Postconditions:**
- Effective shelf life determined by: Purchase (if set) OR Ingredient (default)
- Product acts as pass-through, inheriting from Ingredient immutably
- Expiration date calculated for inventory tracking
- Freshness indicators computed from expiration date

**Notes:**
- Product does not have its own shelf_life_days field
- Product always reflects its ingredient's shelf life
- Only Purchase can override the ingredient default
- Priority: Purchase > Ingredient (Product is transparent)

---

## 5. Functional Requirements

### 5.1 Data Management

**REQ-ING-001:** System shall store ingredients in a self-referential hierarchy using `parent_ingredient_id` foreign key
**REQ-ING-002:** System shall compute `hierarchy_level` (0/1/2) based on parent position
**REQ-ING-003:** System shall generate unique slugs for all ingredients using `display_name`
**REQ-ING-004:** System shall prevent cycles in hierarchy (ingredient cannot be its own ancestor)

### 5.2 Ingredient Creation

**REQ-ING-005:** System shall allow creation of L2 ingredients via UI
**REQ-ING-006:** System shall require L0 and L1 parent selection for L2 creation
**REQ-ING-007:** System shall auto-generate slug from display_name on creation
**REQ-ING-008:** System shall validate slug uniqueness before saving

### 5.3 Ingredient Editing

**REQ-ING-009:** System shall allow editing of L2 ingredient names
**REQ-ING-010:** System shall allow changing L0/L1 parentage of L2 ingredients
**REQ-ING-011:** System shall prevent hierarchy changes that would orphan products
**REQ-ING-012:** System shall prevent hierarchy changes that would orphan recipes
**REQ-ING-013:** System shall update related Product records when ingredient L0/L1 changes
**REQ-ING-014:** System shall update related Recipe records when ingredient attributes change

### 5.4 Product Assignment

**REQ-ING-015:** System shall allow product assignment only to L2 (leaf) ingredients
**REQ-ING-016:** System shall prevent product assignment to L0 or L1 ingredients
**REQ-ING-017:** Product edit form shall use cascading selectors (L0 → L1 → L2)

### 5.5 Recipe Integration

**REQ-ING-018:** System shall allow recipe ingredient selection only for L2 ingredients
**REQ-ING-019:** System shall prevent recipe use of L0 or L1 ingredients
**REQ-ING-020:** Recipe creation form shall use cascading selectors (L0 → L1 → L2)

### 5.6 List Filtering

**REQ-ING-021:** Product tab shall support filtering by ingredient hierarchy (L0 → L1 → L2)
**REQ-ING-022:** Inventory tab shall support filtering by ingredient hierarchy
**REQ-ING-023:** Filters shall cascade (L1 options filtered by selected L0, L2 by selected L1)

### 5.7 Shelf Life Management (F041)

**REQ-ING-024:** System shall support optional shelf life field on ingredients (nullable)
**REQ-ING-025:** Shelf life shall be stored in database as integer days
**REQ-ING-026:** System shall accept shelf life input in units: days, weeks, months, years
**REQ-ING-027:** System shall convert all shelf life inputs to days for storage:
- Days: value × 1
- Weeks: value × 7
- Months: value × 30
- Years: value × 365
**REQ-ING-028:** System shall allow shelf life to be set via:
- Manual input in ingredient edit form
- Import file (JSON format)
- Leave empty/null (no default shelf life)
**REQ-ING-029:** Products shall inherit shelf_life_days from ingredient (immutable, no override at product level)
**REQ-ING-030:** Purchases shall have optional shelf_life_days field (nullable)
**REQ-ING-031:** System shall determine effective shelf life using priority: Purchase > Ingredient (Product is pass-through)
**REQ-ING-032:** System shall display shelf life in human-readable format:
- < 90 days: show in days
- 90-364 days: show in months (approximate)
- ≥ 365 days: show in years (approximate)

---

## 6. Non-Functional Requirements

### 6.1 Performance

**REQ-ING-NFR-001:** Ingredient hierarchy queries shall complete in <100ms for datasets up to 1000 ingredients
**REQ-ING-NFR-002:** Cascading dropdown population shall feel instant (<50ms perceived delay)

### 6.2 Usability

**REQ-ING-NFR-003:** Ingredient selection shall require max 3 clicks (L0 → L1 → L2)
**REQ-ING-NFR-004:** Hierarchy navigation shall feel intuitive to non-technical bakers
**REQ-ING-NFR-005:** Error messages shall clearly explain why actions are blocked (e.g., "Cannot delete: 3 products use this ingredient")

### 6.3 Data Integrity

**REQ-ING-NFR-006:** No orphaned products (all products must have valid L2 ingredient)
**REQ-ING-NFR-007:** No orphaned recipes (all recipe ingredients must have valid L2 ingredient)
**REQ-ING-NFR-008:** Referential integrity enforced at database level (foreign key constraints)

---

## 7. Development & Maintenance Workflow

### 7.1 Hierarchy Modification Process

**When L0/L1 structure needs changes:**

```
1. EXPORT
   └─ Export all data in JSON format
   └─ Extract Ingredient hierarchy (direct export preferred)

2. TRANSFORM (External)
   └─ Convert hierarchy to OPML format
   └─ Upload OPML to Dynalist
   └─ Edit structure in Dynalist
   └─ Export edited OPML from Dynalist

3. CONVERT & VALIDATE
   └─ Convert hierarchy OPML back to JSON
   └─ Transform full data JSON to adhere to new hierarchy
   └─ Validate referential integrity

4. IMPORT
   └─ Import full data JSON file
   └─ Verify no orphaned records
```

### 7.2 Tools & Technologies

**External Tools:**
- **Dynalist:** OPML editing environment for hierarchy structure
- **OPML Converters:** JSON ↔ OPML transformation scripts
- **AI Assistants:** Claude/Gemini for data transformation scripts

**In-App Tools:**
- Export/Import UI (File → Export All Data)
- Ingredient edit forms (restricted to L2 only)
- Cascading selectors throughout UI

---

## 8. Data Model Summary

### 8.1 Ingredient Table Structure

```
Ingredient
├─ id (PK)
├─ uuid (unique)
├─ slug (unique)
├─ display_name
├─ parent_ingredient_id (FK → Ingredient, nullable)
├─ hierarchy_level (0/1/2, computed)
├─ recipe_unit
├─ shelf_life_days (integer, nullable) [F041]
├─ density fields (4-field model)
└─ timestamps
```

**Shelf Life Inheritance Chain (F041):**
```
Ingredient.shelf_life_days (nullable, editable at ingredient level)
  ↓ inherited by (read-only, no override)
Product (inherits from ingredient, immutable pass-through)
  ↓ used as default for
Purchase.shelf_life_days (nullable, can override ingredient default)
  ↓ used to compute
InventoryItem.expiration_date (purchase_date + effective_shelf_life)

Effective shelf life = COALESCE(Purchase.shelf_life_days, Ingredient.shelf_life_days)
```

**Design Rationale:**
- Ingredients define shelf life for the ingredient type (e.g., "All-Purpose Flour" = 180 days)
- Products inherit this value immutably - they don't have their own shelf_life_days field
- Products translate the ingredient shelf life to inventory when purchased
- Purchases can override for specific circumstances (e.g., opened package = 60 days, bulk purchase with different date)
- Priority: Purchase > Ingredient (Product is just a pass-through)

### 8.2 Key Relationships

```
Ingredient (L0)
  └─ children (L1) via parent_ingredient_id
       └─ children (L2) via parent_ingredient_id
            ├─ products (many)
            └─ recipe_ingredients (many)
```

---

## 9. UI Requirements

### 9.1 Ingredients Tab

**Display:**
- Default view: L2 ingredients only
- Columns: Ingredient Name | Subcategory (L1) | Root (L0) | Products | Actions
- Filter: Dropdown to show L0, L1, or All levels

**Actions:**
- Add Ingredient (creates L2 only)
- Edit Ingredient (edits name, parentage)
- View Products (navigates to filtered Product tab)

### 9.2 Ingredient Edit Form

**Layout:**
```
┌─ Edit Ingredient ──────────────────────────────────┐
│ Name: [_______________]                            │
│                                                    │
│ Parent:                                            │
│   L0: [Chocolate ▼]                                │
│   L1: [Dark Chocolate ▼]                           │
│                                                    │
│ Level: L2 (Leaf) [computed]                        │
│ Can have products: Yes ✓                           │
│                                                    │
│ Shelf Life (Optional):                             │
│   [ ] None (no default shelf life)                 │
│   [•] Set value: [___] [Days ▼]                    │
│       (Days, Weeks, Months, Years)                 │
│                                                    │
│ Display: "6 months" or "1 year" or "None"          │
│                                                    │
│ [Cancel] [Save]                                    │
└────────────────────────────────────────────────────┘
```

**Behavior:**
- L0 dropdown: All L0 ingredients
- L1 dropdown: Children of selected L0
- Level display: Computed, read-only
- Shelf Life: Optional field
  - Radio button: "None" (default, saves as NULL)
  - Radio button: "Set value" with numeric input + unit dropdown
  - Unit dropdown: Days, Weeks, Months, Years
  - System converts to days for storage
  - Display shows human-readable format
- Save: Validates no orphaned products/recipes

**Shelf Life Input Examples:**
- User enters: 6, Months → Stored as: 180 days → Displayed as: "6 months"
- User enters: 1, Years → Stored as: 365 days → Displayed as: "1 year"
- User enters: 45, Days → Stored as: 45 days → Displayed as: "45 days"
- User selects: None → Stored as: NULL → Displayed as: "None"

### 9.3 Level-Aware Edit Form Behavior (TD-007)

**Status:** Requirements stub - to be detailed
**Related Tech Debt:** TD-007 (Ingredient Edit Form Missing Hierarchy Level Safeguards)

The ingredient edit form should dynamically adapt based on the hierarchy level of the item being edited. Currently, the form presents the same options regardless of level, which creates counter-intuitive UX.

**L0 (Root Category) Editing:**
- [ ] Hide/disable parent selection (L0 items have no parent by definition)
- [ ] Show only L0-appropriate fields: `display_name`
- [ ] Show read-only child count: "X subcategories"
- [ ] Prevent level changes (L0 → L1/L2)

**L1 (Subcategory) Editing:**
- [ ] Show L0 parent selection only (can re-parent to different L0)
- [ ] Hide L1 selection (item IS an L1)
- [ ] Show only L1-appropriate fields: `display_name`, `parent_ingredient_id`
- [ ] Show read-only child count: "X leaf ingredients"
- [ ] Prevent level changes (L1 → L0/L2)

**L2 (Leaf Ingredient) Editing:**
- [ ] Show L0 selection (grandparent)
- [ ] Show L1 selection filtered by L0 (direct parent)
- [ ] Show all L2-appropriate fields: `display_name`, `parent_ingredient_id`, `shelf_life_days`, `density`, `is_packaging`
- [ ] No children possible, so no child count
- [ ] Prevent level changes (L2 → L0/L1)

**Common Behavior:**
- [ ] Level indicator shown as read-only (computed from position)
- [ ] Validation messages explain why certain options are unavailable
- [ ] Form title reflects level: "Edit Category", "Edit Subcategory", "Edit Ingredient"

**Implementation Notes:**
- Form should query `hierarchy_level` on load and conditionally render fields
- Service layer already validates operations; UI should prevent invalid attempts
- Consider separate form components per level vs. single adaptive form

**Effort Estimate:** 4-6 hours (see TD-007)

---

### 9.4 Cascading Selector Component (Reusable)

**Used In:**
- Product edit form (ingredient selection)
- Recipe creation (ingredient selection)
- Product tab filter
- Inventory tab filter

**Behavior:**
- L0 selection → Updates L1 options
- L1 selection → Updates L2 options
- L2 selection → Final selection confirmed
- Clear button → Resets all levels

---

## 10. Validation Rules

### 10.1 Creation Validation

| Rule ID     | Validation               | Error Message                                 |
| ----------- | ------------------------ | --------------------------------------------- |
| VAL-ING-001 | Ingredient name required | "Ingredient name cannot be empty"             |
| VAL-ING-002 | Slug must be unique      | "An ingredient with this name already exists" |
| VAL-ING-003 | L2 must have L1 parent   | "Please select both L0 and L1 categories"     |
| VAL-ING-004 | L1 must have L0 parent   | "Please select L0 category"                   |

### 10.2 Edit Validation

| Rule ID     | Validation                                   | Error Message                                                   |
| ----------- | -------------------------------------------- | --------------------------------------------------------------- |
| VAL-ING-005 | Cannot change parent if has children         | "Cannot change parent: this ingredient has X children"          |
| VAL-ING-006 | Cannot change to non-leaf if has products    | "Cannot change hierarchy: this ingredient has X products"       |
| VAL-ING-007 | Cannot change to non-leaf if used in recipes | "Cannot change hierarchy: this ingredient is used in X recipes" |
| VAL-ING-008 | Cannot create cycle                          | "Invalid parent: would create circular reference"               |

### 10.3 Deletion Validation

| Rule ID     | Validation                       | Error Message                                                |
| ----------- | -------------------------------- | ------------------------------------------------------------ |
| VAL-ING-009 | Cannot delete if has products    | "Cannot delete: X products use this ingredient"              |
| VAL-ING-010 | Cannot delete if used in recipes | "Cannot delete: X recipes use this ingredient"               |
| VAL-ING-011 | Cannot delete if has children    | "Cannot delete: X ingredients are children of this category" |

### 10.4 Shelf Life Validation (F041)

| Rule ID     | Validation                                   | Error Message                                         |
| ----------- | -------------------------------------------- | ----------------------------------------------------- |
| VAL-ING-012 | Shelf life value must be positive if set     | "Shelf life must be greater than zero"                |
| VAL-ING-013 | Shelf life must be integer                   | "Shelf life must be a whole number"                   |
| VAL-ING-014 | Shelf life unit must be valid                | "Invalid unit: must be Days, Weeks, Months, or Years" |
| VAL-ING-015 | Converted days value must be > 0 and < 36500 | "Shelf life must be between 1 day and 100 years"      |

---

## 11. Acceptance Criteria

### 11.1 Phase 2 (Current) Acceptance

**Must Have:**
- [x] Ingredient hierarchy stored in database (L0/L1/L2)
- [x] Cascading selectors work in Product edit form
- [x] Cascading filters work in Product/Inventory tabs
- [x] Can create new L2 ingredients in-app
- [x] Can edit L2 ingredient name and parentage
- [ ] Shelf life field on ingredients (nullable, stored as days, input as days/weeks/months/years)
- [ ] Shelf life inheritance: Purchase → Product → Ingredient
- [ ] Shelf life UI with None/Set Value radio buttons and unit dropdown
- [ ] Validation prevents orphaning products/recipes
- [ ] Ingredients tab shows L2 by default with L0/L1 columns
- [ ] Edit form uses radio + cascading dropdowns (not level dropdown)

**Should Have:**
- [ ] Clear error messages for validation failures
- [ ] Auto-update related records on hierarchy changes
- [ ] Slug auto-generation on ingredient creation
- [ ] Human-readable shelf life display (days → months → years)
- [ ] Shelf life import via JSON

**Nice to Have:**
- [ ] Inline subcategory creation in edit form
- [ ] Batch operations (move multiple ingredients)
- [ ] Hierarchy visualization (tree view)
- [ ] Bulk shelf life update for ingredient categories

### 11.2 Future Phase Acceptance

**Phase 3 (Web Migration):**
- [ ] Multi-user hierarchy editing conflicts resolved
- [ ] Hierarchy versioning for backward compatibility
- [ ] API endpoints for hierarchy queries

**Phase 4 (Platform Expansion):**
- [ ] Mobile-optimized cascading selectors
- [ ] Offline hierarchy caching
- [ ] Hierarchy import/export via API

---

## 12. Dependencies

### 12.1 Upstream Dependencies (Blocks This)

- ✅ Database schema with `parent_ingredient_id` and `hierarchy_level`
- ✅ Ingredient hierarchy service layer
- ✅ Import/export system supporting hierarchical data

### 12.2 Downstream Dependencies (This Blocks)

- Product management (requires ingredient hierarchy for assignment)
- Recipe creation (requires ingredient hierarchy for selection)
- Inventory management (requires ingredient hierarchy for filtering)
- Shopping list generation (requires ingredient hierarchy for grouping)

---

## 13. Testing Requirements

### 13.1 Test Coverage

**Unit Tests:**
- Hierarchy level computation logic
- Slug generation uniqueness
- Cycle detection algorithm
- Validation rule enforcement

**Integration Tests:**
- Cascading selector behavior
- Product auto-update on ingredient change
- Recipe validation when ingredient changes
- Import/export round-trip with hierarchy

**User Acceptance Tests:**
- Create L2 ingredient workflow
- Edit ingredient parentage workflow
- Filter products by ingredient hierarchy
- Select ingredients in recipe creation

### 13.2 Test Data

**Minimum Test Hierarchy:**
```
Chocolate (L0)
├─ Dark Chocolate (L1)
│   ├─ Semi-Sweet Chocolate Chips (L2)
│   └─ Bittersweet Chocolate Chips (L2)
├─ Milk Chocolate (L1)
│   └─ Milk Chocolate Chips (L2)

Flour (L0)
├─ All-Purpose (L1)
│   └─ King Arthur AP Flour (L2)
├─ Bread Flour (L1)
│   └─ King Arthur Bread Flour (L2)
```

---

## 14. Open Questions & Future Considerations

### 14.1 Open Questions

**Q1:** Should we allow users to suggest L0/L1 changes via in-app feedback mechanism?
**A1:** Deferred to Phase 3. Phase 2 uses external Dynalist workflow.

**Q2:** How to handle ingredient merging (e.g., duplicate ingredients discovered)?
**A2:** Manual process for now. Requires export → transform → import.

**Q3:** Should hierarchy changes create audit trail?
**A3:** Not required for Phase 2. Consider for Phase 3 (multi-user).

### 14.2 Future Enhancements

**Phase 3 Candidates:**
- Hierarchy versioning (v1, v2, etc.)
- Ingredient aliases (search terms)
- Multi-language ingredient names
- Industry standard taxonomy mapping (USDA FoodData Central)

**Phase 4 Candidates:**
- AI-suggested ingredient categorization
- Auto-detect ingredient from recipe text
- Ingredient nutrition data integration
- Allergen tagging at ingredient level

---

## 15. Change Log

| Version | Date       | Author    | Changes                              |
| ------- | ---------- | --------- | ------------------------------------ |
| 1.2     | 2026-01-08 | Kent Gale | Added level-aware edit form requirements stub (TD-007) |
| 1.1     | 2026-01-05 | Kent Gale | Added shelf life requirements (F041) |
| 1.0     | 2025-12-30 | Kent Gale | Initial requirements document        |

---

## 16. Approval & Sign-off

**Document Owner:** Kent Gale
**Last Review Date:** 2025-12-30
**Next Review Date:** 2026-03-30 (quarterly)
**Status:** ✅ APPROVED

---

## 17. Related Documents

- **Design Specs:** `/docs/design/F031_ingredient_hierarchy.md` (backend architecture)
- **Design Specs:** `/docs/design/_F041_shelf_life_freshness_tracking.md` (shelf life feature)
- **Requirements:** `/docs/requirements/req_inventory.md` (inventory & expiration tracking)
- **Bug Reports:** `/docs/bugs/BUG_F032_hierarchy_conceptual_errors.md` (UI fixes needed)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)
- **Data Model:** `/docs/design/architecture.md` (database schema)

---

**END OF REQUIREMENTS DOCUMENT**
