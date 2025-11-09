# Feature Specification: Service Layer for Ingredient/Variant Architecture

**Feature Branch**: `002-service-layer-for`
**Created**: 2025-11-08
**Status**: Draft
**Input**: User description: "Implement all four service layer components to complete Phase 4 of the Ingredient/Variant refactor: IngredientService (catalog CRUD operations), VariantService (brand/package management), PantryService (inventory tracking with FIFO consumption), and PurchaseService (price history tracking and trend analysis). Enable UI interaction with the refactored data model through clean, testable service abstractions that enforce business rules."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingredient Catalog Management (Priority: P1)

The application can create, retrieve, update, and delete generic ingredient definitions in the catalog. Users can search and filter ingredients by name or category. The system ensures ingredient slugs are unique and prevents deletion of ingredients referenced by recipes.

**Why this priority**: Foundation for all other services. Without ingredient catalog management, users cannot define what ingredients exist, blocking all downstream workflows (variants, pantry, recipes).

**Independent Test**: Can be fully tested by creating ingredients through service methods, verifying CRUD operations work correctly, and confirming dependency checking prevents orphaned recipe references. Delivers immediate value by enabling ingredient data management without requiring UI.

**Acceptance Scenarios**:

1. **Given** no ingredients exist, **When** user creates a new ingredient with name "All-Purpose Flour" and category "Flour", **Then** system generates slug "all_purpose_flour", stores ingredient, and returns created object with ID and slug
2. **Given** ingredient "All-Purpose Flour" exists with slug "all_purpose_flour", **When** user searches for ingredients with query "flour", **Then** system returns list containing "All-Purpose Flour"
3. **Given** ingredient exists and is referenced by a recipe, **When** user attempts to delete the ingredient, **Then** system prevents deletion and returns error indicating dependencies exist
4. **Given** ingredient "All-Purpose Flour" exists, **When** user updates its category to "Baking Essentials", **Then** system saves the change and preserves the slug
5. **Given** user provides duplicate ingredient name, **When** attempting to create ingredient, **Then** system either prevents creation with error or auto-generates unique slug with numeric suffix

---

### User Story 2 - Brand/Package Variant Management (Priority: P2)

The application can create and manage brand-specific product variants for each ingredient. Users can define multiple brands, package sizes, and suppliers for a single ingredient. The system supports marking a preferred variant for shopping recommendations and tracks UPC codes for future barcode scanning.

**Why this priority**: Enables multi-brand support which is core value proposition of the refactor. Allows users to track that they can buy "All-Purpose Flour" from King Arthur (25 lb), Bob's Red Mill (5 lb), or store brand (10 lb).

**Independent Test**: Can be tested by creating variants linked to existing ingredients, verifying preferred variant toggling works, and confirming variants can be queried by ingredient. Delivers value by enabling brand/package tracking without requiring full pantry system.

**Acceptance Scenarios**:

1. **Given** ingredient "All-Purpose Flour" exists, **When** user creates variant with brand "King Arthur", package size "25 lb bag", purchase unit "lb", purchase quantity 25, **Then** system creates variant, links it to ingredient, and calculates display name "King Arthur - 25 lb bag"
2. **Given** ingredient has 3 variants, **When** user marks one variant as preferred, **Then** system sets preferred flag to true for selected variant and false for others
3. **Given** variant exists, **When** user retrieves all variants for an ingredient, **Then** system returns list sorted with preferred variant first
4. **Given** variant with UPC "012345678901" exists, **When** user searches by UPC, **Then** system returns matching variant
5. **Given** variant is not referenced by any pantry items, **When** user deletes variant, **Then** system removes it successfully
6. **Given** variant is referenced by pantry items, **When** user attempts to delete variant, **Then** system prevents deletion and returns error indicating dependencies

---

### User Story 3 - FIFO Pantry Inventory Tracking (Priority: P3)

The application can track actual inventory with lot-level detail including purchase date, expiration date, and location. Users can add items to pantry, view current quantities aggregated by ingredient, and consume inventory using FIFO (First In, First Out) logic. The system alerts users to items expiring soon.

**Why this priority**: Core business logic for accurate cost calculation and inventory management. FIFO ensures recipe costs reflect actual pantry consumption, matching physical reality where oldest items are used first.

**Independent Test**: Can be tested by adding pantry items with different purchase dates, consuming quantities using FIFO, and verifying consumption order matches purchase date chronology. Delivers value by enabling accurate inventory tracking and cost calculations.

**Acceptance Scenarios**:

