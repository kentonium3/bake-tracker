# F0XX: Purchase Management and Recording

**Version**: 2.0
**Priority**: HIGH
**Type**: Full Stack (Service + UI)

---

## Executive Summary

Purchase recording currently requires products to exist in catalog before purchases can be recorded. This blocks real-world workflows where new products are discovered during shopping. Additionally, manual entry is the only option—no bulk import support exists despite JSON import service layer being implemented in F040.

Current gaps:
- ❌ Cannot record purchases of unknown products (blocked workflow)
- ❌ No provisional product creation from purchase workflow
- ❌ No JSON purchase import UI (F040 service exists, no UI integration)
- ❌ Purchase service implements product/inventory logic (wrong boundaries)

This spec enables purchase recording regardless of product catalog state, adds JSON import UI integration, and establishes proper service boundaries.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Purchase Recording
├─ ✅ Manual purchase entry UI (F043)
├─ ✅ Purchase model exists
├─ ❌ Blocks when product not in catalog
└─ ❌ No bulk import UI

Product Catalog Integration
├─ ❌ Purchase service doesn't coordinate with product_catalog_service
├─ ❌ No provisional product creation workflow
└─ ❌ No product review queue

JSON Import (F040 Service Layer)
├─ ✅ JSON schema defined (UPC-based purchases)
├─ ✅ Service layer implemented
└─ ❌ No UI integration

Service Boundaries
├─ ❌ Purchase service may implement UPC matching (product catalog concern)
├─ ❌ Purchase service may implement inventory logic (inventory service concern)
└─ ❌ No clear delegation to specialized services
```

**Target State (COMPLETE):**
```
Purchase Recording
├─ ✅ Manual entry for known products
├─ ✅ Provisional product creation for unknown products
├─ ✅ JSON bulk import with UI
└─ ✅ Purchase workflow never blocked

Product Catalog Integration
├─ ✅ Purchase service delegates to product_catalog_service
├─ ✅ Provisional products created with needs_review flag
├─ ✅ Product review queue in Products tab
└─ ✅ Slug generation with uniqueness validation

Inventory Integration
├─ ✅ Purchase service delegates to inventory_service
├─ ✅ Automatic inventory increase after purchase
└─ ✅ No inventory logic in purchase service

Service Boundaries (Clean Separation)
├─ ✅ Purchase service: Recording and coordination only
├─ ✅ Product catalog service: Product lookup, creation, slug generation
├─ ✅ Inventory service: Inventory updates, cost calculations
└─ ✅ Supplier service: Supplier lookup, creation
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F040 AI-Assisted Import Service (Implemented)**
   - Find F040 service layer implementation
   - Study JSON schema validation
   - Note UPC matching workflow (may need refactoring to product_catalog_service)
   - Understand import result structure

2. **Purchase Service and Model (F043)**
   - Find `src/services/purchase_service.py`
   - Find `src/models/purchase.py`
   - Study existing purchase creation patterns
   - Note validation rules

3. **Purchase UI (F043 - Already Exists)**
   - Find `src/ui/tabs/purchases_tab.py`
   - Find `src/ui/dialogs/add_purchase_dialog.py`
   - Study manual purchase entry workflow
   - Note form structure and validation

4. **Product Catalog Service**
   - Find `src/services/product_catalog_service.py` (or similar)
   - Study product lookup methods (by UPC, by slug, by search)
   - Study product creation patterns
   - Note slug generation approach

5. **Inventory Service**
   - Find `src/services/inventory_service.py`
   - Study how purchases trigger inventory updates
   - Note `add_from_purchase()` or similar method
   - Understand weighted average cost calculation

6. **Supplier Service**
   - Find `src/services/supplier_service.py`
   - Study supplier lookup patterns
   - Note supplier creation approach

---

## Requirements Reference

This specification implements:
- **REQ-PUR-001 to REQ-PUR-007**: Purchase Recording
- **REQ-PUR-008 to REQ-PUR-014**: Product Resolution  
- **REQ-PUR-015 to REQ-PUR-022**: Provisional Product Creation
- **REQ-PUR-023 to REQ-PUR-027**: Inventory Integration
- **REQ-PUR-039 to REQ-PUR-045**: Provisional Product Review
- **REQ-PUR-046 to REQ-PUR-052**: Import/Export
- **REQ-PUR-NFR-013 to REQ-PUR-NFR-015**: Service Boundaries

From: `docs/requirements/req_purchasing.md` (v0.2)

---

## Functional Requirements

### FR-1: Manual Purchase Entry for Known Products

