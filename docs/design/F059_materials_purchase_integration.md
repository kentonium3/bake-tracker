# F059: Materials Purchase Mode Integration & Workflows

**Version**: 1.0
**Priority**: HIGH
**Type**: UI Enhancement + Workflow Implementation

---

## Executive Summary

Materials v3.0 foundation (F058) provides FIFO infrastructure, but materials cannot be purchased or tracked through UI. Purchase mode has no materials workflows, and inventory cannot be viewed or adjusted.

Current gaps:
- ❌ No materials purchasing UI in Purchase mode
- ❌ No inventory display for MaterialInventoryItem lots
- ❌ No manual inventory adjustment interface
- ❌ No CLI-assisted provisional product workflow
- ❌ MaterialUnit UI doesn't show inherited unit types

This spec implements Purchase mode integration by adding materials purchasing form, MaterialInventoryItem lot display, manual adjustment dialogs, CLI provisional workflow, and MaterialUnit UI enhancements.

---

## Problem Statement

**Current State (After F058):**
```
Materials Domain - Backend
├─ ✅ MaterialInventoryItem table exists (F058)
├─ ✅ MaterialInventoryService with FIFO primitives (F058)
├─ ✅ Purchase creates MaterialInventoryItem (F058)
└─ ✅ Unit conversion working (F058)

Materials Domain - UI
├─ ✅ Catalog > Materials Hierarchy (exists, unchanged)
├─ ✅ Catalog > Materials (shows definitions only, F058 updated)
├─ ❌ Purchase mode: NO materials workflows
├─ ❌ Purchase > Inventory: NO materials display
├─ ❌ Manual adjustments: NO UI
├─ ❌ MaterialUnit UI: Doesn't show inherited unit type
└─ ❌ CLI workflow: NO provisional product support

User Problems:
❌ Cannot purchase materials through UI
❌ Cannot view MaterialInventoryItem lots
❌ Cannot adjust material inventory manually
❌ CLI mobile purchases blocked (no provisional products)
❌ MaterialUnit creation confusing (unit type inheritance unclear)
```

