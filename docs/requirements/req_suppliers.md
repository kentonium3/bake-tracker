# Suppliers - Requirements Document

**Component:** Suppliers (Vendor Management & Data Portability)  
**Version:** 2.0  
**Last Updated:** 2026-01-12  
**Status:** Draft  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Suppliers represent vendors and stores where ingredients, products, and materials are purchased. The Supplier system supports both physical brick-and-mortar locations (with address information) and online vendors (with website URLs). Suppliers play a critical role in purchase tracking, inventory management, shopping list organization, and future e-commerce integration.

### 1.2 Business Purpose

The Supplier system serves multiple business functions:

1. **Purchase Tracking:** Record where ingredients and products are purchased for cost analysis and shopping optimization
2. **Data Portability:** Enable reliable supplier identification across different database instances without relying on auto-increment IDs
3. **Product Cataloging:** Link products to preferred suppliers for purchasing recommendations
4. **Shopping List Organization:** (Future) Group items by supplier for efficient shopping trips
5. **E-Commerce Integration:** (Future Web) Support food delivery service connections and supplier partnerships
6. **Revenue Generation:** (Future Web) Enable supplier advertising and promotional partnerships

### 1.3 Supplier Types Context

Suppliers fall into two categories with different requirements:

| Supplier Type | Required Fields | Optional Fields | Example |
|--------------|----------------|-----------------|---------|
| **Physical** | name, city, state, zip_code | website_url, street_address, notes | Wegmans (Burlington, MA) |
| **Online** | name, website_url | city, state, zip_code, notes | King Arthur Baking (kingarthurbaking.com) |

---

## 2. Supplier Management

### 2.1 Core Supplier Attributes

**Physical Suppliers:**
- Name (e.g., "Wegmans", "Costco", "Stop & Shop")
- Street address (optional but recommended)
- City (required)
- State (required, 2-letter uppercase code)
- ZIP code (required)
- Website URL (optional)
- Notes (e.g., membership requirements, directions)

**Online Suppliers:**
- Name (e.g., "King Arthur Baking", "Amazon")
- Website URL (required)
- City/State/ZIP (optional)
- Notes (e.g., shipping policies, minimum order)

**Common Attributes:**
- Supplier type: 'physical' or 'online'
- Active status flag (soft delete)
- Portable identifier (slug) for cross-environment identification

### 2.2 Supplier Identity & Portability

**Portable Identification (Current Priority):**
- Each supplier must have a unique, stable slug identifier
- Slugs enable data portability across dev/test/production environments
- Slugs support import/export without ID-based fragility
- Physical suppliers: slug derived from `{name}_{city}_{state}`
- Online suppliers: slug derived from `{name}`
- Slug conflicts resolved with numeric suffixes (`_2`, `_3`, etc.)

**Special Suppliers:**
- "Unknown" supplier: Default for legacy inventory migrations (id=1, slug: `unknown_unknown_xx`)
- System-required supplier for backward compatibility

---

## 3. Scope & Boundaries

### 3.1 In Scope (Current Phase)

**Supplier Management:**
- ✅ Create physical suppliers with required address fields
- ✅ Create online suppliers with required website URL
- ✅ Edit supplier information (name, address, type, notes)
- ✅ Soft-delete suppliers (mark inactive)
- ✅ Validate supplier type requirements (physical vs online)
- ✅ Generate unique slug identifiers on creation

**Product Integration:**
- ✅ Link products to preferred suppliers
- ✅ Optional supplier assignment (products can exist without preferred supplier)
- ✅ Display supplier information in product lists

**Import/Export:**
- ✅ Export suppliers with slug-based identification
- ✅ Import suppliers using slug matching (not name/city/state)
- ✅ Export products with supplier slug references
- ✅ Import products with supplier slug resolution

**Data Portability:**
- ✅ Slug-based cross-environment supplier identification
- ✅ Backward compatibility with ID-based legacy exports

### 3.2 Out of Scope (Future Phases)

