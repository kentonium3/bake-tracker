# Products - Requirements Document

**Component:** Products (Purchasable Items & Catalog Management)  
**Version:** 0.1 (DRAFT - SEEDED)  
**Last Updated:** 2025-01-04  
**Status:** Draft - Awaiting Extension  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Products are **catalog entities** within the bake-tracker application that represent specific purchasable items linked to ingredients. Products serve as the bridge between abstract ingredients (used in recipes) and concrete items that can be purchased and tracked in inventory.

### 1.2 Business Purpose

The Product system serves multiple business functions:

1. **Ontological Bridge:** Connects abstract ingredients to specific purchasable products (e.g., "All-Purpose Flour" → "King Arthur All-Purpose Flour 25lb")
2. **Purchase Planning:** Defines what to buy when recipes require ingredients
3. **Inventory Tracking:** Links purchased items to inventory management
4. **Unit Conversion:** Manages relationship between purchase units and recipe units
5. **Density Tracking:** Enables volume-to-weight conversions for accurate inventory

### 1.3 Design Rationale

**Catalog Data Classification:** Products are catalog data (like ingredients and recipes), not transactional data. This allows safe catalog expansion without risking user purchase or inventory history.

**One-to-Many Relationship:** Each product links to exactly one L2 ingredient, but an ingredient can have multiple products (different brands, sizes, package types).

---

## 2. Product Structure

### 2.1 Core Components

**Product Entity:**
- Product metadata (brand, name, purchase unit, package size)
- Link to single L2 ingredient (via foreign key)
- Automatic L0/L1 propagation from ingredient
- Default vendor reference (optional)
- Density information for unit conversion

**Key Attributes:**
- **Brand Name:** Product brand (e.g., "King Arthur")
- **Product Name:** Specific product variant (e.g., "All-Purpose Flour")
- **Purchase Unit:** Unit in which product is sold (e.g., "25lb bag")
- **Package Size:** Numeric quantity (e.g., 25) with unit (e.g., "lb")
- **Ingredient Link:** Foreign key to L2 ingredient only

### 2.2 Key Relationships

```
Product
  ├─ ingredient_id → Ingredient (L2 only)
  ├─ ingredient_l0_id → Ingredient (propagated from L2)
  ├─ ingredient_l1_id → Ingredient (propagated from L2)
  ├─ default_vendor_id → Vendor (optional)
  ├─ purchases → Purchase (many)
  └─ inventory_items → InventoryItem (many)
```

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Product Management:**
- ✅ Create products linked to L2 ingredients
- ✅ Edit product metadata (brand, name, purchase unit, package size)
- ✅ Link products to single L2 ingredient via cascading selectors
- ✅ Automatic L0/L1 propagation from selected ingredient
- ✅ Product list filtering by ingredient hierarchy (L0 → L1 → L2)
- ✅ Product import/export for AI-assisted catalog expansion

**Ingredient Integration:**
- ✅ Cascading ingredient selectors (L0 → L1 → L2) in product edit form
- ✅ Validation preventing assignment to non-leaf ingredients
- ✅ Automatic hierarchy update when ingredient hierarchy changes

**Density Support:**
- ✅ Four-field density model (volume amount, volume unit, weight amount, weight unit)
- ✅ Density data for volume-to-weight conversions in inventory

### 3.2 Out of Scope (Phase 2)

**Explicitly NOT Yet Supported:**
- ❌ Multi-vendor product pricing tracking
- ❌ Product availability/stock status at vendors
- ❌ Product substitution recommendations
- ❌ Product barcodes/UPC codes
- ❌ Product images
- ❌ Product review/rating system

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Add new products when I discover new brands or package sizes
2. Link products to the correct ingredient so inventory tracking works
3. See all products for a specific ingredient (e.g., all AP flour brands)
4. Filter products by ingredient hierarchy to find what I need quickly
5. Track which vendor I typically purchase each product from

**As a purchaser, I want to:**
1. See which products are available for an ingredient
2. Select products when creating purchase orders
3. Know the purchase unit and package size before buying
4. Have the system suggest products based on ingredient requirements

