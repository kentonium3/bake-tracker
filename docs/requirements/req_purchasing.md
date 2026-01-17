# Purchasing - Requirements Document

**Component:** Purchasing (Purchase Transaction Recording & Management)  
**Version:** 0.2 (DRAFT)  
**Last Updated:** 2026-01-17  
**Status:** Draft - Clarified Requirements  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Purchasing is the **transactional subsystem** within bake-tracker that records the acquisition of products (food) and material products (non-food). Purchases create the historical record of what was bought, when, where, at what price, and in what quantity, serving as the foundation for inventory management, cost tracking, and supplier relationship management.

### 1.2 Business Purpose

The Purchasing system serves multiple business functions:

1. **Transaction Recording:** Captures purchase events as they occur (date, product, supplier, price, quantity)
2. **Inventory Source:** Provides the data that creates and increases inventory items
3. **Cost Tracking:** Records actual purchase prices for weighted average cost calculations
4. **Supplier History:** Tracks which products are purchased from which suppliers
5. **Price History:** Enables price trend analysis and comparison shopping
6. **Product Discovery:** Facilitates adding new products to catalog through purchase recording

### 1.3 Design Rationale

**Transactional Data Classification:** Purchases are transactional data (immutable events), distinct from catalog data (products, ingredients). Once recorded, purchases should not be modified as they represent historical facts.

**Product-First Design:** Every purchase must reference an existing product. If a product doesn't exist in the catalog, the purchase workflow must create it (potentially in provisional/review state) before the purchase can be recorded.

**Inventory Integration:** Purchases automatically trigger inventory updates by calling inventory services. Purchase service doesn't implement inventory logic; it delegates to inventory service.

---

## 2. Purchase Structure

### 2.1 Core Components

**Purchase Entity (Food Products):**
- Purchase metadata (date, price, quantity, notes)
- Required link to Product (via foreign key)
- Required link to Supplier (via foreign key)
- Immutable after creation (no edit/delete in production use)

**MaterialPurchase Entity (Non-Food):**
- Same structure as Purchase
- Links to MaterialProduct instead of Product
- Separate table for clean domain separation

**Key Attributes:**
- **Purchase Date:** When item was acquired
- **Product Reference:** What was purchased (Product or MaterialProduct)
- **Supplier Reference:** Where it was purchased
- **Unit Price:** Price per package (as purchased)
- **Quantity Purchased:** Number of packages
- **Total Cost:** Calculated (unit_price × quantity)
- **Notes:** Optional context (sale info, quality notes)

### 2.2 Key Relationships

```
Purchase
  ├─ product_id → Product (required)
  ├─ supplier_id → Supplier (required)
  └─ Triggers: inventory_service.add_from_purchase()

MaterialPurchase
  ├─ material_product_id → MaterialProduct (required)
  ├─ supplier_id → Supplier (required)
  └─ Triggers: inventory_service.add_from_material_purchase()
```

### 2.3 Product Lifecycle Integration

**When Product Exists:** Purchase → Inventory Update (straightforward)

**When Product Doesn't Exist:** Purchase → Product Creation → Purchase → Inventory Update

**Product Creation from Purchase (Provisional State):**
1. Purchase service receives purchase data with unknown product
2. Purchase service calls product_catalog_service.create_provisional_product()
3. Provisional product created with:
   - Available data from purchase (brand, description, UPC if available)
   - Generated slug (with uniqueness validation)
   - Flag: `needs_review = true` or `provisional = true`
   - Missing/incomplete fields flagged for later completion
4. Purchase references new provisional product
5. Inventory created from purchase
6. User reviews provisional products separately (queue/workflow)
7. User completes missing fields, corrects errors
8. Product marked as reviewed/complete

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Purchase Recording:**
- ✅ Manual purchase entry (UI form)
- ✅ Bulk purchase import (JSON format per F040)
- ✅ UPC-based product matching (delegates to product_catalog_service)
- ✅ Unknown product resolution (create provisional products)
- ✅ Automatic inventory updates (calls inventory_service)
- ✅ Purchase validation (positive quantities, valid references)