**Explicitly NOT in Current Phase:**
- ❌ Shopping list organization by supplier (Phase 3)
- ❌ Supplier contact information (phone, email, hours)
- ❌ Supplier pricing comparison tools
- ❌ Multi-location supplier chains management
- ❌ Supplier product availability tracking
- ❌ E-commerce integration (Web Phase)
- ❌ Food delivery service connections (Web Phase)
- ❌ Supplier advertising platform (Web Phase - Revenue)
- ❌ Supplier partnership dashboard (Web Phase - B2B)
- ❌ Supplier performance analytics (Phase 4)

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Record where I purchased ingredients so I can find them again
2. Track which stores carry specific products
3. See supplier information when reviewing purchase history
4. Link products to preferred suppliers for easy reordering
5. (Future) Organize my shopping list by store to minimize trips

**As a developer, I want to:**
1. Export product catalogs with supplier references that work across environments
2. Import supplier data without manual ID mapping
3. Trust that supplier references survive export/import cycles
4. Identify suppliers consistently across dev, test, and production databases

**As a business owner (Future Web), I want to:**
1. Partner with suppliers for promotional opportunities
2. Enable food delivery service integrations
3. Generate revenue through supplier advertising
4. Provide customers with purchasing options

### 4.2 Use Case: Create Physical Supplier

**Actor:** Baker  
**Preconditions:** None  
**Main Flow:**
1. User opens Suppliers management
2. Clicks "Add Supplier"
3. Selects type: "Physical Store"
4. Enters name: "Wegmans"
5. Enters address: "53 Third Avenue, Burlington, MA 01803"
6. Optionally enters website URL
7. Optionally enters notes
8. System auto-generates slug: `wegmans_burlington_ma`
9. User saves

**Postconditions:**
- Supplier created with unique slug
- Supplier available for product association
- Supplier appears in purchase entry dropdowns

### 4.3 Use Case: Create Online Supplier

**Actor:** Baker  
**Preconditions:** None  
**Main Flow:**
1. User opens Suppliers management
2. Clicks "Add Supplier"
3. Selects type: "Online Vendor"
4. Enters name: "King Arthur Baking"
5. Enters website URL: "https://www.kingarthurbaking.com"
6. Optionally enters notes
7. System auto-generates slug: `king_arthur_baking`
8. User saves

**Postconditions:**
- Supplier created with unique slug
- Supplier available for product association

### 4.4 Use Case: Link Product to Preferred Supplier

**Actor:** Baker  
**Preconditions:** Product exists, Supplier exists  
**Main Flow:**
1. User opens product edit form
2. Selects "Preferred Supplier" dropdown
3. Chooses supplier: "Wegmans (Burlington, MA)"
4. User saves product
5. System links product to supplier via ID

**Postconditions:**
- Product shows preferred supplier in product list
- Preferred supplier available when creating purchases

### 4.5 Use Case: Export/Import Products with Supplier References

**Actor:** Developer  
**Preconditions:** Products exist with preferred suppliers  
**Main Flow:**
1. User exports product catalog
2. System includes supplier slug references in export
3. User deletes database (or moves to different environment)
4. User re-initializes with suppliers (matching slugs)
5. User imports products
6. System resolves supplier slugs to supplier IDs in target database
7. Product-supplier associations preserved

**Postconditions:**
- Products linked to correct suppliers via slug resolution
- No manual ID remapping required

---

## 5. Functional Requirements

### 5.1 Supplier Creation & Management

**REQ-SUP-001:** System shall support creation of physical suppliers with required fields: name, city, state, zip_code  
**REQ-SUP-002:** System shall support creation of online suppliers with required fields: name, website_url  
**REQ-SUP-003:** System shall validate physical suppliers have city, state, and zip_code  
**REQ-SUP-004:** System shall validate online suppliers have website_url  
**REQ-SUP-005:** System shall validate state field as 2-letter uppercase code  
**REQ-SUP-006:** System shall support optional street_address field for physical suppliers  
**REQ-SUP-007:** System shall support optional notes field for all suppliers  
**REQ-SUP-008:** System shall support soft-delete via is_active flag (True = active, False = inactive)  
**REQ-SUP-009:** System shall support editing supplier information (name, address, type, notes)  
**REQ-SUP-010:** System shall prevent deletion of suppliers referenced by products or purchases

