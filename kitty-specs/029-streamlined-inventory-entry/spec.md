# Feature Specification: Streamlined Inventory Entry

**Feature Branch**: `029-streamlined-inventory-entry`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Transform inventory entry from tedious data entry into intelligent, flow-optimized experience with type-ahead filtering, recency intelligence, session memory, inline product creation, and smart defaults.

## Problem Statement

Current inventory entry workflow creates significant friction for the primary use case: adding 20+ items after a shopping trip. Users face:
- **Too many clicks**: 4-5 dropdown selections per item (100+ interactions for shopping trip)
- **Long lists**: Hundreds of ingredients requiring excessive scrolling/searching
- **No memory**: Must manually select same supplier 20 times for one shopping trip
- **Modal switching**: Product creation breaks workflow flow
- **Price recall difficulty**: No visibility into previous purchase prices

**Current state**: 15-20 minutes to enter 20 items after shopping.
**Target state**: 5 minutes for the same task.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rapid Multi-Item Entry (Priority: P1)

A user returns from a shopping trip with 20+ items from one supplier. They need to quickly add all items to inventory without repetitive selections or excessive navigation.

**Why this priority**: This is the primary use case blocking effective user testing. Without efficient bulk entry, realistic inventory data cannot be populated quickly enough to validate production and event workflows.

**Independent Test**: Can be fully tested by adding 10 items from one supplier in sequence and measuring time/clicks. Delivers immediate friction reduction.

**Acceptance Scenarios**:

1. **Given** the user has opened the Add Inventory dialog, **When** they select a supplier once, **Then** that supplier remains pre-selected (with visual indicator) for subsequent items until the app restarts.

2. **Given** the user has added an item with category "Baking", **When** they add another item, **Then** the category dropdown shows "Baking" pre-selected.

3. **Given** the user has entered all fields and clicks Add, **When** the operation succeeds, **Then** the dialog clears product-specific fields but retains category and supplier selections for the next entry.

---

### User Story 2 - Type-Ahead Filtering (Priority: P1)

A user needs to quickly find a specific ingredient or product from a long list without scrolling through hundreds of options.

**Why this priority**: Core enabler for speed improvement. Without filtering, users must scroll through 300+ ingredients and 150+ products repeatedly.

**Independent Test**: Can be tested by typing partial names and verifying filtered results appear instantly. Delivers immediate usability improvement.

**Acceptance Scenarios**:

1. **Given** the Category dropdown is focused, **When** user types "bak", **Then** the dropdown filters to show only categories containing "bak" (e.g., "Baking").

2. **Given** the Ingredient dropdown is enabled, **When** user types "ap", **Then** the dropdown shows ingredients containing "ap" with word-boundary matches first (e.g., "All-Purpose Flour" before "Maple Syrup").

3. **Given** the Product dropdown is enabled, **When** user types "gold", **Then** the dropdown filters to products containing "gold" within the selected ingredient.

4. **Given** the user has typed fewer than the minimum characters (1 for category, 2 for ingredient/product), **When** they view the dropdown, **Then** all items are shown (no filtering applied).

---

### User Story 3 - Recency Intelligence (Priority: P2)

A user frequently purchases the same products and wants quick access to their commonly-used items without searching.

**Why this priority**: Enhances efficiency for repeat users. Less critical than basic filtering but provides significant value for regular usage patterns.

**Independent Test**: Can be tested by verifying recently-added products appear at top of dropdowns with visual markers. Delivers convenience for repeat purchases.

**Acceptance Scenarios**:

1. **Given** a product was added to inventory within the last 30 days, **When** the user opens the Product dropdown for that ingredient, **Then** the product appears at the top with a visual marker (star).

2. **Given** a product was added 3+ times in the last 90 days but not in the last 30, **When** the user opens the Product dropdown, **Then** the product still appears at the top with a visual marker (frequency-based recency).

3. **Given** an ingredient was recently used, **When** the user opens the Ingredient dropdown for that category, **Then** the ingredient appears at the top of the list.

4. **Given** the dropdown contains both recent and non-recent items, **When** displayed, **Then** recent items appear first, followed by a separator, then alphabetically-sorted non-recent items.

---

### User Story 4 - Inline Product Creation (Priority: P2)