**As an inventory manager, I want to:**
1. Link inventory items to specific products
2. Track product density for accurate volume-to-weight conversions
3. See which products have active inventory
4. Filter inventory by product or ingredient

### 4.2 Use Case: Create New Product

**Actor:** Baker  
**Preconditions:** Ingredient hierarchy exists with L2 ingredient "King Arthur AP Flour"  
**Main Flow:**
1. User opens Products tab
2. Clicks "Add Product"
3. Enters brand: "King Arthur"
4. Enters product name: "All-Purpose Flour"
5. Selects ingredient via cascading selectors:
   - L0: Flour
   - L1: All-Purpose
   - L2: King Arthur AP Flour
6. System propagates L0/L1 from selected L2
7. Enters purchase unit: "25lb bag"
8. Enters package size: 25, unit: lb
9. User saves

**Postconditions:**
- Product created with ingredient linkage
- L0/L1 propagated automatically
- Product available for purchase orders
- Product available for inventory tracking

### 4.3 Use Case: Filter Products by Ingredient

**Actor:** Baker  
**Preconditions:** Multiple products exist for different ingredients  
**Main Flow:**
1. User opens Products tab
2. Selects L0 filter: "Chocolate"
3. L1 dropdown updates to show: Dark, Milk, White
4. Selects L1 filter: "Dark Chocolate"
5. L2 dropdown updates to show leaf ingredients
6. Selects L2 filter: "Semi-Sweet Chocolate Chips"
7. Product list filters to show only products linked to that ingredient

**Postconditions:**
- Product list shows only matching products
- Clear filters returns to full list

---

## 5. Functional Requirements

### 5.1 Product Management

**REQ-PRD-001:** System shall support product creation with brand, name, purchase unit, package size  
**REQ-PRD-002:** System shall link each product to exactly one L2 ingredient  
**REQ-PRD-003:** System shall automatically propagate L0/L1 from selected L2 ingredient  
**REQ-PRD-004:** System shall validate products are linked only to L2 ingredients  
**REQ-PRD-005:** System shall support product editing (metadata and ingredient link)  
**REQ-PRD-006:** System shall support product deletion with validation (no inventory or purchases)  
**REQ-PRD-007:** System shall generate unique identifiers for products

### 5.2 Ingredient Selection

**REQ-PRD-008:** Product edit form shall use cascading ingredient selectors (L0 → L1 → L2)  
**REQ-PRD-009:** System shall prevent product assignment to L0 or L1 ingredients  
**REQ-PRD-010:** System shall update product L0/L1 when ingredient hierarchy changes  
**REQ-PRD-011:** System shall validate ingredient exists before saving product

### 5.3 Product Filtering

**REQ-PRD-012:** Products tab shall support filtering by ingredient hierarchy (L0 → L1 → L2)  
**REQ-PRD-013:** Cascading filters shall update L1 options based on L0 selection  
**REQ-PRD-014:** Cascading filters shall update L2 options based on L1 selection  
**REQ-PRD-015:** System shall support clearing filters to show all products  
**REQ-PRD-016:** System shall support text search across brand and product name

### 5.4 Density Management

**REQ-PRD-017:** System shall support optional density specification (4-field model)  
**REQ-PRD-018:** Density fields: volume_amount, volume_unit, weight_amount, weight_unit  
**REQ-PRD-019:** System shall validate density fields are all present or all absent  
**REQ-PRD-020:** System shall use density for inventory unit conversions

### 5.5 Import/Export

**REQ-PRD-021:** System shall export products in JSON format (normalized and denormalized)  
**REQ-PRD-022:** System shall import products with automatic ingredient resolution  
**REQ-PRD-023:** System shall handle missing ingredients during import with user prompt  
**REQ-PRD-024:** System shall validate product integrity after import (ingredient exists)

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-PRD-NFR-001:** Product creation shall require max 5 clicks  
**REQ-PRD-NFR-002:** Ingredient selection via cascading selectors shall feel instant  
**REQ-PRD-NFR-003:** Product filtering shall update list without page reload  
**REQ-PRD-NFR-004:** Error messages shall clearly explain validation failures

### 6.2 Data Integrity