### 5.2 Portable Identification (Slug)

**REQ-SUP-011:** System shall auto-generate unique slug identifier on supplier creation  
**REQ-SUP-012:** System shall generate slugs for physical suppliers using pattern: `{name}_{city}_{state}`  
**REQ-SUP-013:** System shall generate slugs for online suppliers using pattern: `{name}`  
**REQ-SUP-014:** System shall normalize slugs: lowercase, spaces→underscores, remove non-alphanumeric except underscores  
**REQ-SUP-015:** System shall validate slug uniqueness before saving supplier  
**REQ-SUP-016:** System shall append numeric suffixes (`_2`, `_3`) to resolve slug conflicts  
**REQ-SUP-017:** System shall prevent slug modification after creation (immutable)  
**REQ-SUP-018:** System shall index slug field for fast lookups  
**REQ-SUP-019:** System shall enforce non-null constraint on slug field

### 5.3 Product Integration

**REQ-SUP-020:** System shall support linking products to preferred supplier (optional)  
**REQ-SUP-021:** System shall display supplier information in product lists  
**REQ-SUP-022:** System shall allow products without preferred supplier  
**REQ-SUP-023:** System shall validate supplier exists before linking to product  
**REQ-SUP-024:** System shall allow changing product's preferred supplier

### 5.4 Supplier Import

**REQ-SUP-025:** System shall import suppliers in JSON format  
**REQ-SUP-026:** System shall match imported suppliers by slug (not name/city/state)  
**REQ-SUP-027:** System shall support merge mode (update existing + add new suppliers)  
**REQ-SUP-028:** System shall support skip mode (add new suppliers only)  
**REQ-SUP-029:** System shall validate supplier data before import  
**REQ-SUP-030:** System shall log validation errors during import  
**REQ-SUP-031:** System shall support dry-run mode (preview without database changes)

### 5.5 Supplier Export

**REQ-SUP-032:** System shall export suppliers in JSON format with slug field  
**REQ-SUP-033:** System shall include all supplier fields in export (name, city, state, zip, type, url, notes, is_active)  
**REQ-SUP-034:** System shall include metadata (export timestamp, count)  
**REQ-SUP-035:** System shall export format matching ingredient/material patterns

### 5.6 Product Import/Export with Supplier References

**REQ-SUP-036:** Product export shall include preferred_supplier_slug when supplier is set  
**REQ-SUP-037:** Product export shall include preferred_supplier_name for human readability  
**REQ-SUP-038:** Product export shall maintain preferred_supplier_id for backward compatibility  
**REQ-SUP-039:** Product import shall resolve preferred_supplier_slug to preferred_supplier_id  
**REQ-SUP-040:** Product import shall fall back to preferred_supplier_id if slug not present (legacy support)  
**REQ-SUP-041:** Product import shall log warnings when supplier slug cannot be resolved  
**REQ-SUP-042:** Product import shall allow products without supplier references

---

## 6. Non-Functional Requirements

### 6.1 Performance

**REQ-SUP-NFR-001:** Slug generation shall complete in <10ms per supplier  
**REQ-SUP-NFR-002:** Slug uniqueness validation shall use database index (no table scan)  
**REQ-SUP-NFR-003:** Supplier lookup by slug shall complete in <5ms  
**REQ-SUP-NFR-004:** Supplier list loading shall complete in <100ms for 100+ suppliers

### 6.2 Data Integrity

**REQ-SUP-NFR-005:** Slugs shall be immutable after creation  
**REQ-SUP-NFR-006:** All suppliers shall have unique, non-null slugs  
**REQ-SUP-NFR-007:** Supplier deletion shall not orphan product references (foreign key cascade/set null)  
**REQ-SUP-NFR-008:** Slug conflicts shall be resolved deterministically (no race conditions)  
**REQ-SUP-NFR-009:** State codes shall be validated as 2-letter uppercase  
**REQ-SUP-NFR-010:** Supplier type shall be validated as 'physical' or 'online' only

### 6.3 Usability