**What it must do:**
- Support manual purchase recording via UI form (already exists in F043)
- Validate purchase date, price, quantity
- Require positive unit price and quantity
- Calculate total cost (unit_price × quantity_purchased)
- Prevent duplicate purchases (warn, don't hard block)

**Pattern reference:** Study existing add_purchase_dialog.py, enhance with product lookup delegation

**Success criteria:**
- [ ] Can record purchase when product exists
- [ ] Form validates required fields
- [ ] Total cost calculated correctly
- [ ] Duplicate detection shows warning
- [ ] Purchase appears in history after save

---

### FR-2: Product Lookup and Search

**What it must do:**
- Delegate product lookup to product_catalog_service
- Support product search by UPC code
- Support product search by name/brand
- Support product search by slug
- Return clear "not found" when product doesn't exist

**Pattern reference:** Study how product_catalog_service exposes lookup methods

**Business rules:**
- UPC matching is product_catalog_service responsibility
- Purchase service calls product_catalog_service, doesn't implement matching
- "Not found" triggers provisional product creation workflow (FR-3)

**Success criteria:**
- [ ] Product lookup delegates to product_catalog_service
- [ ] UPC search works when product exists
- [ ] Name/brand search returns matches
- [ ] "Not found" clearly indicated
- [ ] No UPC matching logic in purchase service

---

### FR-3: Provisional Product Creation for Unknown Products

**What it must do:**
- When product not found, offer to create provisional product
- Delegate provisional product creation to product_catalog_service
- Provide available data (UPC, brand, description from purchase context)
- Allow user to select ingredient (cascading selector)
- Product catalog service generates slug with uniqueness validation
- Product catalog service creates product with `needs_review = true` flag
- Purchase can reference new provisional product immediately

**Pattern reference:** Study product creation in product_catalog_service, add provisional flag support

**Business rules:**
- Provisional products created by product_catalog_service, not purchase service
- Slug generation is product_catalog_service responsibility
- Slug uniqueness validated by product_catalog_service (retry with suffix if needed)
- Purchase service provides context, doesn't implement creation logic
- Provisional products usable immediately (not blocked on completion)

**Success criteria:**
- [ ] "Product not found" prompts user to create provisional product
- [ ] User can enter brand, description, select ingredient
- [ ] Slug generated by product_catalog_service
- [ ] Slug uniqueness validated (auto-suffix on collision)
- [ ] Provisional product created with `needs_review = true`
- [ ] Purchase references provisional product successfully
- [ ] Inventory created from purchase with provisional product

---

### FR-4: Provisional Product Review Queue

**What it must do:**
- Products tab shows filter for "Needs Review" or "Provisional Products"
- Filter shows products where `needs_review = true`
- Highlight missing/incomplete fields (package size, density, etc.)
- Allow user to complete fields and mark as reviewed
- Clear `needs_review` flag when reviewed

**Pattern reference:** Study Products tab filtering, add provisional filter option

**Success criteria:**
- [ ] Products tab has "Needs Review" filter
- [ ] Filter shows only provisional products
- [ ] Missing fields clearly indicated
- [ ] User can edit and complete product details
- [ ] User can mark as reviewed
- [ ] `needs_review` flag cleared after review

---

### FR-5: JSON Purchase Import (UI Integration for F040)

**What it must do:**
- Provide UI to select JSON file
- Call F040 import service with file path
- Display import results (success/skip/error counts)
- Handle unknown products via provisional creation (delegates to product_catalog_service)
- Show which products were created as provisional
- Offer to navigate to provisional product review queue

**Pattern reference:** Study F049 import UI patterns, adapt for purchase import

**UI Requirements:**
- File selection dialog
- Import progress indicator
- Results summary display
- Clear messaging for provisional products created
- Option to review provisional products immediately

**Success criteria:**
- [ ] User can select JSON file
- [ ] Import service called correctly
- [ ] Results displayed clearly
- [ ] Unknown products create provisional products
- [ ] User notified of provisional products
- [ ] Can navigate to review queue

---

### FR-6: Inventory Integration (Delegation)

**What it must do:**
- After successful purchase recording, call inventory_service
- Pass purchase details to inventory_service.add_from_purchase()
- Purchase service does NOT implement inventory quantity logic
- Purchase service does NOT implement cost calculation logic
- Inventory service handles weighted average costs
- Failed inventory updates roll back purchase creation

**Pattern reference:** Study how inventory_service.add_from_purchase() is called

**Business rules:**
- Inventory updates are inventory_service responsibility
- Purchase service coordinates, doesn't implement
- Atomic transaction (both purchase and inventory succeed or both fail)

**Success criteria:**
- [ ] Purchase recording calls inventory_service.add_from_purchase()
- [ ] Inventory increased after successful purchase
- [ ] No inventory logic in purchase service code
- [ ] Failed inventory update rolls back purchase
- [ ] Weighted average cost calculated by inventory service

---

### FR-7: Supplier Integration (Delegation)

**What it must do:**
- Delegate supplier lookup to supplier_service
- If supplier not found, delegate supplier creation to supplier_service
- Purchase service does NOT implement supplier slug generation
- Auto-created suppliers get unique slugs from supplier_service

**Pattern reference:** Study supplier_service lookup and creation methods

**Success criteria:**
- [ ] Supplier lookup delegates to supplier_service
- [ ] Supplier creation delegates to supplier_service
- [ ] No supplier slug generation in purchase service
- [ ] Auto-created suppliers have unique slugs
- [ ] Every purchase references valid supplier

---

### FR-8: Purchase History and Filtering

**What it must do:**
- Display purchase history in reverse chronological order (already exists in F043)
- Support filtering by product, supplier, date range
- Support text search across products and suppliers
- Show purchase details (product, supplier, date, price, quantity, total)

**Pattern reference:** Study existing purchases_tab.py implementation

**Success criteria:**
- [ ] Purchase list shows recent purchases
- [ ] Filters work correctly
- [ ] Search finds relevant purchases
- [ ] Performance acceptable with 100+ purchases

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ CSV import (JSON only per project decision)
- ❌ UPC matching algorithm implementation (product_catalog_service responsibility)
- ❌ Slug generation algorithm implementation (product_catalog_service responsibility)
- ❌ Inventory quantity calculations (inventory_service responsibility)
- ❌ Weighted average cost calculations (inventory_service responsibility)
- ❌ File transport mechanisms (Dropbox/Drive sync - external concern)
- ❌ File monitoring/detection (desktop OS concern, not service layer)
- ❌ Mobile app implementation (external system)
- ❌ Purchase editing after creation (immutable transactions)
- ❌ Purchase deletion (archive, don't delete)
- ❌ Receipt OCR (external tool generates JSON, not purchase service)

**Rationale:** This spec focuses on purchase recording and coordination. Specialized logic belongs in domain-specific services (product catalog, inventory, supplier). External concerns (file transport, mobile app) are separate systems.

---

## Success Criteria

**Complete when:**

### Manual Purchase Entry
- [ ] Can record purchase when product exists
- [ ] Can create provisional product when product doesn't exist
- [ ] Form validation prevents invalid entries
- [ ] Total cost calculated correctly
- [ ] Duplicate detection warns user

### Provisional Product Creation
- [ ] "Product not found" offers provisional creation
- [ ] User provides brand/description, selects ingredient
- [ ] Slug generated by product_catalog_service
- [ ] Slug uniqueness validated (auto-suffix on collision)
- [ ] Provisional product created with `needs_review = true`
- [ ] Purchase references provisional product successfully
- [ ] Purchase workflow not blocked by unknown products

### Provisional Product Review
- [ ] Products tab has "Needs Review" filter
- [ ] Filter shows provisional products only
- [ ] Missing fields highlighted
- [ ] User can complete and mark reviewed
- [ ] Flag cleared after review

### JSON Import
- [ ] Can select and import JSON file
- [ ] F040 service called correctly
- [ ] Results summary clear and accurate
- [ ] Unknown products create provisional products automatically
- [ ] User notified of provisional products
- [ ] Can navigate to review queue

### Service Boundaries
- [ ] Purchase service delegates product lookup to product_catalog_service
- [ ] Purchase service delegates inventory updates to inventory_service
- [ ] Purchase service delegates supplier operations to supplier_service
- [ ] No UPC matching in purchase service
- [ ] No slug generation in purchase service
- [ ] No inventory calculations in purchase service

### Purchase History
- [ ] Recent purchases easily visible
- [ ] Filters work correctly
- [ ] Search finds purchases
- [ ] Performance acceptable with 100+ purchases

### Quality
- [ ] All purchases link to valid products (including provisional)
- [ ] Inventory automatically updated
- [ ] Service layer tests cover purchase coordination
- [ ] Integration tests cover provisional product workflow
- [ ] UI follows project conventions

---

## Architecture Principles

### Service Boundary Separation

**Purchase Service Responsibilities:**
- Validate purchase data (date, price, quantity, references)
- Create purchase records
- Coordinate with other services (delegate, don't implement)
- Return import results

**Purchase Service Does NOT:**
- Implement UPC matching (delegates to product_catalog_service)
- Implement slug generation (delegates to product_catalog_service)
- Implement product creation logic (delegates to product_catalog_service)
- Implement inventory calculations (delegates to inventory_service)
- Implement supplier slug generation (delegates to supplier_service)

**Rationale:** Clean service boundaries prevent duplication, enable reuse, maintain single source of truth for each domain.

---

### Provisional Product Pattern

**Design Philosophy:**
- Purchase workflow never blocked by missing products
- Provisional products created with minimum viable data
- Missing/incomplete fields flagged for later completion
- Provisional products immediately usable
- Review queue enables batch completion

**Provisional Product Lifecycle:**
1. Purchase encounters unknown product
2. Product catalog service creates provisional product (needs_review=true)
3. Purchase references provisional product
4. Inventory created from purchase
5. User reviews and completes product details later
6. Product marked as reviewed (needs_review=false)

**Rationale:** Separates purchase recording (time-sensitive) from product catalog completion (can be deferred).

---

### JSON Import Integration

**F040 Service Layer (Implemented):**
- JSON schema validation
- UPC-based product matching
- Purchase record creation
- Inventory updates

**This Spec (UI Layer):**
- File selection UI
- Call F040 service
- Display results
- Navigate to review queue

**Rationale:** F040 did service layer, this spec adds UI. No service duplication.

---

### Immutable Transactions

**Purchase as Historical Record:**
- Purchases are immutable after creation
- No edit/delete in production use
- Archive rather than delete if needed
- Purchase date, price, quantity are facts, not opinions

**Rationale:** Transaction integrity, audit trail, cost history accuracy.

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Purchase validation prevents invalid data
- Slug uniqueness guaranteed via product_catalog_service validation
- Atomic transactions (purchase + inventory both succeed or both fail)
- Provisional products don't break referential integrity

✅ **Principle II: Future-Proof Schema**
- Provisional product flag enables gradual catalog completion
- Service boundaries support future enhancements
- JSON import format extensible (F040 schema)

✅ **Principle V: Layered Architecture Discipline**
- Purchase service coordinates, doesn't implement domain logic
- Product catalog service handles products
- Inventory service handles inventory
- Supplier service handles suppliers
- Clear delegation patterns

✅ **Principle VII: Pragmatic Aspiration**
- Phase 2 (Desktop): Manual entry + JSON import
- Future phases: Mobile app, receipt OCR, real-time sync
- Current design supports evolution without breaking changes

---

## Risk Considerations

**Risk: Provisional product creation may generate bad slugs**
- Context: Slug generation from purchase data may have quality issues
- Mitigation: Product catalog service owns slug generation, can improve algorithm without affecting purchase service; manual review queue catches issues

**Risk: User may skip provisional product review indefinitely**
- Context: Provisional products may accumulate in review queue
- Mitigation: Provisional products are immediately usable (purchase workflow not blocked); review queue visible in Products tab; future enhancement could add notifications

**Risk: F040 service may have different interface than expected**
- Context: Spec assumes F040 service exists with specific signature
- Mitigation: Planning phase discovers actual F040 interface; adapt purchase service coordination to match

**Risk: Service boundaries may require refactoring existing code**
- Context: Current purchase service may already implement UPC matching or inventory logic
- Mitigation: Planning phase identifies what needs refactoring; incremental approach (add delegation, then remove old code); comprehensive testing during refactor

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study F040 service layer → understand JSON import interface
- Study F043 purchase UI → enhance with provisional product workflow
- Study product_catalog_service → find lookup, creation, slug generation methods
- Study inventory_service → find add_from_purchase method
- Study supplier_service → find lookup and creation patterns

**Key Patterns to Copy:**
- F049 import UI → JSON purchase import UI
- Product creation in product_catalog_service → add provisional flag support
- Existing purchase recording → enhance with product lookup delegation

**Focus Areas:**
- Service boundary refactoring (move UPC matching to product_catalog_service if needed)
- Provisional product creation inline in purchase workflow (don't break flow)
- Slug uniqueness validation in product_catalog_service (retry with suffix)
- Error handling when services unavailable
- User messaging for provisional products created

**Integration with F040:**
- F040 provides service layer for JSON import
- This spec adds UI and provisional product workflow
- Don't duplicate F040 logic, just call it

**Service Coordination Pattern:**
```
Purchase Service (Coordinator)
  ├─ Calls: product_catalog_service.lookup_by_upc()
  ├─ Calls: product_catalog_service.create_provisional_product()
  ├─ Calls: supplier_service.lookup_or_create()
  ├─ Creates: Purchase record
  └─ Calls: inventory_service.add_from_purchase()
```

---

**END OF SPECIFICATION**