**Product Integration:**
- ✅ Product lookup by UPC, slug, or search
- ✅ Provisional product creation when needed
- ✅ Slug generation with uniqueness validation
- ✅ Provisional product flagging for review queue

**Inventory Integration:**
- ✅ Automatic inventory increase after purchase recording
- ✅ Delegation to inventory_service (purchase doesn't implement inventory logic)
- ✅ Cost tracking for weighted average calculations

**Purchase History:**
- ✅ View purchase history (list, filter, search)
- ✅ Filter by product, supplier, date range
- ✅ Purchase detail views
- ✅ Export purchase history

### 3.2 Out of Scope

**Explicitly NOT Purchasing Concerns:**
- ❌ UPC matching algorithm implementation (product_catalog_service responsibility)
- ❌ Product slug generation algorithm (product_catalog_service responsibility)
- ❌ Inventory quantity calculations (inventory_service responsibility)
- ❌ File transport (Dropbox, Drive sync - external concern)
- ❌ File monitoring/detection (desktop OS concern)
- ❌ Mobile app implementation (external system)
- ❌ CSV import (JSON only per project decision)
- ❌ Purchase editing after creation (immutable transactions)
- ❌ Purchase deletion (archived, not deleted)

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Quickly record purchases after shopping trip
2. Have system look up products by UPC code
3. Add new products when I buy something for the first time
4. See my purchase history to track spending patterns
5. Know which supplier has best prices for specific products

**As a purchaser using mobile/AI, I want to:**
1. Scan UPCs while shopping and have purchases recorded automatically
2. Have unknown products added to system with minimal manual work
3. Review and correct provisional products in batch later
4. Not be blocked from recording purchases due to incomplete product info

**As a cost tracker, I want to:**
1. See actual purchase prices over time
2. Track price trends by supplier
3. Know weighted average cost of inventory items
4. Identify best value suppliers for each product

### 4.2 Use Case: Record Purchase of Known Product

**Actor:** Baker  
**Preconditions:** 
- Product "King Arthur AP Flour 25lb" exists in catalog
- Supplier "Costco Waltham MA" exists in system

**Main Flow:**
1. User opens Purchases tab
2. Clicks "Add Purchase"
3. Searches for product by name or UPC
4. Selects "King Arthur AP Flour 25lb"
5. Selects supplier "Costco Waltham MA"
6. Enters date: 2026-01-15
7. Enters unit price: $7.99
8. Enters quantity: 2
9. System shows total: $15.98
10. User saves

**Postconditions:**
- Purchase record created
- Inventory increased by 2 packages (50 lbs total)
- Purchase appears in history

### 4.3 Use Case: Record Purchase of Unknown Product (Create Provisional)

**Actor:** Baker  
**Preconditions:** 
- Product does not exist in catalog
- User has UPC code or product description

**Main Flow:**
1. User opens Purchases tab or imports JSON with unknown UPC
2. System attempts product lookup by UPC: NOT FOUND
3. System prompts: "Product not found. Create new product?"
4. User confirms
5. System presents provisional product creation:
   - Pre-filled UPC (if available)
   - User enters brand: "Bob's Red Mill"
   - User enters description: "Organic All-Purpose Flour 5lb"
   - System generates slug: "bobs_red_mill_organic_all_purpose_flour_5lb"
   - System validates slug uniqueness (regenerates if needed with suffix)
   - User selects ingredient (cascading selector)
   - Optional fields marked as "complete later"
6. System creates provisional product with flag: `needs_review = true`
7. Purchase references new provisional product
8. Purchase saved
9. System shows notification: "Product created as provisional - review in Product Catalog"

**Postconditions:**
- Provisional product created with available info
- Purchase recorded referencing provisional product
- Inventory created from purchase
- Product appears in "Needs Review" queue
- User can complete product details later

### 4.4 Use Case: Review Provisional Products

**Actor:** Baker  
**Preconditions:** 
- System has provisional products flagged `needs_review = true`

**Main Flow:**
1. User opens Products tab
2. Filters to "Needs Review" or "Provisional Products"
3. List shows products with incomplete/unverified info
4. User selects provisional product
5. System highlights missing fields (package size, density, etc.)
6. User completes/corrects fields
7. User marks as reviewed
8. System clears `needs_review` flag

**Postconditions:**
- Product fully validated and complete
- Product available for normal use
- Removed from review queue

### 4.5 Use Case: Import Purchases from JSON (F040 Format)

**Actor:** System (automated)  
**Preconditions:** 
- User has JSON file with purchase data (AI-generated or manual)

**Main Flow:**
1. User/system provides JSON file path
2. Purchase service reads and validates JSON
3. For each purchase in JSON:
   a. Looks up product by UPC via product_catalog_service
   b. If found: proceeds to step 4
   c. If not found: creates provisional product (case 4.3)
4. Validates supplier (looks up or creates)
5. Creates purchase record
6. Calls inventory_service.add_from_purchase()
7. Records result (success/skip/error)
8. Returns import summary

**Postconditions:**
- All matched purchases recorded
- Unknown products created as provisional
- Inventory updated
- Import summary shows results

---

## 5. Functional Requirements

### 5.1 Purchase Recording

**REQ-PUR-001:** System shall support manual purchase recording via UI form  
**REQ-PUR-002:** System shall support bulk purchase import via JSON (F040 format)  
**REQ-PUR-003:** System shall validate purchase date, price, quantity before saving  
**REQ-PUR-004:** System shall require positive unit price and quantity  
**REQ-PUR-005:** System shall calculate total cost (unit_price × quantity_purchased)  
**REQ-PUR-006:** System shall detect potential duplicate purchases (same product/supplier/date/price within tolerance) and warn user, but allow override  
**REQ-PUR-007:** System shall generate unique identifiers for purchases

### 5.2 Product Resolution

**REQ-PUR-008:** Purchase service shall look up products by UPC via product_catalog_service  
**REQ-PUR-009:** Purchase service shall look up products by slug via product_catalog_service  
**REQ-PUR-010:** Purchase service shall support product search by name/brand  
**REQ-PUR-011:** When product not found, purchase service shall delegate provisional product creation to product_catalog_service  
**REQ-PUR-012:** Purchase service shall NOT implement product creation logic directly  
**REQ-PUR-013:** Purchase service shall NOT implement slug generation logic directly  
**REQ-PUR-014:** Product model shall support optional UPC code field (indexed for lookup)

### 5.3 Provisional Product Creation (via product_catalog_service)

**REQ-PUR-015:** Provisional products shall be created with `needs_review = true` flag  
**REQ-PUR-016:** Provisional products shall be created with available data (brand, description, UPC)  
**REQ-PUR-017:** Provisional products shall have slugs generated by product_catalog_service  
**REQ-PUR-018:** Slug generation shall validate uniqueness and retry with suffix if collision  
**REQ-PUR-019:** Provisional products shall allow missing optional fields (package size, density)  
**REQ-PUR-020:** Provisional products shall require minimum viable data (brand OR description, ingredient)  
**REQ-PUR-021:** Provisional products shall be usable immediately (not blocked on completion)  
**REQ-PUR-022:** Product catalog service shall provide method to create provisional products with context data from purchase

### 5.4 Inventory Integration

**REQ-PUR-023:** Purchase recording shall trigger inventory_service.add_from_purchase()  
**REQ-PUR-024:** Purchase service shall NOT implement inventory quantity logic  
**REQ-PUR-025:** Purchase service shall NOT implement cost calculation logic beyond total_cost  
**REQ-PUR-026:** Inventory service shall handle weighted average cost calculations  
**REQ-PUR-027:** Failed inventory updates shall roll back purchase creation

### 5.5 Supplier Integration

**REQ-PUR-028:** Every purchase shall reference a supplier  
**REQ-PUR-029:** Purchase service shall look up suppliers by name or slug  
**REQ-PUR-030:** If supplier not found, purchase service shall create supplier record  
**REQ-PUR-031:** Auto-created suppliers shall generate unique slugs  
**REQ-PUR-032:** Supplier creation delegated to supplier service (not purchase service)

### 5.6 Purchase History

**REQ-PUR-033:** System shall display purchase history in reverse chronological order  
**REQ-PUR-034:** System shall support filtering purchases by product  
**REQ-PUR-035:** System shall support filtering purchases by supplier  
**REQ-PUR-036:** System shall support filtering purchases by date range  
**REQ-PUR-037:** System shall support text search across product names and suppliers  
**REQ-PUR-038:** System shall display purchase details (product, supplier, date, price, quantity, total)

### 5.7 Provisional Product Review

**REQ-PUR-039:** Products tab shall provide filter for provisional products (needs_review = true)  
**REQ-PUR-040:** Provisional product list shall highlight missing/incomplete fields  
**REQ-PUR-041:** User shall be able to edit provisional products to complete missing fields  
**REQ-PUR-042:** User shall be able to mark provisional product as reviewed  
**REQ-PUR-043:** Marking as reviewed shall clear needs_review flag  
**REQ-PUR-044:** Provisional products shall show count of purchases referencing them  
**REQ-PUR-045:** Review queue shall sort by creation date (newest first)

### 5.8 Import/Export

**REQ-PUR-046:** System shall export purchases in JSON format  
**REQ-PUR-047:** System shall import purchases from JSON (F040 format)  
**REQ-PUR-048:** Purchase import shall support UPC-based product matching  
**REQ-PUR-049:** Purchase import shall handle unknown products via provisional creation  
**REQ-PUR-050:** Purchase import shall return structured results (success/skip/error counts)  
**REQ-PUR-051:** Import UI shall display import results clearly to user  
**REQ-PUR-052:** Import UI shall offer navigation to provisional product review queue

### 5.9 MaterialPurchase Parity

**REQ-PUR-053:** MaterialPurchase shall mirror Purchase functionality for non-food items  
**REQ-PUR-054:** MaterialPurchase shall reference MaterialProduct instead of Product  
**REQ-PUR-055:** MaterialPurchase shall support same validation rules as Purchase  
**REQ-PUR-056:** MaterialPurchase shall trigger inventory_service.add_from_material_purchase()  
**REQ-PUR-057:** MaterialPurchase shall support provisional MaterialProduct creation  
**REQ-PUR-058:** MaterialPurchase import/export shall follow same patterns as Purchase

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-PUR-NFR-001:** Manual purchase entry shall require max 6 clicks  
**REQ-PUR-NFR-002:** Product search shall return results in <100ms  
**REQ-PUR-NFR-003:** Purchase list shall update without page reload  
**REQ-PUR-NFR-004:** Provisional product creation shall not block purchase workflow  
**REQ-PUR-NFR-005:** Error messages shall clearly explain validation failures

### 6.2 Data Integrity

**REQ-PUR-NFR-006:** Purchases shall be immutable after creation (no edit/delete)  
**REQ-PUR-NFR-007:** Purchase → Inventory update shall be atomic (both succeed or both fail)  
**REQ-PUR-NFR-008:** Provisional products shall not break purchase history or inventory  
**REQ-PUR-NFR-009:** Slug uniqueness shall be guaranteed via validation retry logic

### 6.3 Performance

**REQ-PUR-NFR-010:** Purchase list shall load <100ms for 1000+ purchases  
**REQ-PUR-NFR-011:** JSON import shall process 100 purchases in <5 seconds  
**REQ-PUR-NFR-012:** Duplicate detection shall complete in <50ms per purchase

### 6.4 Separation of Concerns

**REQ-PUR-NFR-013:** Purchase service shall NOT implement product catalog logic  
**REQ-PUR-NFR-014:** Purchase service shall NOT implement inventory calculation logic  
**REQ-PUR-NFR-015:** Purchase service shall delegate to specialized services via well-defined interfaces

---

## 7. Service Boundaries

### 7.1 What Purchase Service Owns

**Purchase service responsibilities:**
- Validate purchase data (date, price, quantity, references)
- Create purchase records in database
- Coordinate product lookup (calls product_catalog_service)
- Coordinate inventory updates (calls inventory_service)
- Coordinate supplier lookup/creation (calls supplier_service)
- Return import results (success/skip/error)
- Query purchase history

### 7.2 What Purchase Service Does NOT Own

**Delegated to product_catalog_service:**
- UPC matching algorithm
- Slug generation algorithm
- Product creation logic
- Product validation rules
- Provisional product flagging

**Delegated to inventory_service:**
- Inventory quantity calculations
- Weighted average cost calculations
- FIFO inventory management
- Inventory item creation

**Delegated to supplier_service:**
- Supplier lookup logic
- Supplier slug generation
- Supplier validation

**External concerns (not service layer):**
- File transport (Dropbox/Drive sync)
- File monitoring/detection
- Mobile app logic
- UI presentation

---

## 8. Data Model Summary

### 8.1 Purchase Table Structure

```
Purchase
├─ id (PK)
├─ uuid (unique)
├─ product_id (FK → Product, required)
├─ supplier_id (FK → Supplier, required)
├─ purchase_date (date, required)
├─ unit_price (decimal, required, > 0)
├─ quantity_purchased (decimal, required, > 0)
├─ total_cost (decimal, computed: unit_price × quantity)
├─ notes (text, optional)
└─ timestamps (created_at, immutable)
```

### 8.2 MaterialPurchase Table Structure

```
MaterialPurchase
├─ id (PK)
├─ uuid (unique)
├─ material_product_id (FK → MaterialProduct, required)
├─ supplier_id (FK → Supplier, required)
├─ purchase_date (date, required)
├─ unit_price (decimal, required, > 0)
├─ quantity_purchased (decimal, required, > 0)
├─ total_cost (decimal, computed)
├─ notes (text, optional)
└─ timestamps (created_at, immutable)
```

### 8.3 Provisional Product Indicators

**Option A: Flag field on Product (RECOMMENDED)**
```
Product
├─ ... (existing fields)
├─ upc_code (text, optional, indexed for lookup)
├─ needs_review (boolean, default: false)
└─ provisional (boolean, default: false)
```

**Notes on Product fields:**
- `upc_code`: Universal Product Code for lookup during purchase import
- `needs_review`: Flag indicating provisional product needs completion
- `provisional`: Alternative/alias flag (use one or the other, not both)
- Product must have slug field (see req_products.md)

**Option B: Separate provisional product queue table**
```
ProvisionalProduct
├─ product_id (FK → Product, unique)
├─ created_from (enum: purchase, import, manual)
├─ missing_fields (json array: ["package_size", "density"])
└─ timestamps
```

**Recommendation:** Option A simpler for MVP, Option B if review workflow gets complex

---

## 9. JSON Import Format (F040)

### 9.1 Purchase Import Schema

```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-17T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco Waltham MA",
  "purchases": [
    {
      "upc": "051000127952",
      "scanned_at": "2026-01-17T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 2.0,
      "supplier": "Costco Waltham MA",
      "notes": "Weekly shopping",
      "product_description": "King Arthur All-Purpose Flour 25lb"
    }
  ]
}
```

### 9.2 Import Workflow

```
1. Validate JSON structure
2. For each purchase:
   a. Lookup product by UPC
   b. If not found:
      - Extract brand/description from purchase data
      - Call product_catalog_service.create_provisional_product()
      - Generate/validate slug
      - Create provisional product with needs_review=true
   c. Lookup/create supplier
   d. Create purchase record
   e. Call inventory_service.add_from_purchase()
3. Return results summary
```

---

## 10. UI Requirements

### 10.1 Purchases Tab

**Display:**
- List view: Date | Product | Supplier | Unit Price | Quantity | Total | Notes
- Filter: Product search, Supplier dropdown, Date range, Text search
- Sort: Date (desc default), Product, Supplier, Price

**Actions:**
- Add Purchase (manual entry)
- Import Purchases (JSON file)
- View Details
- Export Purchase History

### 10.2 Add Purchase Dialog

**Layout:**
```
┌─ Add Purchase ─────────────────────┐
│ Product: [Search or scan UPC...]   │
│   → [King Arthur AP 25lb]          │
│                                    │
│ If not found: [+ Create Product]   │
│                                    │
│ Supplier: [Costco Waltham ▼]       │
│                                    │
│ Purchase Date: [2026-01-17 📅]     │
│                                    │
│ Unit Price: [$____.__]             │
│ Quantity: [___] packages           │
│ Total: $15.98 (calculated)         │
│                                    │
│ Notes: [____________________]      │
│                                    │
│ [Cancel] [Save Purchase]           │
└────────────────────────────────────┘
```

**Behavior:**
- Product search shows matches as user types
- UPC scan triggers product lookup
- "Create Product" opens provisional product creation flow
- Total auto-calculates from price × quantity
- Save validates all required fields

### 10.3 Provisional Product Creation (Inline)

**Layout:**
```
┌─ Create Product (Quick Add) ───────┐
│ Product not found. Create new?     │
│                                    │
│ UPC: [051000127952] (if scanned)   │
│ Brand: [______________]            │
│ Description: [______________]      │
│                                    │
│ Ingredient:                        │
│   L0: [Flour ▼]                    │
│   L1: [All-Purpose ▼]              │
│   L2: [Generic AP ▼]               │
│                                    │
│ ⓘ Additional details can be        │
│   completed later in Products tab  │
│                                    │
│ [Cancel] [Create & Continue]       │
└────────────────────────────────────┘
```

**Behavior:**
- UPC pre-filled if available
- Minimum required: brand/description, ingredient
- Optional fields skipped (added to review queue)
- "Create & Continue" creates provisional product and returns to purchase form

### 10.4 Provisional Products Queue

**Location:** Products Tab → Filter: "Needs Review"

**Display:**
- List shows products with `needs_review = true`
- Highlight missing fields (package size, density, etc.)
- Show purchase count (how many purchases reference this product)

**Actions:**
- Edit Product (complete missing fields)
- Mark as Reviewed (clears flag)

---

## 11. Validation Rules

### 11.1 Purchase Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PUR-001 | Product required | "Please select a product" |
| VAL-PUR-002 | Supplier required | "Please select a supplier" |
| VAL-PUR-003 | Purchase date required | "Purchase date cannot be empty" |
| VAL-PUR-004 | Purchase date not in future | "Purchase date cannot be in the future" |
| VAL-PUR-005 | Unit price must be positive | "Unit price must be greater than zero" |
| VAL-PUR-006 | Quantity must be positive | "Quantity must be greater than zero" |
| VAL-PUR-007 | Duplicate purchase detection (warning only) | "Warning: Similar purchase already exists (same product/supplier/date/price). Continue anyway?" |

### 11.2 Provisional Product Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PUR-008 | Brand OR description required | "Product needs at least brand or description" |
| VAL-PUR-009 | Ingredient (L2) required | "Please select an ingredient" |
| VAL-PUR-010 | Slug must be unique | "Product slug already exists (will auto-generate suffix)" |

### 11.3 Import Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PUR-011 | JSON schema version supported | "Unsupported schema version" |
| VAL-PUR-012 | import_type must be "purchases" | "Wrong import type (expected 'purchases')" |
| VAL-PUR-013 | purchases array not empty | "No purchases found in file" |

---

## 12. Acceptance Criteria

### 12.1 Phase 2 (Current) Acceptance

**Must Have:**
- [ ] Manual purchase entry via UI form
- [ ] JSON purchase import (F040 format)
- [ ] UPC-based product matching (delegates to product_catalog_service)
- [ ] Provisional product creation when product not found
- [ ] Slug generation with uniqueness validation
- [ ] Automatic inventory updates (calls inventory_service)
- [ ] Purchase history list with filtering
- [ ] Provisional product review queue

**Should Have:**
- [ ] Duplicate purchase detection (warning, not hard block)
- [ ] Supplier auto-creation if not found
- [ ] Purchase export (JSON format)
- [ ] Purchase detail view

**Nice to Have:**
- [ ] Batch provisional product review
- [ ] Price history visualization
- [ ] Supplier price comparison

---

## 13. Dependencies

### 13.1 Upstream Dependencies (Blocks This)

- ✅ Product catalog (purchases require products)
- ✅ Ingredient hierarchy (provisional products require ingredients)
- ✅ Supplier system (purchases require suppliers)
- ✅ Inventory service (purchases trigger inventory updates)
- ⏳ F040 AI-assisted import format (schema defined, implementation needed)

### 13.2 Downstream Dependencies (This Blocks)

- Cost tracking analytics (requires purchase history)
- Price comparison features (requires purchase prices)
- Supplier evaluation (requires supplier purchase history)

---

## 14. Open Questions & Future Considerations

### 14.1 Open Questions

**Q1:** Should purchases be editable after creation?  
**A1:** No for production use (immutable transactions). Archive/void instead of delete.

**Q2:** How to handle purchase returns/refunds?  
**A2:** Deferred. Consider negative purchases or separate return transaction type.

**Q3:** Should system prevent duplicate purchases?  
**A3:** Warning only, not hard block (user may intentionally buy same item twice).

**Q4:** How aggressive should provisional product creation be?  
**A4:** Create immediately with minimum data. Flag for review. Don't block purchase workflow.

**Q5:** Should provisional products have different slug naming?  
**A5:** No, treat same as regular products. Flag field sufficient.

**Q6:** What if slug collision detected during provisional creation?  
**A6:** Auto-append numeric suffix (_2, _3, etc.) and retry validation.

### 14.2 Future Enhancements

**Phase 3 Candidates:**
- Purchase editing/voiding workflow
- Return/refund transactions
- Price trend analysis
- Supplier price comparison dashboard
- Automated supplier recommendations
- Receipt OCR integration

**Phase 4 Candidates:**
- Predictive purchase suggestions
- Bulk purchase approval workflows
- Purchase order generation
- Multi-currency support

---

## 15. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-17 | Kent Gale | Initial draft based on F040/F049 analysis |
| 0.2 | 2026-01-17 | Kent Gale | Clarified requirements: Added UPC code field to Product model (REQ-PUR-014), Added provisional product review requirements (REQ-PUR-039 to REQ-PUR-045), Added MaterialPurchase parity requirements (REQ-PUR-053 to REQ-PUR-058), Added import UI requirements (REQ-PUR-051, REQ-PUR-052), Clarified duplicate detection as warning only (REQ-PUR-006, VAL-PUR-007), Added requirement for product_catalog_service provisional creation method (REQ-PUR-022) |

---

## 16. Approval & Sign-off

**Document Owner:** Kent Gale  
**Last Review Date:** 2026-01-17  
**Next Review Date:** TBD  
**Status:** 📝 DRAFT - Clarified Requirements

---

## 17. Related Documents

- **Design Specs:** 
  - `/docs/design/F040_import_export_v4.md` (AI-assisted purchase import)
  - `/docs/design/F043_purchases_tab_implementation.md` (UI implementation)
  - `/docs/design/F049_import_export_phase1.md` (transaction imports)
- **Requirements:** 
  - `/docs/requirements/req_products.md` (product catalog dependency)
  - `/docs/requirements/req_inventory.md` (inventory integration)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT)**