**REQ-SUP-NFR-011:** Supplier creation shall require max 5 clicks  
**REQ-SUP-NFR-012:** Slug conflicts shall be logged with clear descriptions  
**REQ-SUP-NFR-013:** Import errors for missing supplier slugs shall include supplier name  
**REQ-SUP-NFR-014:** Supplier validation errors shall be clear and actionable  
**REQ-SUP-NFR-015:** Supplier type selection shall be obvious (physical vs online)

---

## 7. Data Model Summary

### 7.1 Supplier Table Structure

```
Supplier
├─ id (PK, auto-increment)
├─ slug (String, unique, indexed, non-nullable)
├─ name (String, required)
├─ supplier_type (String: 'physical' | 'online', required)
├─ website_url (String, optional)
├─ street_address (String, optional)
├─ city (String, required for physical, optional for online)
├─ state (String, required for physical, optional for online)
├─ zip_code (String, required for physical, optional for online)
├─ notes (Text, optional)
├─ is_active (Boolean, default True)
├─ created_at (DateTime)
└─ updated_at (DateTime)
```

### 7.2 Key Relationships

```
Supplier
├─ products (many) → Product.preferred_supplier_id
└─ purchases (many) → Purchase.supplier_id
```

### 7.3 Indexes

- Primary key on `id`
- Unique index on `slug`
- Index on `name` and `city` (composite)
- Index on `is_active`
- Index on `supplier_type`

---

## 8. UI Requirements

### 8.1 Supplier Management View

**Display:**
- List view: Name | Type | Location | Actions
- Filter: Active/Inactive, Physical/Online
- Sort: Alphabetical by name, recently updated

**Actions:**
- Add Supplier
- Edit Supplier
- Toggle Active/Inactive
- View Products (navigates to filtered Products tab)
- View Purchases (navigates to filtered Purchases tab)

### 8.2 Supplier Edit Form

**Layout:**
```
┌─ Edit Supplier ─────────────────────┐
│ Name: [_______________]             │
│                                     │
│ Type: ( ) Physical  ( ) Online      │
│                                     │
│ [IF PHYSICAL]                       │
│   Street Address: [_______________] │
│   City: [_______________]           │
│   State: [__]                       │
│   ZIP: [_____]                      │
│                                     │
│ [IF ONLINE OR PHYSICAL]             │
│   Website URL: [_______________]    │
│                                     │
│ Notes: [_______________________]    │
│        [_______________________]    │
│                                     │
│ [Cancel] [Save]                     │
└─────────────────────────────────────┘
```

**Behavior:**
- Type selection (physical/online) shows/hides relevant fields
- Physical type: city, state, zip required
- Online type: website_url required
- Slug auto-generates on save (displayed read-only after creation)
- Validation errors shown inline

### 8.3 Product Edit Form - Supplier Selection

**Layout (within Product Edit):**
```
┌─ Product Details ───────────────────┐
│ ...                                 │
│                                     │
│ Preferred Supplier:                 │
│   [None ▼]                          │
│   - None                            │
│   - Wegmans (Burlington, MA)        │
│   - Costco (Waltham, MA)            │
│   - King Arthur Baking (Online)     │
│                                     │
│ ...                                 │
└─────────────────────────────────────┘
```

**Behavior:**
- Dropdown shows active suppliers only
- Physical suppliers: "Name (City, State)"
- Online suppliers: "Name (Online)"
- Optional field (can select "None")

---

## 9. Validation Rules

### 9.1 Supplier Creation Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-SUP-001 | Name required | "Supplier name cannot be empty" |
| VAL-SUP-002 | Supplier type required | "Please select supplier type (physical or online)" |
| VAL-SUP-003 | Physical: city required | "City is required for physical suppliers" |
| VAL-SUP-004 | Physical: state required | "State is required for physical suppliers" |
| VAL-SUP-005 | Physical: zip required | "ZIP code is required for physical suppliers" |
| VAL-SUP-006 | Online: website_url required | "Website URL is required for online suppliers" |
| VAL-SUP-007 | State must be 2-letter uppercase | "State must be 2-letter code (e.g., MA, CA)" |
| VAL-SUP-008 | Supplier type must be 'physical' or 'online' | "Invalid supplier type" |