A user encounters a product they purchased that doesn't exist in the catalog. They need to add it without leaving the inventory entry workflow.

**Why this priority**: Eliminates modal-switching friction. Important for catalog expansion scenarios but secondary to core entry workflow.

**Independent Test**: Can be tested by selecting an ingredient with no products and creating one inline. Delivers uninterrupted workflow.

**Acceptance Scenarios**:

1. **Given** the user has selected an ingredient, **When** they click the "New Product" button, **Then** an inline form expands within the dialog (accordion-style) without opening a separate modal.

2. **Given** the inline form is expanded, **When** displayed, **Then** the ingredient field shows the current selection (read-only) and the package unit defaults based on ingredient category.

3. **Given** the user completes the inline form and clicks Create, **When** creation succeeds, **Then** the new product appears in the Product dropdown (selected) and the inline form collapses.

4. **Given** an ingredient has zero products, **When** the user selects it, **Then** a prominent "Create First Product" button is displayed with visual emphasis.

5. **Given** the user clicks Cancel on the inline form, **When** cancelled, **Then** the form collapses and the Product dropdown is re-enabled without changes.

---

### User Story 5 - Price Suggestions (Priority: P3)

A user wants to know what they paid previously for a product to inform their current entry and catch potential errors.

**Why this priority**: Helpful for data quality but not blocking for core workflow. Users can enter prices manually without suggestions.

**Independent Test**: Can be tested by selecting a product/supplier with purchase history and verifying price hint appears. Delivers data entry assistance.

**Acceptance Scenarios**:

1. **Given** a product/supplier combination has purchase history, **When** both are selected, **Then** the Price field pre-fills with the last purchase price and shows a hint "(last paid: $X.XX on MM/DD)".

2. **Given** a product has no purchase history at the selected supplier but has history at another supplier, **When** both are selected, **Then** the Price field pre-fills with the fallback price and shows "(last paid: $X.XX at [Other Supplier] on MM/DD)".

3. **Given** a product has no purchase history anywhere, **When** product and supplier are selected, **Then** the Price field is empty and shows "(no purchase history)".

---

### User Story 6 - Smart Defaults and Validation (Priority: P3)

A user benefits from intelligent defaults that reduce data entry and validation warnings that catch potential errors.

**Why this priority**: Quality-of-life improvements that enhance accuracy. Not blocking for core workflow.

**Independent Test**: Can be tested by creating products in different categories and verifying unit defaults. Delivers error prevention.

**Acceptance Scenarios**:

1. **Given** the user is creating a product for a "Baking" ingredient, **When** the inline form opens, **Then** the package unit defaults to "lb".

2. **Given** the user is creating a product for a "Chocolate" ingredient, **When** the inline form opens, **Then** the package unit defaults to "oz".

3. **Given** the user enters a price greater than $100, **When** they leave the price field, **Then** a confirmation dialog appears asking them to verify the high price.

4. **Given** the user enters a decimal quantity for a count-based product (e.g., "bags"), **When** they leave the quantity field, **Then** a warning appears noting that package quantities are usually whole numbers.

---

### Edge Cases

- What happens when the user switches categories mid-entry? Downstream dropdowns (ingredient, product) must clear and reset.
- What happens if recency queries fail? Silent failure with blank suggestions; log error for debugging.
- What happens if inline product creation fails? Error displays in inline form; form stays expanded for correction.
- What happens if the app crashes during session? Session memory is lost (in-memory only); documented as expected behavior.
- What happens with very long product/ingredient names? Type-ahead still works; dropdown may need horizontal scroll or truncation.

## Requirements *(mandatory)*

### Functional Requirements

**Type-Ahead Filtering:**
- **FR-001**: System MUST filter Category dropdown options in real-time as user types (1-character minimum threshold)
- **FR-002**: System MUST filter Ingredient dropdown options in real-time as user types (2-character minimum threshold, filtered by selected category)
- **FR-003**: System MUST filter Product dropdown options in real-time as user types (2-character minimum threshold, filtered by selected ingredient)
- **FR-004**: System MUST prioritize word-boundary matches over contains-only matches in type-ahead results (e.g., "ap" matches "AP Flour" before "Maple")
- **FR-005**: System MUST use case-insensitive matching for all type-ahead filtering