1. **Given** user has purchased King Arthur flour on Jan 1 (10 lbs) and Jan 15 (15 lbs), **When** user adds both to pantry with respective purchase dates, **Then** system creates two pantry items linked to same variant
2. **Given** pantry has flour from Jan 1 (10 lbs) and Jan 15 (15 lbs), **When** user requests total quantity for "All-Purpose Flour" ingredient, **Then** system returns 25 lbs
3. **Given** pantry has flour from Jan 1 (10 lbs) and Jan 15 (15 lbs), **When** recipe consumes 12 lbs using FIFO, **Then** system consumes all 10 lbs from Jan 1 lot and 2 lbs from Jan 15 lot, returning breakdown showing consumption from both lots
4. **Given** pantry item with expiration date 7 days from now exists, **When** user queries items expiring within 14 days, **Then** system returns that item in the list
5. **Given** pantry items exist in "Main Pantry" and "Basement Storage" locations, **When** user filters by location, **Then** system returns only items matching specified location
6. **Given** insufficient inventory exists (need 20 lbs, have 15 lbs), **When** FIFO consumption attempted, **Then** system consumes all available inventory (15 lbs), returns consumed quantity and shortfall amount (5 lbs)

---

### User Story 4 - Purchase History & Price Trends (Priority: P4)

The application can record all purchase transactions with price, quantity, store, and date. Users can view price history for any variant and calculate average cost over time periods. The system supports detecting significant price changes for budget planning.

**Why this priority**: Enables cost trend analysis and budget forecasting. Lower priority than core inventory because users can still track inventory without price history, but price trends help users make informed purchasing decisions.

**Independent Test**: Can be tested by recording multiple purchases for a variant at different prices/dates, calculating average prices, and retrieving purchase history. Delivers value by providing cost insights without requiring full UI integration.

**Acceptance Scenarios**:

1. **Given** variant "King Arthur 25 lb flour" exists, **When** user records purchase of 25 lbs for $18.99 at "Costco" on Nov 1, **Then** system creates purchase record with all details and links to variant
2. **Given** variant has purchases: $18.99 (Nov 1), $19.99 (Nov 15), $17.99 (Nov 30), **When** user requests average price for last 60 days, **Then** system returns $18.99
3. **Given** variant has 10 purchases over 6 months, **When** user retrieves purchase history, **Then** system returns purchases sorted by date descending (most recent first)
4. **Given** variant's typical price is $18-20 and new purchase recorded at $25, **When** system calculates price change, **Then** system detects 25%+ increase from average
5. **Given** variant "King Arthur 25 lb flour" exists, **When** user requests most recent purchase, **Then** system returns latest purchase record for current price display

---

### Edge Cases

- **What happens when user creates ingredient with special characters in name?** System generates safe slug by removing/replacing special characters (e.g., "Confectioner's Sugar" → "confectioners_sugar")
- **What happens when FIFO consumption requires splitting a lot?** System calculates partial consumption, updates remaining quantity for that lot, and includes both full and partial lot consumptions in breakdown
- **What happens when user deletes an ingredient with variants and pantry items?** System prevents deletion and returns error listing all dependencies (variants, pantry items, recipes)
- **What happens when purchase record has zero or negative cost?** System validation rejects negative costs, allows zero for free/donated items with warning
- **What happens when pantry item quantity goes negative due to overconsumption?** System prevents negative quantities, stops consumption when inventory depleted, returns shortfall amount
- **What happens when user changes ingredient slug?** System prevents slug changes after creation to avoid breaking foreign key references
- **What happens when two variants have same UPC code?** System allows (same product from different suppliers may share UPC) but warns user of potential duplication
- **What happens when no preferred variant set and system needs current price?** System uses most recently purchased variant as fallback

## Requirements *(mandatory)*

### Functional Requirements

**IngredientService:**

- **FR-001**: System MUST create new ingredients with auto-generated slugs from names
- **FR-002**: System MUST enforce unique slugs (either prevent duplicates or auto-increment)
- **FR-003**: System MUST retrieve ingredients by slug or ID
- **FR-004**: System MUST support searching ingredients by partial name match (case-insensitive)
- **FR-005**: System MUST support filtering ingredients by category
- **FR-006**: System MUST update ingredient attributes while preserving slug and ID
- **FR-007**: System MUST prevent deletion of ingredients referenced by recipes, variants, or pantry items
- **FR-008**: System MUST provide dependency check method listing all entities referencing an ingredient

**VariantService:**

- **FR-009**: System MUST create variants linked to parent ingredient via slug
- **FR-010**: System MUST calculate display name from brand and package size
- **FR-011**: System MUST support marking one variant as preferred per ingredient (toggle off others)
- **FR-012**: System MUST retrieve all variants for an ingredient, sorted with preferred first
- **FR-013**: System MUST update variant attributes (brand, package, UPC, supplier, pricing)
- **FR-014**: System MUST prevent deletion of variants referenced by pantry items or purchases
- **FR-015**: System MUST support searching variants by UPC/GTIN code
- **FR-016**: System MUST validate package quantity is positive and purchase unit is valid