### 9.2 Slug Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-SUP-009 | Slug must not be empty | "Supplier slug cannot be empty" |
| VAL-SUP-010 | Slug must be unique | "Supplier slug '{slug}' already exists" |
| VAL-SUP-011 | Slug max length 100 chars | "Supplier slug exceeds 100 characters" |
| VAL-SUP-012 | Slug must match pattern `^[a-z0-9_]+$` | "Supplier slug contains invalid characters" |
| VAL-SUP-013 | Slug cannot be modified | "Supplier slug is immutable" |

### 9.3 Import Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-SUP-014 | Supplier slug must exist for product import | "Supplier slug '{slug}' not found for product '{product}'" |
| VAL-SUP-015 | Supplier JSON must include required fields | "Supplier import missing required field: {field}" |
| VAL-SUP-016 | Physical suppliers must have city/state/zip | "Physical supplier '{name}' missing address fields" |
| VAL-SUP-017 | Online suppliers must have website_url | "Online supplier '{name}' missing website URL" |

### 9.4 Deletion Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-SUP-018 | Cannot delete if has products | "Cannot delete: supplier has {count} products" |
| VAL-SUP-019 | Cannot delete if has purchases | "Cannot delete: supplier has {count} purchases" |

---

## 10. Acceptance Criteria

### 10.1 Current Phase Acceptance

**Must Have:**
- [ ] Supplier model includes all required fields (name, type, address, slug)
- [ ] Physical supplier creation requires city/state/zip
- [ ] Online supplier creation requires website_url
- [ ] Slugs auto-generate on creation
- [ ] Slug conflicts resolve with numeric suffixes
- [ ] Supplier import/export functionality works
- [ ] Product import resolves supplier slug references
- [ ] Migration adds slugs to existing suppliers
- [ ] Validation prevents invalid supplier data

**Should Have:**
- [ ] Supplier edit form intuitive (type selection shows/hides fields)
- [ ] Supplier list filtering by type and status
- [ ] Slug generation preview before save
- [ ] Import dry-run mode works

**Nice to Have:**
- [ ] Supplier usage statistics (product count, purchase count)
- [ ] Bulk supplier import/update
- [ ] Supplier duplicate detection suggestions

### 10.2 Future Phase Acceptance

**Phase 3: Shopping List Organization**
- [ ] Shopping list items grouped by supplier
- [ ] Supplier selection optimizes trip planning
- [ ] Multi-supplier trip planning support

**Phase 4 (Web): E-Commerce Integration**
- [ ] Food delivery service API integration
- [ ] Supplier partnership dashboard
- [ ] Promotional content management
- [ ] Supplier advertising platform

**Phase 5: Analytics & Optimization**
- [ ] Supplier performance tracking (price, availability)
- [ ] Supplier comparison tools
- [ ] Purchase pattern analysis by supplier

---

## 11. Dependencies

### 11.1 Upstream Dependencies (Blocks This)

- ✅ Product model with preferred_supplier_id FK
- ✅ Purchase model with supplier_id FK
- ✅ Import/export service infrastructure
- ⏳ Enhanced import service (for FK resolution patterns)

### 11.2 Downstream Dependencies (This Blocks)

- Feature 048: Import/Export Rationalization (supplier portability)
- Web Migration: Multi-environment supplier references
- Mobile Integration: Supplier catalog sync
- Shopping List Feature: Supplier-based organization
- E-Commerce Integration: Food delivery partnerships
- Advertising Platform: Supplier promotional content

---

## 12. Testing Requirements

### 12.1 Unit Tests

**Supplier Creation:**
- Create physical supplier with all required fields
- Create online supplier with required fields
- Validate physical supplier address requirements
- Validate online supplier URL requirement
- Reject invalid supplier type

**Slug Generation:**
- Generate slug for physical supplier: `wegmans_burlington_ma`
- Generate slug for online supplier: `king_arthur_baking`
- Handle conflicts with numeric suffixes: `wegmans_burlington_ma_2`
- Normalize special characters: "Stop & Shop" → `stop_shop`
- Enforce uniqueness constraint