**Recency Intelligence:**
- **FR-006**: System MUST identify products as "recent" if added within the last 30 days OR added 3+ times in the last 90 days
- **FR-007**: System MUST display recent products at the top of the Product dropdown with a visual marker
- **FR-008**: System MUST display recent ingredients at the top of the Ingredient dropdown with a visual marker
- **FR-009**: System MUST include a separator between recent and non-recent items in dropdowns
- **FR-010**: System MUST sort recent items by most recent addition date (newest first)

**Session Memory:**
- **FR-011**: System MUST remember the last-used supplier for the duration of the application session
- **FR-012**: System MUST remember the last-selected category for the duration of the application session
- **FR-013**: System MUST pre-select remembered supplier and category with visual indicators when dialog opens
- **FR-014**: System MUST update session memory only on successful inventory addition (not on cancel/close)
- **FR-015**: System MUST clear session memory when the application restarts

**Inline Product Creation:**
- **FR-016**: System MUST provide an inline product creation form within the Add Inventory dialog (collapsible accordion)
- **FR-017**: System MUST pre-fill the ingredient field (read-only) from the current selection
- **FR-018**: System MUST pre-fill the preferred supplier from session memory (if set)
- **FR-019**: System MUST pre-fill the package unit with a smart default based on ingredient category
- **FR-020**: System MUST add newly created products to the Product dropdown and auto-select them
- **FR-021**: System MUST collapse the inline form and re-enable the Product dropdown on successful creation or cancel

**Smart Defaults:**
- **FR-022**: System MUST provide category-to-unit default mappings (e.g., Baking→lb, Chocolate→oz, Spices→oz)
- **FR-023**: System MUST allow users to override all default values

**Price Suggestions:**
- **FR-024**: System MUST query and display the last purchase price when product and supplier are selected
- **FR-025**: System MUST fall back to last purchase price from any supplier if none exists at selected supplier
- **FR-026**: System MUST display price hint showing date and (if fallback) supplier name

**Validation:**
- **FR-027**: System MUST warn users when entering a price greater than $100
- **FR-028**: System MUST warn users when entering decimal quantities for count-based package units
- **FR-029**: System MUST prevent negative prices

**Navigation:**
- **FR-030**: System MUST support Tab navigation through all fields in logical order
- **FR-031**: System MUST support Enter key to advance/select and Escape key to cancel/close

**Workflow Continuity:**
- **FR-032**: System MUST clear product-specific fields (ingredient, product, price, quantity) after successful Add
- **FR-033**: System MUST retain category and supplier selections after successful Add for next entry
- **FR-034**: System MUST focus the Ingredient dropdown after successful Add for rapid next-item entry

### Key Entities

- **SessionState**: In-memory singleton storing last_supplier_id and last_category for session duration. Not persisted to database.
- **RecencyData**: Query result identifying products/ingredients that meet temporal (30 days) or frequency (3+ uses in 90 days) thresholds.
- **CategoryUnitDefaults**: Configuration mapping ingredient categories to default package units (e.g., "Baking" → "lb").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add 20 inventory items from a single shopping trip in under 5 minutes (reduced from 15-20 minutes)
- **SC-002**: Users require at most 1 supplier selection per shopping trip (session memory working)
- **SC-003**: Type-ahead filtering reduces visible dropdown options to under 10 items within 2 typed characters
- **SC-004**: 90% of recently-used products appear in the top 5 dropdown positions
- **SC-005**: Users can create a new product inline without leaving the Add Inventory dialog
- **SC-006**: Price suggestion accuracy: 80%+ of suggested prices match user expectations (within $1 of manual entry)
- **SC-007**: All existing inventory entry tests continue to pass after enhancement
- **SC-008**: Tab and Enter/Escape keyboard navigation works for complete dialog traversal

## Dependencies

- **Feature 027** (Product Catalog Management): Provides Product and Supplier entities - COMPLETE
- **Feature 028** (Purchase Tracking): Provides Purchase entity and price history queries - COMPLETE

## Design Reference

Detailed technical design, UI wireframes, and implementation guidance available in:
`docs/design/F029_streamlined_inventory_entry.md`

Note: The design document contains illustrative code samples and technical details. The spec-kitty planning phase should validate and rationalize the technical approach based on current codebase patterns.