**REQ-PRD-NFR-005:** No orphaned products (all must link to valid L2 ingredient)  
**REQ-PRD-NFR-006:** Product deletion shall prevent orphaning of inventory or purchases  
**REQ-PRD-NFR-007:** Ingredient hierarchy changes shall auto-update product L0/L1 references

### 6.3 Performance

**REQ-PRD-NFR-008:** Product list loading shall complete in <100ms for 500+ products  
**REQ-PRD-NFR-009:** Cascading filter updates shall feel instant (<50ms)  
**REQ-PRD-NFR-010:** Product search shall return results in <100ms

---

## 7. Data Model Summary

### 7.1 Product Table Structure

```
Product
├─ id (PK)
├─ uuid (unique)
├─ brand_name
├─ product_name
├─ ingredient_id (FK → Ingredient, L2 only, required)
├─ ingredient_l0_id (FK → Ingredient, propagated)
├─ ingredient_l1_id (FK → Ingredient, propagated)
├─ purchase_unit (text)
├─ package_size_amount (decimal, optional)
├─ package_size_unit (text, optional)
├─ default_vendor_id (FK → Vendor, optional)
├─ density_volume_amount (decimal, optional)
├─ density_volume_unit (text, optional)
├─ density_weight_amount (decimal, optional)
├─ density_weight_unit (text, optional)
└─ timestamps
```

### 7.2 Key Relationships

```
Ingredient (L2)
  └─ products (many)
       ├─ purchases (many)
       └─ inventory_items (many)
```

---

## 8. UI Requirements

### 8.1 Products Tab

**Display:**
- List view: Brand | Product Name | Ingredient (L2) | Subcategory (L1) | Root (L0) | Purchase Unit | Actions
- Filter: Cascading ingredient filters (L0 → L1 → L2), text search
- Sort: Alphabetical by brand/product, recently updated

**Actions:**
- Add Product
- Edit Product
- Delete Product (with validation)
- View Inventory (navigates to filtered Inventory tab)
- View Purchases (navigates to filtered Purchases tab)

### 8.2 Product Edit Form

**Layout:**
```
┌─ Edit Product ─────────────────────┐
│ Brand: [_______________]           │
│ Product Name: [_______________]    │
│                                    │
│ Ingredient:                        │
│   L0: [Flour ▼]                    │
│   L1: [All-Purpose ▼]              │
│   L2: [King Arthur AP ▼]           │
│                                    │
│ Purchase Unit: [25lb bag]          │
│ Package Size: [25] [lb ▼]          │
│                                    │
│ Default Vendor: [Vendor ▼] (opt)   │
│                                    │
│ Density (optional):                │
│   Volume: [1] [cup ▼]              │
│   Weight: [120] [g ▼]              │
│                                    │
│ [Cancel] [Save]                    │
└────────────────────────────────────┘
```

**Behavior:**
- Cascading ingredient selectors update L1/L2 based on L0/L1 selection
- Package size unit dropdown or free text
- Density fields all-or-nothing validation
- Save validates L2 ingredient selected

### 8.3 Product Filter Component

**Layout:**
```
┌─ Filter Products ──────────────────┐
│ Search: [_______________] 🔍       │
│                                    │
│ Ingredient:                        │
│   L0: [All ▼]                      │
│   L1: [All ▼]                      │
│   L2: [All ▼]                      │
│                                    │
│ [Clear Filters]                    │
└────────────────────────────────────┘
```

**Behavior:**
- L0 "All" shows all L1 options
- L1 "All" shows all L2 options within selected L0
- L2 "All" shows all products within selected L0/L1
- Clear Filters resets all dropdowns to "All"

---

## 9. Validation Rules

### 9.1 Creation Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PRD-001 | Brand name required | "Brand name cannot be empty" |
| VAL-PRD-002 | Product name required | "Product name cannot be empty" |
| VAL-PRD-003 | Ingredient (L2) required | "Please select an ingredient" |
| VAL-PRD-004 | Ingredient must be L2 | "Only leaf ingredients can have products" |
| VAL-PRD-005 | Purchase unit recommended | "Purchase unit is recommended" (warning, not error) |
| VAL-PRD-006 | Package size amount must be positive if specified | "Package size must be greater than zero" |
| VAL-PRD-007 | Package size unit required if amount specified | "Package size unit required" |