**PantryService:**

- **FR-017**: System MUST add pantry items linked to specific variant with quantity, purchase date, and location
- **FR-018**: System MUST calculate total quantity for an ingredient across all variants and locations
- **FR-019**: System MUST implement FIFO consumption that consumes oldest items first by purchase date
- **FR-020**: System MUST return consumption breakdown showing which lots were used and quantities
- **FR-021**: System MUST update pantry item quantities after consumption (or delete if fully consumed)
- **FR-022**: System MUST retrieve pantry items filtered by ingredient, variant, location, or expiration date
- **FR-023**: System MUST identify items expiring within specified days
- **FR-024**: System MUST prevent negative quantities (stop consumption when inventory depleted)
- **FR-025**: System MUST return shortfall amount when requested quantity exceeds available inventory

**PurchaseService:**

- **FR-026**: System MUST record purchases with variant, date, quantity, unit cost, store, and notes
- **FR-027**: System MUST retrieve purchase history for a variant sorted by date descending
- **FR-028**: System MUST calculate average purchase price over specified time period
- **FR-029**: System MUST retrieve most recent purchase for a variant
- **FR-030**: System MUST detect significant price changes (>20% from recent average)
- **FR-031**: System MUST validate purchase costs are non-negative
- **FR-032**: System MUST support filtering purchases by date range, store, or variant

### Key Entities

- **Ingredient**: Generic ingredient definition with name, slug, category, recipe_unit, density, and optional industry standard IDs (FoodOn, FDC, GTIN)
- **Variant**: Brand-specific product with ingredient_slug FK, brand, package_size, purchase_unit, purchase_quantity, preferred flag, UPC, supplier info
- **PantryItem**: Inventory instance with variant_id FK, quantity, purchase_date, expiration_date, location, notes
- **Purchase**: Transaction record with variant_id FK, purchase_date, quantity, unit_cost, store, total_cost, notes
- **UnitConversion**: Ingredient-specific conversion with ingredient_slug FK, from/to units and quantities

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four service modules implement specified methods with correct signatures and return types
- **SC-002**: Service layer test coverage exceeds 70% (measured by pytest-cov)
- **SC-003**: All CRUD operations complete in under 100ms for datasets with up to 1000 ingredients and 5000 pantry items
- **SC-004**: FIFO consumption correctly orders lots by purchase date in 100% of test cases
- **SC-005**: Dependency checking prevents orphaned data in 100% of deletion attempts
- **SC-006**: Services enforce all business rules (unique slugs, non-negative quantities, valid dates, preferred variant toggling)
- **SC-007**: All services use database sessions correctly (commit on success, rollback on error)
- **SC-008**: Services return clear error messages for validation failures (specify which field and why)
- **SC-009**: Average price calculation accuracy within 0.01 for all test scenarios
- **SC-010**: Pantry consumption shortfall calculations are accurate to 0.001 (3 decimal places)

### Quality Metrics

- **SC-011**: All service methods are stateless and UI-independent (no UI imports)
- **SC-012**: Services use explicit parameters rather than global state or config
- **SC-013**: All database queries use SQLAlchemy ORM (no raw SQL)
- **SC-014**: Services log errors with sufficient context for debugging
- **SC-015**: Each service has comprehensive unit tests covering happy path, edge cases, and error conditions

## Assumptions

1. Database models (Ingredient, Variant, PantryItem, Purchase) already exist and have correct schema (completed in Phase 4 Items 1-6)
2. Database session management utility (`session_scope()` context manager) is available and working
3. SQLAlchemy relationships are properly configured with appropriate lazy loading and cascades
4. Slug generation utility function exists or will be implemented as part of IngredientService
5. Date/time handling uses Python datetime objects in UTC
6. Quantity calculations use Python Decimal for precision
7. Unit validation is handled by existing `unit_converter.py` or will be added
8. Services will be tested with in-memory SQLite for speed
9. Recipe cost calculation will be updated separately to use these services (not in scope)
10. UI integration will occur in subsequent feature (not in scope)

## Dependencies

- **Upstream**: Phase 4 Items 1-6 (models, migration scripts) must be complete
- **Downstream**: UI tabs ("My Ingredients", "My Pantry") will consume these services
- **External**: None (no external APIs or third-party services)

## Out of Scope

The following are explicitly NOT included in this feature:

- UI components or CustomTkinter widgets
- Recipe cost calculation updates (separate feature)
- Event planning service updates (separate feature)
- Data migration execution (dry-run testing only)
- Import/export service updates for new services
- API endpoint creation (desktop app, no API needed)
- Mobile barcode scanning integration
- Supplier API connections
- Price alert notifications
- Batch update operations
- Data export to CSV/Excel