**Target State (After F059):**
```
Materials Domain - Complete
├─ ✅ Backend infrastructure (F058)
├─ ✅ Purchase > Add Purchase: Materials form working
│   ├─ Product type selector (Food/Material)
│   ├─ MaterialProduct dropdown
│   ├─ Package quantity fields
│   ├─ Unit cost calculated and displayed
│   └─ Creates MaterialPurchase + MaterialInventoryItem
├─ ✅ Purchase > Inventory: MaterialInventoryItem lots displayed
│   ├─ display order (newest first for visibility)
│   ├─ Product, Date, Qty columns
│   ├─ Filter/sort capabilities
│   └─ Manual adjustment button
├─ ✅ Manual adjustment dialog working
│   ├─ Count-based for "each" materials
│   └─ Percentage-based for variable materials
├─ ✅ CLI provisional workflow functional
│   ├─ Creates MaterialProduct with is_provisional=True
│   ├─ Inventory available immediately
│   └─ Catalog enrichment later
└─ ✅ MaterialUnit UI shows inherited unit type clearly

User Workflows Complete:
✅ Can purchase materials via UI
✅ Can view inventory lots
✅ Can adjust inventory manually
✅ Can use CLI for mobile purchases
✅ Understands MaterialUnit quantity meaning
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Existing Purchase UI**
   - Find current Purchase > Add Purchase form
   - Study form layout and field structure
   - Note validation patterns
   - Understand supplier dropdown integration
   - **This is the base form to extend**

2. **Inventory Display Patterns**
   - Find existing inventory list views
   - Study column layouts
   - Note filter/sort implementations
   - Understand date formatting
   - Study FIFO order display (if ingredients show this)

3. **Dialog Patterns**
   - Find existing edit/adjustment dialogs
   - Study CTkToplevel usage
   - Note button layouts (Save/Cancel)
   - Understand validation feedback patterns

4. **Form Input Patterns**
   - Find CTkEntry, CTkComboBox usage
   - Study placeholder text patterns
   - Note label conventions
   - Understand calculated field display (read-only entry widgets)

5. **MaterialUnit Existing UI**
   - Find MaterialUnit create/edit form
   - Study current field layout
   - Note where unit type should be displayed
   - Understand quantity field validation

---

## Requirements Reference

This specification implements:
- **REQ-M-013**: Purchase workflow (manual UI + CLI)
- **REQ-M-027 through REQ-M-029**: Inventory management UI
- **REQ-M-035**: Materials purchasing (PURCHASE Mode)
- **REQ-M-036**: Materials inventory (PURCHASE Mode)
- **REQ-M-039**: Material unit type display

From: `docs/requirements/req_materials.md` (v3.0)

---

## Functional Requirements

### FR-1: Add Materials to Purchase Form

**What it must do:**
- Purchase > Add Purchase form:
  - Add product type selector: Radio buttons "○ Food  ○ Material"
  - When Material selected:
    - Show MaterialProduct dropdown (replaces Product dropdown)
    - Show package quantity input fields:
      - "Packages purchased" (integer, e.g., "4")
      - "Package unit count" (decimal, e.g., "25.0")
      - "Package unit" (dropdown: feet, inches, cm, meters, yards, etc.)
    - Show total cost input field (decimal)
    - Show supplier dropdown (optional, same as food)
    - Show purchase date (same as food)
    - Display calculated fields (read-only):
      - "Total units (base)" - shows quantity in base units (e.g., "100 bags" or "3048 cm")
      - "Unit cost" - shows cost per base unit (e.g., "$0.40/bag" or "$0.032/cm")
  - When Food selected: Existing food purchase form (unchanged)
- Form switches fields dynamically based on product type radio selection
- Validation: All required fields must be filled before submit enabled

**Pattern reference:** Study existing Purchase form, extend with conditional field display based on product type

**UI Requirements:**
- Product type selector at top of form (always visible)
- Field groups visually separated (package info group, cost group)
- Calculated fields clearly marked as read-only (different background color)
- Unit cost updates in real-time as user types (calculation: total_cost ÷ total_units)

**Success criteria:**
- [ ] Product type radio buttons working
- [ ] Form fields switch correctly based on selection
- [ ] MaterialProduct dropdown populated correctly
- [ ] Package quantity fields accept correct input types
- [ ] Package unit dropdown has all supported units
- [ ] Total units calculated correctly (using F058 unit conversion)
- [ ] Unit cost calculated correctly and displayed
- [ ] Submit creates MaterialPurchase + MaterialInventoryItem (via F058 services)
- [ ] Validation prevents submission with incomplete data

---

### FR-2: Create Purchase > Inventory Materials View

**What it must do:**
- Purchase > Inventory view:
  - Add tab or section: "Materials" (parallel to food inventory if tabbed)
  - Display MaterialInventoryItem lots:
    - Columns:
      - Product Name (MaterialProduct.name)
      - Brand (MaterialProduct.brand)
      - Purchased Date (purchased_at, formatted)
      - Qty Purchased (quantity_purchased + unit, e.g., "100 bags" or "3048 cm")
      - Qty Remaining (quantity_remaining + unit, same format)
      - Cost/Unit (cost_per_unit, formatted as currency)
      - Total Value (quantity_remaining × cost_per_unit, formatted as currency)
      - Actions (Manual Adjust button per row)
    - Sort: By purchased_at DESC (newest first for visibility)
    - Visual indicator: Recent purchases shown first or marked
    - Empty state: "No material inventory items. Purchase materials to get started."
  - Filters (above table):
    - MaterialProduct dropdown (filter by product, "All Products" default)
    - Date range picker (from/to dates)
    - "Show depleted" checkbox (include items where quantity_remaining = 0)
  - Action buttons:
    - "Export Inventory Snapshot" (exports to JSON for backup/analysis)

**Pattern reference:** Study existing inventory list views, copy column layout pattern

**UI Requirements:**
- Table layout clean and readable
- Display newest purchases first (DESC) for user convenience - this is display order, not consumption order
- Note: FIFO consumption (oldest first) happens via F058 services when materials are used
- Items near depletion (low quantity_remaining) highlighted for attention
- Depleted items (quantity_remaining = 0) shown in gray or hidden by default
- Filters work instantly (no submit button needed)
- Date formatting consistent with rest of app (YYYY-MM-DD or locale format)

**Success criteria:**
- [ ] Purchase > Inventory shows materials section/tab
- [ ] MaterialInventoryItem lots displayed correctly
- [ ] Columns show correct data with proper formatting
- [ ] Sort by purchased_at DESC working (newest purchases shown first)
- [ ] Items near depletion indicated
- [ ] Filters work correctly
- [ ] "Show depleted" checkbox filters correctly
- [ ] Empty state displays when no inventory
- [ ] Manual Adjust button per row present (functionality in FR-3)

---

### FR-3: Implement Manual Inventory Adjustment Dialog

**What it must do:**
- "Manual Adjust" button opens dialog:
  - Dialog title: "Adjust Inventory: [Product Name]"
  - Display current state:
    - "Current remaining: [quantity_remaining] [unit]"
    - "Purchased: [purchased_at]"
    - "Original quantity: [quantity_purchased] [unit]"
  - Adjustment interface depends on Material.base_unit_type:
    
    **For "each" materials** (discrete items like bags, boxes):
    - Radio buttons: "○ Add  ○ Subtract  ○ Set to"
    - Quantity input (integer)
    - Preview: "New remaining: [calculated] [unit]"
    - Creates NEW MaterialInventoryItem with adjustment quantity
    
    **For "linear_cm" or "square_cm" materials** (variable like ribbon, tissue):
    - Label: "Percentage remaining"
    - Percentage slider or input (0-100%)
    - Preview: "Current: [current] cm → New: [calculated] cm"
    - Updates EXISTING MaterialInventoryItem.quantity_remaining
  
  - Notes field (optional, records reason for adjustment)
  - Buttons: [Save] [Cancel]

**Pattern reference:** Study existing edit dialogs, copy layout and button patterns

**Adjustment Logic:**
- **Each materials**: Create new MaterialInventoryItem with adjustment_type flag
- **Variable materials**: Update quantity_remaining directly (not a new item)
- Validation: New quantity_remaining cannot be negative
- Validation: Percentage must be 0-100

**Success criteria:**
- [ ] Manual Adjust button opens dialog
- [ ] Dialog displays current inventory state
- [ ] "Each" materials show Add/Subtract/Set interface
- [ ] "Variable" materials show percentage interface
- [ ] Preview calculation correct
- [ ] Save button creates adjustment or updates inventory
- [ ] Notes field stored if provided
- [ ] Validation prevents negative quantities
- [ ] Cancel button closes without changes
- [ ] Inventory table updates after adjustment

---

### FR-4: Implement CLI Provisional Product Workflow

**What it must do:**
- When MaterialPurchase created via API/CLI:
  - If MaterialProduct exists (matched by slug or name): Use existing
  - If MaterialProduct NOT found:
    - Create MaterialProduct with:
      - name (from CLI input)
      - material_id (user provides or system prompts)
      - package_quantity (from CLI input)
      - package_unit (from CLI input)
      - quantity_in_base_units (calculated using F058 conversion)
      - is_provisional = True (marker flag)
      - brand, SKU, supplier, notes = NULL (filled later)
    - Display: "Created provisional product: [name]"
  - Create MaterialPurchase normally
  - Create MaterialInventoryItem normally (via F058 service)
  - Inventory immediately available for consumption

**Pattern reference:** Study CLI purchase patterns for food (if exists), or create new CLI entry point

**CLI Workflow Example:**
```
User (at store): "bt purchase add material --name 'Snowflake Bag' --qty 100 --cost 25.00"
System: "Material not found. Create provisional? (y/n)"
User: "y"
System: "Material type? (1=ribbon, 2=bags, 3=boxes, etc.)"
User: "2"
System: "Created provisional MaterialProduct: Snowflake Bag (100 units)"
System: "Purchase recorded. Inventory available."
```

**Success criteria:**
- [ ] CLI can create provisional MaterialProduct
- [ ] is_provisional flag set correctly
- [ ] MaterialInventoryItem created (inventory available immediately)
- [ ] Provisional products visible in catalog with indicator

---

### FR-5: Implement Provisional Product Enrichment

**What it must do:**
- Catalog > Materials > Material Products view:
  - Provisional products show indicator: "⚠️ Needs enrichment" badge or icon
  - Edit button available (same as non-provisional products)
  - Edit dialog shows all fields (including brand, SKU, supplier)
  - Save updates:
    - All provided fields
    - Sets is_provisional = False when complete metadata added
  - Historical MaterialPurchase and MaterialInventoryItem unchanged (linked by ID)

**Pattern reference:** Study existing catalog edit dialogs, add provisional indicator only

**UI Requirements:**
- Provisional indicator clearly visible (color or icon)
- Edit form same as regular products (no special handling needed)
- User understands provisional = "incomplete catalog info, but inventory working"

**Success criteria:**
- [ ] Provisional products display with indicator
- [ ] Edit dialog accessible for provisional products
- [ ] Save updates all fields including is_provisional
- [ ] Historical data preserved (MaterialPurchase, MaterialInventoryItem unchanged)
- [ ] Enriched products no longer show provisional indicator

---

### FR-6: Enhance MaterialUnit UI with Inherited Unit Type Display

**What it must do:**
- MaterialUnit create/edit dialog:
  - When Material selected:
    - Display inherited unit type clearly:
      - Label: "Unit type: [base_unit_type] (inherited from [Material.name])"
      - Shown as read-only text or badge, NOT editable
    - Update quantity field label dynamically:
      - "Quantity per unit (in [base_unit_type]):"
      - Example: "Quantity per unit (in linear_cm):"
    - Add preview text below quantity:
      - "This unit will consume [quantity] [base_unit_type] of [Material.name]"
      - Example: "This unit will consume 15 cm of Red Ribbon"
  - For "each" materials:
    - Quantity field read-only, always shows "1"
    - Preview: "This unit will consume 1 [Material.name]"

**Pattern reference:** Study existing MaterialUnit dialog, add unit type display section

**UI Requirements:**
- Unit type inheritance visually clear (not buried in small text)
- Preview text helps user understand what they're defining
- For "each" materials, quantity=1 is obvious and unchangeable

**Success criteria:**
- [ ] Material dropdown populated correctly
- [ ] Unit type displays when Material selected
- [ ] "Inherited from" text clear
- [ ] Quantity field label dynamic (shows unit type)
- [ ] Preview text calculates correctly
- [ ] For "each" materials, quantity locked to 1
- [ ] For variable materials, quantity accepts decimal input

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Assembly integration (separate feature - F060 or later)
- ❌ FinishedGood composition with MaterialUnits (separate feature)
- ❌ Material assignment interface at assembly time (separate feature)
- ❌ Event planning cost calculations (separate feature)
- ❌ MaterialInventoryItem lot merging/splitting (not needed)
- ❌ Advanced inventory analytics/reporting (future enhancement)
- ❌ Low stock alerts (future enhancement)
- ❌ Barcode scanning for purchases (future enhancement)

---

## Success Criteria

**Complete when:**

### Purchase Workflows
- [ ] Product type selector (Food/Material) working
- [ ] Material purchase form functional (all fields)
- [ ] Package quantity fields working
- [ ] Unit cost calculation real-time
- [ ] Submit creates MaterialPurchase + MaterialInventoryItem
- [ ] Validation prevents incomplete submissions

### Inventory Display
- [ ] Purchase > Inventory shows materials section
- [ ] MaterialInventoryItem lots displayed correctly
- [ ] FIFO order clear (newest first)
- [ ] Filters working (product, date range, depleted)
- [ ] Export inventory snapshot working

### Manual Adjustments
- [ ] Manual Adjust dialog opens from inventory row
- [ ] "Each" materials: Add/Subtract/Set interface working
- [ ] "Variable" materials: Percentage interface working
- [ ] Preview calculations correct
- [ ] Save updates inventory correctly
- [ ] Notes stored if provided

### CLI Workflow
- [ ] Provisional product creation working
- [ ] is_provisional flag set correctly
- [ ] Inventory available immediately after CLI purchase
- [ ] Provisional indicator shows in catalog

### Catalog Enrichment
- [ ] Provisional products identifiable in catalog
- [ ] Edit dialog accessible for provisional products
- [ ] Save enriches product and removes provisional flag
- [ ] Historical data preserved

### MaterialUnit UI
- [ ] Unit type displayed clearly when Material selected
- [ ] "Inherited from" text present
- [ ] Quantity label dynamic (shows unit type)
- [ ] Preview text calculates correctly
- [ ] "Each" materials quantity locked to 1

### Quality
- [ ] UI patterns consistent with existing app
- [ ] Validation feedback clear and helpful
- [ ] Error handling graceful (network/database errors)
- [ ] Empty states display appropriate messages
- [ ] Loading states shown during async operations

---

## Architecture Principles

### Purchase Mode Organization

**UI Structure:**
- Purchase > Add Purchase: One form, switches fields based on product type
- Purchase > Inventory: Separate sections/tabs for Food and Materials
- Consistent navigation patterns across food and materials

**Rationale:** Users understand one purchase workflow, applies to both domains

### Conditional Field Display

**Form Behavior:**
- Product type selector always visible at top
- Field groups show/hide based on selection
- No page reload needed (dynamic UI update)

**Rationale:** Single form reduces navigation, clear context switching

### Provisional Product Philosophy

**Purpose:**
- Enable CLI mobile purchases (speed at store)
- Inventory tracking immediate (no blocking)
- Catalog enrichment asynchronous (convenience)

**Workflow:**
- Purchase → Provisional product created → Inventory available → Enrich later at desk

**Rationale:** Mobile workflow requires minimal data entry; complete metadata added when convenient

---

## Constitutional Compliance

✅ **Principle IV (User Experience)**
- Purchase workflows intuitive (parallel to food purchasing)
- Inventory display clear (FIFO order obvious)
- Provisional products don't block usage (inventory immediately available)

✅ **Principle V (Layered Architecture)**
- UI calls F058 services (proper separation)
- Purchase form → MaterialInventoryService → creates inventory
- Manual adjustments → MaterialInventoryService → updates inventory

✅ **Principle VI (Parallel Architecture)**
- Materials purchase mirrors food purchase (same form, conditional fields)
- Materials inventory mirrors food inventory (same columns, same filters)
- Patterns consistent across domains

---

## Risk Considerations

**Risk: Form complexity with conditional fields**
- Product type switching might confuse users if not visually clear
- Too many fields visible at once could overwhelm
- **Mitigation approach**: Clear visual grouping, hide irrelevant fields completely, product type selector prominent

**Risk: FIFO order not obvious to users**
- Users might not understand why newest items appear first
- Sorting by date DESC natural but requires explanation
- **Mitigation approach**: Visual indicators (highlighting newest), tooltip explaining FIFO, consistent with food inventory if that also shows FIFO

**Risk: Provisional product workflow confusion**
- Users might not understand provisional vs complete products
- Provisional indicator might be missed
- **Mitigation approach**: Clear indicator (icon + text), edit prompt when viewing provisional products, documentation/help text

**Risk: Unit type inheritance confusion**
- MaterialUnit quantity meaning unclear without context
- Users might not understand inherited unit type concept
- **Mitigation approach**: Prominent unit type display, preview text showing concrete example, "inherited from" text makes relationship explicit

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study existing Purchase form → extend with product type conditional fields
- Study existing inventory tables → copy for MaterialInventoryItem display
- Study existing edit dialogs → copy for manual adjustment dialog
- Study form validation patterns → apply to materials purchase form

**Key Patterns to Copy:**
- Purchase form structure → Materials purchase section (same form, new fields)
- Inventory table columns → MaterialInventoryItem columns (parallel structure)
- Dialog layout → Manual adjustment dialog (same button positions, validation)
- Dropdown population → MaterialProduct dropdown (same pattern as Product dropdown)

**Focus Areas:**
- Conditional field display (show/hide based on product type selection)
- Real-time calculation display (unit cost updates as user types)
- FIFO order visualization (newest items clearly distinguished)
- Provisional product workflow (CLI → provisional creation → catalog enrichment)
- Unit type inheritance clarity (MaterialUnit UI shows inherited type)

**UI Layout Guidance:**
```
Purchase > Add Purchase:
┌─────────────────────────────────┐
│ Product Type: ○ Food ○ Material │ ← Always visible
├─────────────────────────────────┤
│ [Material-specific fields]      │ ← Show when Material selected
│ - MaterialProduct dropdown      │
│ - Package quantity fields       │
│ - Total cost                    │
│ - Calculated: Total units       │ ← Read-only, auto-calculated
│ - Calculated: Unit cost         │ ← Read-only, auto-calculated
├─────────────────────────────────┤
│ [Common fields]                 │
│ - Supplier dropdown (optional)  │
│ - Purchase date                 │
├─────────────────────────────────┤
│         [Save] [Cancel]         │
└─────────────────────────────────┘