### 9.2 Density Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PRD-008 | Density all-or-nothing | "Density requires all 4 fields or none" |
| VAL-PRD-009 | Density volume amount must be positive | "Density volume must be greater than zero" |
| VAL-PRD-010 | Density weight amount must be positive | "Density weight must be greater than zero" |

### 9.3 Edit Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PRD-011 | Cannot change ingredient if has inventory | "Cannot change ingredient: product has active inventory" |
| VAL-PRD-012 | Cannot change ingredient if has purchases | "Cannot change ingredient: product has purchase history" |

### 9.4 Deletion Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PRD-013 | Cannot delete if has inventory | "Cannot delete: product has X inventory items" |
| VAL-PRD-014 | Cannot delete if has purchases | "Cannot delete: product has X purchases" |

---

## 10. Acceptance Criteria

### 10.1 Phase 2 (Current) Acceptance

**Must Have:**
- [x] Product creation with ingredient linkage via cascading selectors
- [x] Product editing (metadata and ingredient link)
- [x] Automatic L0/L1 propagation from L2 ingredient
- [x] Cascading ingredient filters in Products tab
- [x] Product import/export for catalog expansion
- [ ] Validation preventing non-L2 ingredient assignment
- [ ] Auto-update of L0/L1 when ingredient hierarchy changes

**Should Have:**
- [ ] Product deletion with validation (no inventory/purchases)
- [ ] Text search across brand and product name
- [ ] Default vendor assignment
- [ ] Density specification UI

**Nice to Have:**
- [ ] Product cloning (duplicate with new brand/name)
- [ ] Bulk product operations (assign vendor to multiple)
- [ ] Product usage statistics (purchase frequency, inventory levels)
- [ ] Product notes/comments field

---

## 11. Dependencies

### 11.1 Upstream Dependencies (Blocks This)

- ✅ Ingredient hierarchy (products require L2 ingredients)
- ✅ Import/export system
- ⏳ Vendor system (for default vendor assignment)

### 11.2 Downstream Dependencies (This Blocks)

- Purchase management (requires products for purchase orders)
- Inventory management (requires products for inventory tracking)
- Shopping list generation (requires products for purchase planning)

---

## 12. Testing Requirements

### 12.1 Test Coverage

**Unit Tests:**
- Product validation logic
- L0/L1 propagation from L2 ingredient
- Density all-or-nothing validation
- Unique identifier generation

**Integration Tests:**
- Product creation workflow
- Cascading selector behavior in edit form
- Cascading filter behavior in Products tab
- Import/export round-trip
- Auto-update L0/L1 on ingredient hierarchy change

**User Acceptance Tests:**
- Create product with cascading ingredient selection
- Filter products by ingredient hierarchy
- Edit product and change ingredient
- Import products with missing ingredients (resolve interactively)

---

## 13. Open Questions & Future Considerations

### 13.1 Open Questions

**Q1:** Should products support multiple vendors with different prices?  
**A1:** Deferred to Phase 3. Phase 2 uses single default vendor per product.

**Q2:** Should products track historical pricing?  
**A2:** Not required for Phase 2. Consider for Phase 3.

**Q3:** Should products support package quantity (e.g., "pack of 6")?  
**A3:** Not required for Phase 2. Use purchase unit text for now.

**Q4:** Should product units be standardized or free text?  
**A4:** Phase 2 uses free text. UN/CEFACT standardization deferred.

### 13.2 Future Enhancements

**Phase 3 Candidates:**
- Multi-vendor pricing tracking
- Product availability status
- Product substitution suggestions
- Product images
- Barcode/UPC code tracking
- Product categories/tags (beyond ingredient hierarchy)

**Phase 4 Candidates:**
- AI-suggested product matching from receipts
- Product price comparison across vendors
- Product review/rating system
- Product sharing across users

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

- **Design Specs:** `/docs/func-spec/F031_ingredient_hierarchy.md` (cascading selectors architecture)
- **Bug Reports:** TBD (Product-related bugs to be cataloged)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)
- **Data Model:** `/docs/design/architecture.md` (database schema)
- **Requirements:** `/docs/requirements/req_ingredients.md` (ingredient dependency)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT - SEEDED)**