**Validation:**
- Reject empty name
- Reject physical supplier without city/state/zip
- Reject online supplier without website_url
- Reject invalid state code (not 2 letters)
- Reject invalid supplier type

### 12.2 Integration Tests

**Supplier CRUD:**
- Create, read, update physical supplier
- Create, read, update online supplier
- Soft-delete supplier (mark inactive)
- Prevent deletion with product references
- Prevent deletion with purchase references

**Product Integration:**
- Link product to preferred supplier
- Unlink product from supplier
- Display supplier in product list

**Import/Export:**
- Export suppliers with slugs
- Import suppliers into fresh database
- Match suppliers by slug
- Merge mode updates existing suppliers
- Skip mode ignores existing suppliers

**Product Import/Export:**
- Export products with supplier references
- Import products into fresh database
- Verify supplier associations intact
- Import legacy file without slugs (fallback to IDs)

### 12.3 User Acceptance Tests

**Scenario 1: Create Physical Supplier**
1. Open Supplier management
2. Click "Add Supplier"
3. Select "Physical Store"
4. Enter name, address details
5. Save
6. Verify supplier appears in list
7. Verify slug generated correctly

**Scenario 2: Export/Import with Supplier References**
1. Export products with preferred suppliers
2. Delete database
3. Re-initialize with suppliers (matching slugs)
4. Import products
5. Verify supplier associations correct

**Scenario 3: Handle Missing Supplier on Import**
1. Export products with supplier references
2. Import into database missing one supplier
3. Verify warning message identifies missing supplier
4. Manually create supplier
5. Retry import succeeds

---

## 13. Open Questions & Future Considerations

### 13.1 Open Questions

**Q1:** Should suppliers support multiple locations (e.g., "Wegmans" chain)?  
**A1:** Not in current phase - each location is separate supplier. Future enhancement: supplier chains.

**Q2:** Should system track supplier contact information (phone, email, hours)?  
**A2:** Not required for current phase. Consider for Phase 4 (e-commerce integration).

**Q3:** Should slugs be editable in admin UI for manual correction?  
**A3:** No - slugs are immutable to maintain referential integrity. If correction needed, delete and recreate.

**Q4:** How should system handle supplier name changes?  
**A4:** Slug remains unchanged (immutable). Slug represents identity at creation time, not current state.

### 13.2 Future Enhancements

**Phase 3: Shopping List Organization**
- Group shopping list items by supplier
- Optimize trip planning across multiple suppliers
- Supplier distance/location mapping

**Phase 4 (Web): E-Commerce Integration**
- Food delivery service API connections (Instacart, Amazon Fresh)
- Supplier partnership portal
- Promotional content management
- Supplier advertising dashboard
- Revenue sharing model

**Phase 5: Advanced Features**
- Supplier chains management (link related locations)
- Supplier pricing comparison tools
- Supplier product availability tracking
- Supplier performance analytics
- Supplier merge/deduplication tools
- Slug aliases (multiple slugs → one supplier)

---

## 14. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-12 | Kent Gale | Initial requirements document (slug-focused) |
| 2.0 | 2026-01-12 | Kent Gale | Generalized requirements, added future phases (shopping lists, e-commerce, advertising) |

---

## 15. Approval & Sign-off

**Document Owner:** Kent Gale  
**Last Review Date:** 2026-01-12  
**Next Review Date:** TBD (after Phase 2 implementation)  
**Status:** 📝 DRAFT

---

## 16. Related Documents

- **Technical Debt:** `/docs/archive/tech-debt/_TD-009_supplier_slug_portable_identification.md`
- **Design Specs:** `/kitty-specs/0XX-supplier-slug-support/spec.md` (v1.0)
- **Constitution:** `/.kittify/memory/constitution.md`
- **Data Model:** Supplier model (`/src/models/supplier.py`), Product model (`/src/models/product.py`)
- **Test Data:** `/test_data/suppliers.json`

---

**END OF REQUIREMENTS DOCUMENT**