Purchase > Inventory > Materials:
┌──────────────────────────────────────────────────┐
│ Filters: [Product ▼] [Date From] [Date To]      │
│          ☐ Show depleted items                   │
├──────────────────────────────────────────────────┤
│ Product     │ Date       │ Purchased │ Remaining │
│ Snowflake   │ 2026-01-15 │ 100 bags  │ 50 bags   │
│ Red Ribbon  │ 2026-01-10 │ 3048 cm   │ 1200 cm   │
│             ...newest first (FIFO order)          │
└──────────────────────────────────────────────────┘
```

**Adjustment Dialog Types:**
```
Each Materials (discrete items):
- Radio: ○ Add ○ Subtract ○ Set to
- Input: [50] bags
- Preview: "Current: 100 → New: 150"

Variable Materials (ribbon, tissue):
- Label: "Percentage remaining"
- Input: [50] %
- Preview: "Current: 3048 cm → New: 1524 cm"
```

**Provisional Product Workflow:**
```
1. CLI Purchase:
   bt purchase add material --name "Snowflake Bag" --qty 100 --cost 25

2. System Creates:
   MaterialProduct (is_provisional=True, minimal metadata)
   MaterialPurchase
   MaterialInventoryItem

3. Later in Catalog:
   User sees: "Snowflake Bag ⚠️ Needs enrichment"
   User clicks Edit
   User adds: brand="Snowflake", SKU="SB-100", supplier="Party Supply Co"
   User saves: is_provisional=False

4. Result:
   Complete MaterialProduct (no more warning)
   Historical purchases/inventory unchanged
```

---

**END OF SPECIFICATION**
