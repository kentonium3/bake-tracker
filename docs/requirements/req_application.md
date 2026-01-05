# Seasonal Baking Tracker - Requirements Document v1.3

## Executive Summary

A desktop application for managing holiday baking inventory, recipes, and gift package planning. Built with Python, SQLite, and CustomTkinter for a single Windows user with cross-platform compatibility.

**Technology Stack:** Python 3.10+, SQLite, CustomTkinter, SQLAlchemy, Pandas

---

## 1. Application Requirements

### 1.1 Data Model Requirements

**Ingredients** (Refactored in v0.4.0 - Hierarchical Catalog)
- **Three-tier hierarchy**: L0 (category), L1 (subcategory), L2 (specific ingredient)
- Example: Flour (L0) → All-Purpose Flour (L1) → King Arthur AP Flour (L2)
- Unique identifier (UUID), name, slug (auto-generated)
- Recipe unit type (canonical unit for recipes to reference)
- Density (g/ml) for volume-weight conversions (optional)
- Shelf life (days) for expiration tracking
- Optional: industry standard identifiers (FoodOn, FDC, FoodEx2, LanguaL)
- Unit types: oz, lb, g, kg, tsp, tbsp, cup, ml, l, count/each

**Products** (v0.4.0 - Purchasable Items)
- Links to L2 Ingredient (specific ingredient)
- Auto-propagates to L0/L1 (cascading hierarchy)
- Brand, package size, UPC/GTIN barcode
- Purchase unit type and quantity (e.g., "bag", 25 lb)
- Supplier/source information
- Shelf life override (optional, inherits from ingredient if not set)
- Preferred product flag (for cost calculation fallback)
- Density override (optional, inherits from ingredient if not set)

**Purchases** (v0.4.0 - Inventory with FIFO Support)
- Links to Product (specific brand/package purchased)
- Purchase quantity, unit, price, date
- Auto-propagates ingredient L0/L1/L2 from product
- Shelf life override (optional, inherits from product/ingredient)
- Computed expiration date (purchase_date + effective_shelf_life)
- Vendor (optional), notes
- Inventory tracking: remaining quantity (depletes via FIFO)
- Depletion history (audit trail)

**Materials** (New - Packaging/Assembly Supplies)
- Unique identifier, name, category (e.g., "Cellophane Bags", "Ribbon", "Boxes")
- Purchase unit type, current quantity
- Unit cost (per purchase unit)
- Shelf life (days, optional)
- Last updated date, purchase history
- Tracked like ingredients but associated with bundles (not recipes)
- Examples: cellophane bags, ribbon, plastic wrap, boxes, tags, stickers

**Inventory Snapshots** (Updated for Materials)
- Snapshot date, description
- Copy of ingredient quantities (aggregated by ingredient across purchases)
- Copy of material quantities
- References which events use this snapshot
- Auto-create on first event planning for a period

**Recipes** (Updated - Template Architecture)
- **Recipe Templates**: Base recipes with variants
- Unique identifier, name, category, source, date added, last modified
- **Base ingredients**: Common across all variants
- **Yield options**: Multiple yield levels (e.g., 24, 48, 96 cookies)
  - Each with batch multiplier for scaling ingredients
- **Recipe variants**: Ingredient/finishing variations
  - Each variant produces a specific FinishedUnit
  - Variant ingredients (additions, substitutions)
- References L2 Ingredients (not specific Products) for brand flexibility
- Cost calculation: FIFO from purchases or preferred product pricing

**Finished Units** (Updated - Atomic Items)
- Individual baked items (1 cookie, 1 cake, 1 truffle)
- Links to RecipeVariant (what recipe produces this)
- Display name, description
- Cost derived from recipe (FIFO costing)
- Inventory tracking (Phase 3 - cross-event)
- Can be delivered as-is (bulk mode) OR assembled into Bundles

**Bundles** (Updated - Consumer Packages)
- Consumer-facing packages (bag of 6 cookies, box of 12 brownies)
- List of FinishedUnits with quantities per bundle
- List of materials with quantities per bundle (e.g., "1 cellophane bag", "2 ft ribbon")
- Packaging material (optional, can be deferred until assembly)
- Calculated cost: FinishedUnits + materials
- Inventory tracking (Phase 3 - cross-event)
- Assembly completion tracking (event-scoped Phase 2)

**Packages** (Logistics Containers)
- Shipping/delivery containers (gift basket, shipping box)
- List of Bundles and/or FinishedUnits with quantities
- Packaging material (optional)
- Recipient assignment (optional)
- Calculated cost from components
- Template flag (reusable across events)

**Recipients**
- Name, household name/identifier, notes
- Delivery history: event, year, package sent, date delivered, actual cost

**Events** (Updated - Planning Architecture)
- Name (Christmas 2025, Easter 2026, etc.), year, date range
- **Output mode**: BULK_COUNT, BUNDLED, PACKAGED, etc.
- Requirements based on mode:
  - BULK_COUNT: FinishedUnit quantities (trays, baskets)
  - BUNDLED: Bundle quantities (gift bags, boxes)
  - PACKAGED: Package quantities (multi-bundle containers)
- References inventory snapshot (ingredients + materials)
- Planning status: planning, in-progress, completed
- **Production plan** (auto-generated):
  - Recipe batches needed (by recipe template)
  - FinishedUnit quantities (by variant)
  - Assembly requirements (bundles to make)
- **Shopping list** (auto-generated):
  - Ingredient gaps (need vs snapshot)
  - Material gaps (need vs snapshot)

**Edit History (for Undo)**
- Table/entity modified, record ID, field, old value, new value, timestamp
- Keep last 8 edits per entity type in memory
- User can undo sequentially

### 1.2 Functional Requirements

**FR1: Inventory Management** (Updated for Hierarchical Architecture)
- **Ingredient Catalog**: Manage hierarchical ingredients
  - Three-tier hierarchy: L0 → L1 → L2
  - Cascading selectors in UI (pick L0, then L1, then L2)
  - Only L2 ingredients can be assigned to products
  - Auto-propagation to L0/L1 when product selected
  - Shelf life at all levels (L2 overrides L1, L1 overrides L0)
  - Density at all levels (same override pattern)
- **Product Catalog**: Manage purchasable items
  - Link to L2 ingredient (required)
  - Brand, package size, UPC, supplier
  - Preferred product flag per ingredient
  - Shelf life and density overrides
- **Purchase Tracking**: Record ingredient purchases
  - Link to product, quantity, price, date, vendor
  - Auto-create inventory item with FIFO tracking
  - Shelf life override at purchase level
  - Computed expiration date (F041)
  - Freshness indicators: FRESH, EXPIRING_SOON, EXPIRED
- **Materials Management**: Track packaging/assembly supplies
  - Add/edit/delete materials with category, unit, quantity
  - Unit cost tracking
  - Shelf life (optional)
  - Search and filter by category, name

**FR2: Unit Conversion System**
- Maintain conversion tables for standard units
- Support density-based conversions (ingredient-specific)
- Three-tier density inheritance: Purchase > Product > Ingredient
- Display helper showing conversions
- Validation of unit compatibility

**FR3: Recipe Management** (Updated - Template Architecture)
- **Recipe Templates**:
  - Base ingredients (common across variants)
  - Multiple yield options (e.g., 24, 48, 96 cookies)
  - Batch multipliers per yield option
- **Recipe Variants**:
  - Link variant to FinishedUnit it produces
  - Variant-specific ingredients (additions, substitutions)
  - Proportional ingredient calculation
- **Cost Calculation**:
  - FIFO costing from purchases
  - Fallback to preferred product pricing
  - Variant ingredients scaled by proportion
- Filter/search by category, name, ingredients
- Show all recipes using a specific ingredient

**FR4: Bundle & Package Management** (Updated for Materials & Assembly)
- **Bundles**:
  - Define FinishedUnit contents with quantities
  - Add materials with quantities (cellophane bags, ribbon, etc.)
  - Packaging material selection (can defer until assembly)
  - Auto-calculate cost (FinishedUnits + materials)
  - Assembly completion tracking (Phase 2 event-scoped)
- **Packages**:
  - Define Bundle/FinishedUnit contents
  - Auto-calculate costs
  - Template flag for reuse
  - Recipient assignment
- Clone existing bundles/packages
- Validation preventing circular references

**FR5: Event Planning** (Updated - Automatic Batch Calculation)
- **Event Setup**:
  - Create event with name, year, date range, output mode
  - Select inventory snapshot (ingredients + materials)
- **Requirements Definition**:
  - Based on output mode (Bundles, Packages, or FinishedUnits)
  - Assign quantities needed
- **Automatic Production Planning**:
  - **Explosion**: Bundle/Package → FinishedUnit quantities
  - **Recipe Grouping**: Group FinishedUnits by recipe template
  - **Batch Calculation**: Optimal yield option per recipe
    - Minimize waste (extra units)
    - Minimize batches (fewer production runs)
  - **Variant Allocation**: Proportional distribution within batches
  - **Ingredient Aggregation**: Base + variant ingredients
- **Inventory Gap Analysis**:
  - Compare needs vs snapshot (ingredients)
  - Compare needs vs snapshot (materials)
  - Generate shopping lists (separate for ingredients/materials)
  - Color coding: sufficient (green), low (yellow), insufficient (red)
- **Assembly Feasibility** (Phase 2 Event-Scoped):
  - After production, validate enough FinishedUnits for assembly
  - Display feasibility status: ✅/⚠️/❌
  - Assembly completion checklist (minimal UI Phase 2)
- Export shopping lists to CSV

**FR6: Production Tracking** (Updated for Checkoff Workflow)
- **Production Execution**:
  - Execute production runs (create FinishedUnits)
  - FIFO depletion of ingredient inventory
  - Record actual yield vs planned
  - Update event production status
- **Assembly Tracking** (Phase 2 Event-Scoped):
  - Display bundles needed for event
  - Check off assembled bundles
  - Show progress (assembled vs remaining)
  - Validate components available
  - Record assembly confirmation (no inventory transactions Phase 2)
- **Delivery Tracking**:
  - Mark packages delivered to recipients
  - Track actual costs vs estimates
- Update event status (planning → in-progress → completed)

**FR7: Reporting & Analysis** (Updated for Materials)
- **Dashboard**: Current event summary, upcoming tasks, production progress
- **Inventory Report**: Ingredients + materials stock, value, low items
- **Event Summary**: Planned vs actual, costs (ingredients + materials)
- **Year-over-Year Comparison**: Costs, quantities, recipients
- **Recipient History**: Packages received by event/year
- **Cost Analysis**: By package, recipient, FinishedUnit, ingredient, material
- **Shopping List**: Exportable by category (ingredients and materials)
- **Materials Usage Report**: Materials per event, cost per bundle
- All reports viewable on-screen with CSV export

**FR8: Navigation & UI (CustomTkinter)**
- Main window with tabbed interface or sidebar navigation
- Sections: Dashboard, Ingredients, Purchases, Materials, Recipes, Bundles, Packages, Recipients, Events, Reports
- Hierarchical ingredient selectors (L0 → L1 → L2 cascading)
- Consistent styling using CustomTkinter widgets
- Forms with validation and clear error messages
- Confirmation dialogs for deletions
- Search/filter bars in list views
- Sortable table/list views
- Status bar showing last save time, current event

### 1.3 Non-Functional Requirements

**NFR1: Performance**
- UI response time < 200ms for typical operations
- Batch calculation < 500ms for events with 10+ recipes
- Ingredient aggregation < 200ms
- Assembly feasibility check < 100ms
- Support for 500+ ingredients, 100+ recipes, 50+ recipients, 10+ years of events
- Database queries optimized with indexes

**NFR2: Usability**
- Minimal clicks to common operations
- Cascading selectors intuitive (L0 → L1 → L2)
- Tab navigation through forms
- Tooltip help on complex fields
- Clear visual hierarchy
- Consistent button placement (Save/Cancel)
- Confirmation on destructive actions
- Visual indicators for assembly feasibility (✅/⚠️/❌)

**NFR3: Data Integrity**
- Foreign key constraints in SQLite
- Non-negative inventory quantities (enforced)
- FIFO ordering deterministic
- Only L2 ingredients assignable to products (validation)
- Prevent deletion of referenced items (cascade with confirmation)
- Input validation: non-negative quantities/costs, required fields, valid units
- Transaction-based saves (all-or-nothing)
- Depletion records immutable (audit trail)

**NFR4: Extensibility**
- Event-agnostic data model (any event type, any date)
- Food-agnostic (supports any recipe type)
- Output mode extensible (BULK_COUNT, BUNDLED, PACKAGED, PER_SERVING, etc.)
- Easy to add categories, unit types via configuration
- Modular code structure for future enhancements

**NFR5: Platform Requirements**
- Windows 10/11 primary target
- Python code cross-platform compatible
- CustomTkinter handles OS-specific rendering
- SQLite database file portable across systems
- No internet connection required

**NFR6: Data Safety**
- Database file in user's Documents folder (Carbonite backup coverage)
- Write-ahead logging (WAL) mode for SQLite
- Graceful error handling prevents data corruption
- Option to manually backup/restore database file

---

## 2. System Requirements

### 2.1 Required Software

**Python Environment**
- Python 3.10 or higher
- pip (Python package manager)
- venv or virtualenv (virtual environment)

**Python Packages**
- `customtkinter` - Modern Tkinter UI framework
- `sqlite3` - Database (included with Python)
- `Pillow` - Image library for CustomTkinter
- `sqlalchemy` - ORM for database operations
- `pandas` - Data manipulation and CSV export
- `reportlab` or `fpdf2` - Optional, for PDF export
- `pytest` - Testing framework
- `python-dateutil` - Date handling utilities

**Development Tools (Recommended)**
- VS Code or PyCharm
- Git for Windows
- DB Browser for SQLite (optional, for database inspection)

### 2.2 Installation Steps

1. Install Python 3.10+ from python.org
2. Create project directory
3. Create virtual environment: `python -m venv venv`
4. Activate: `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`
6. Run application: `python src/main.py`

### 2.3 File Structure (Updated 2025-01-04)

```
bake-tracker/
├── src/
│   ├── main.py                 # Application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            # SQLAlchemy base with UUID support
│   │   ├── ingredient.py      # Hierarchical ingredient (L0/L1/L2)
│   │   ├── product.py         # Purchasable items (brand/package)
│   │   ├── purchase.py        # Inventory with FIFO
│   │   ├── material.py        # Packaging/assembly supplies
│   │   ├── inventory_snapshot.py
│   │   ├── recipe.py          # Template with variants
│   │   ├── finished_unit.py   # Atomic items (new)
│   │   ├── bundle.py          # Consumer packages (with materials)
│   │   ├── package.py         # Logistics containers
│   │   ├── recipient.py
│   │   ├── event.py           # With output mode, production plan
│   │   └── edit_history.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py        # DB connection, session_scope()
│   │   ├── exceptions.py      # Service exception hierarchy
│   │   ├── ingredient_service.py  # Hierarchical ingredient CRUD
│   │   ├── product_service.py     # Product management
│   │   ├── purchase_service.py    # Purchase & FIFO inventory
│   │   ├── material_service.py    # Materials management
│   │   ├── recipe_service.py      # Template/variant recipes
│   │   ├── finished_unit_service.py  # FinishedUnit management
│   │   ├── bundle_service.py      # Bundle with materials
│   │   ├── package_service.py
│   │   ├── event_service.py       # Event planning with batch calc
│   │   ├── planning_service.py    # Batch calculation algorithm
│   │   ├── recipient_service.py
│   │   ├── import_export_service.py
│   │   ├── health_service.py
│   │   └── unit_converter.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── dashboard_tab.py
│   │   ├── ingredients_tab.py     # Hierarchical catalog (L0/L1/L2)
│   │   ├── products_tab.py        # Product catalog
│   │   ├── purchases_tab.py       # Purchase entry & inventory
│   │   ├── materials_tab.py       # Materials management
│   │   ├── recipe_tab.py          # Template/variant recipes
│   │   ├── finished_units_tab.py  # FinishedUnit catalog
│   │   ├── bundle_tab.py          # Bundle with materials & assembly
│   │   ├── package_tab.py
│   │   ├── recipient_tab.py
│   │   ├── event_tab.py           # Event planning with production plan
│   │   ├── event_detail_window.py # Production plan & assembly checklist
│   │   ├── report_tab.py
│   │   └── widgets/               # Reusable UI components
│   │       ├── cascading_selector.py  # L0→L1→L2 selector
│   │       ├── data_table.py
│   │       ├── search_bar.py
│   │       └── dialogs.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── validators.py
│   │   ├── slug_generator.py
│   │   └── constants.py
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_planning.py       # Batch calculation tests
│       ├── test_fifo.py           # FIFO algorithm tests
│       └── integration/
│           ├── test_event_planning.py
│           ├── test_production_flow.py
│           └── test_assembly_flow.py
├── data/                          # Created at runtime
│   └── bake_tracker.db          # SQLite database (gitignored)
├── docs/
│   ├── requirements/              # Requirements documents
│   │   ├── req_application.md     # This document
│   │   ├── req_ingredients.md     # Hierarchical ingredient requirements
│   │   ├── req_products.md        # Product catalog requirements
│   │   ├── req_recipes.md         # Template/variant recipe requirements
│   │   ├── req_finished_goods.md  # FinishedUnit/Bundle/Package requirements
│   │   ├── req_planning.md        # Event planning & batch calculation
│   │   └── req_inventory.md       # FIFO inventory requirements
│   ├── design/                    # Design specifications
│   │   ├── _F040_finished_goods_inventory.md
│   │   ├── _F041_shelf_life_freshness_tracking.md
│   │   ├── F026-deferred-packaging-decisions.md
│   │   └── [other feature specs]
│   ├── architecture.md
│   ├── user_guide.md
│   ├── schema.md
│   └── web_migration_notes.md     # Future web architecture
├── .kittify/                      # Spec-Kitty workflow
│   └── memory/
│       └── constitution.md        # Project constitution
├── examples/
│   └── test_data.json
├── .gitignore
├── README.md
├── CHANGELOG.md
├── requirements.txt
└── setup.py
```

---

## 3. Project Management Requirements

### 3.1 Version Control

- Git repository initialized
- `.gitignore`: Python cache, `__pycache__/`, `*.pyc`, `venv/`, `data/*.db`, OS files
- README.md with setup and quick start
- LICENSE (MIT recommended)
- Main branch for stable code
- Feature branches for development

### 3.2 Documentation Deliverables

1. **README.md**: Project overview, installation, quick start
2. **Requirements Documents** (in `docs/requirements/`):
   - `req_application.md` (this document)
   - `req_ingredients.md`, `req_products.md`, `req_recipes.md`
   - `req_finished_goods.md`, `req_planning.md`, `req_inventory.md`
3. **ARCHITECTURE.md**: System architecture, database schema (ERD), component flow
4. **USER_GUIDE.md**: Step-by-step workflows, screenshots, tutorials, troubleshooting
5. **SCHEMA.md**: Detailed database schema
6. **CHANGELOG.md**: Version history

### 3.3 Code Standards

- PEP 8 style guide
- Docstrings for all classes and public methods
- Type hints where beneficial
- Comments for complex logic
- Meaningful variable/function names

### 3.4 Testing Strategy

- Unit tests for services (business logic)
- Unit tests for planning algorithms (batch calculation, FIFO)
- Integration tests for database operations
- Manual UI testing (automated UI testing complex for Tkinter)
- Test coverage goal: >70% for services layer

---

## 4. Implementation Phases (Updated 2025-01-04)

### Phase 1: Foundation (MVP) - ✅ COMPLETED
- Database schema and models
- Basic unit conversion system
- Ingredient CRUD with inventory management
- Simple recipe CRUD
- Basic CustomTkinter UI shell with navigation

### Phase 2: Core Architecture Refactor - 🔄 IN PROGRESS

**Completed:**
- ✅ Hierarchical ingredient model (L0/L1/L2)
- ✅ Product catalog with ingredient linkage
- ✅ Purchase-based inventory with FIFO
- ✅ Shelf life tracking (F041)
- ✅ Service layer for ingredient/product/purchase
- ✅ Three requirements docs seeded (ingredients, products, inventory)

**In Progress:**
- ⏳ Recipe template/variant architecture
- ⏳ FinishedUnit/Bundle/Package hierarchy
- ⏳ Event planning with batch calculation
- ⏳ Three requirements docs seeded (recipes, finished_goods, planning)
- ⏳ UI updates for hierarchical selectors

**Next Steps:**
- Implement recipe template models and services
- Implement FinishedUnit/Bundle/Package models
- Implement planning service (batch calculation algorithm)
- Create UI for event planning with production plan display
- Assembly feasibility checks (event-scoped Phase 2)

### Phase 3: Production & Assembly Tracking - 📋 PLANNED

**Scope:**
- Materials model and service
- Bundle-material associations
- Production execution (FIFO depletion)
- Assembly completion checklist (Phase 2 minimal)
- Event-scoped production/assembly tracking
- Shopping list generation (ingredients + materials)

**Out of Scope (Phase 3+):**
- Cross-event inventory tracking (deferred)
- Inventory transactions on assembly (deferred)
- Full assembly workflow UI (deferred)

### Phase 4: Polish & Reporting - 📋 PLANNED
- Advanced reports and analysis
- Materials usage reports
- CSV export functionality
- UI polish and usability improvements
- Comprehensive testing
- User guide completion

### Phase 5: Nice-to-Haves (Future Features) - 📋 PLANNED
- PDF export for reports
- Inventory snapshot comparison tool
- Recipe scaling
- Bulk import from CSV
- Flexible output terminology (packages/servings/plates)
- Category management with UIDs

---

## 5. Key Technical Considerations

### 5.1 Hierarchical Ingredient Strategy

**Challenge:** Ingredients need categorization but also product-level specificity.

**Solution:**
- **Three-tier hierarchy**: L0 (Flour) → L1 (All-Purpose Flour) → L2 (King Arthur AP Flour)
- **Cascading selectors**: UI guides user through L0 → L1 → L2 selection
- **Product linkage**: Products link to L2 only
- **Auto-propagation**: Selecting product auto-fills L0/L1/L2
- **Property inheritance**: Shelf life, density cascade from L0 → L1 → L2
- **Override pattern**: L2 > L1 > L0 (child overrides parent)

### 5.2 Recipe Template/Variant Strategy

**Challenge:** One recipe base produces multiple finished goods with variations.

**Solution:**
- **Recipe Templates**: Base recipe with common ingredients
- **Yield Options**: Multiple yield levels (24, 48, 96 cookies)
  - Each with batch multiplier for scaling
- **Recipe Variants**: Ingredient/finishing variations
  - Each variant links to specific FinishedUnit it produces
  - Variant-specific ingredients (additions, substitutions)
- **Proportional Calculation**: Variant ingredients scaled by proportion within batch

**Example:**
```
Recipe: Sugar Cookie Template
  Base: 2 cups flour, 1 cup butter, 1 cup sugar
  Yield Options: 24 (1x), 48 (2x), 96 (4x)
  Variants:
    - Chocolate Chip → produces "Chocolate Chip Cookie" FinishedUnit
      - Add: 0.5 cup chocolate chips
    - Rainbow Sprinkle → produces "Rainbow Sprinkle Cookie" FinishedUnit
      - Add: 0.25 cup sprinkles
```

### 5.3 Automatic Batch Calculation

**Challenge:** Users struggle to calculate recipe batches from event requirements.

**Solution:**
```
Step 1: Explosion (Bundle/Package → FinishedUnit)
  Event needs 50 gift bags × (6 cookies + 3 brownies)
  = 300 cookies + 150 brownies

Step 2: Recipe Grouping
  Group FinishedUnits by recipe template
  Sugar Cookie Recipe: 300 cookies
  Brownie Recipe: 150 brownies

Step 3: Batch Calculation
  For each recipe, find optimal yield option:
    - Minimize waste (extra units)
    - Minimize batches (fewer runs)
  
  Sugar Cookie (yield: 24, 48, 96):
    Option 1: 96-cookie yield → 4 batches (384 total, 84 extra)
    Option 2: 48-cookie yield → 7 batches (336 total, 36 extra) ← OPTIMAL
    Option 3: 24-cookie yield → 13 batches (312 total, 12 extra)

Step 4: Ingredient Aggregation
  Base ingredients × batches × batch_multiplier
  Variant ingredients × batches × batch_multiplier × variant_proportion
  Sum across all recipes

Step 5: Inventory Gap Analysis
  Compare needs vs snapshot → shopping list
```

### 5.4 FIFO Inventory Strategy

**Challenge:** Ingredients purchased at different times/prices need accurate costing.

**Solution:**
- **Purchase-based tracking**: Each purchase is separate inventory item
- **FIFO depletion**: Always consume oldest purchases first (by purchase_date)
- **Multi-purchase spanning**: Single depletion can consume from multiple purchases
- **Weighted cost**: Calculate cost from actual purchases consumed
- **Audit trail**: Depletion records immutable for cost accuracy

**Example:**
```
Recipe needs 10 cups flour
Inventory:
  Purchase A (2024-12-01): 5 cups @ $0.50/cup
  Purchase B (2024-12-15): 8 cups @ $0.60/cup
  Purchase C (2025-01-02): 20 cups @ $0.55/cup

FIFO Depletion:
  Take 5 cups from Purchase A (oldest) = $2.50
  Take 5 cups from Purchase B (next oldest) = $3.00
  Total cost: $5.50 for 10 cups
```

### 5.5 Event-Scoped Planning (Phase 2)

**Challenge:** Cross-event inventory complex, defer to Phase 3.

**Solution (Phase 2):**
- **Event-scoped only**: Each event plans production independently
- **No inventory carry-over**: Event calculates full production needs
- **Assembly feasibility**: Check if production plan enables assembly
- **Checklist confirmation**: User confirms assembly (no inventory transactions)

**Future (Phase 3):**
- Cross-event inventory tracking
- Production shortfall calculation (use existing inventory)
- Assembly runs with inventory transactions
- Inventory awareness in planning

### 5.6 Database Relationships (Updated)

**Ingredient Hierarchy:**
```
Ingredient L0 (Flour)
  └─ Ingredient L1 (All-Purpose Flour)
       └─ Ingredient L2 (King Arthur AP Flour)
            └─ Product ("King Arthur AP 25lb bag")
                 └─ Purchase (actual inventory, FIFO tracking)
```

**Recipe → FinishedUnit:**
```
RecipeTemplate
  ├─ base_ingredients (many Ingredients)
  ├─ yield_options (many YieldOptions)
  └─ variants (many RecipeVariants)
       └─ produces → FinishedUnit (1:1 per variant)
```

**Event Planning:**
```
Event
  ├─ output_mode (enum: BULK_COUNT, BUNDLED, PACKAGED)
  ├─ requirements:
  │    ├─ BULK_COUNT → List[FinishedUnit, quantity]
  │    ├─ BUNDLED → List[Bundle, quantity]
  │    └─ PACKAGED → List[Package, quantity]
  └─ production_plan (auto-generated):
       ├─ recipe_batches (by recipe template)
       ├─ finished_units (by variant)
       ├─ assembly_requirements (bundles to make)
       └─ shopping_list (ingredient + material gaps)
```

**Materials:**
```
Material
  └─ used_in → BundleMaterial (many)
       └─ Bundle (contains materials + FinishedUnits)
```

---

## 6. Assumptions & Constraints

**Assumptions:**
- Single user, no concurrent access needed
- User has basic computer skills
- Data volume within specified limits (500 ingredients, 100 recipes, etc.)
- User manages backups via Carbonite
- Internet connection not required after installation

**Constraints:**
- No cost budget for software/services
- Windows primary platform (cross-platform code)
- No server/cloud components
- Development by Claude Code with user oversight
- Must use free/open-source dependencies

**Phase 2 Constraints:**
- Event-scoped planning only (no cross-event inventory)
- Assembly confirmation only (no inventory transactions)
- No production shortfall calculation

---

## 7. Success Criteria (Updated 2025-01-04)

**Phase 1 Success:** ✅ ACHIEVED
- User can add ingredients with purchase/recipe units
- User can create recipes with ingredients
- Basic UI navigates between Inventory and Recipes
- Database persists data correctly

**Phase 2 Success:** 🔄 IN PROGRESS
- ✅ Hierarchical ingredient catalog (L0/L1/L2) working
- ✅ Product catalog linked to L2 ingredients
- ✅ Purchase-based inventory with FIFO
- ✅ Shelf life tracking with freshness indicators
- ⏳ Recipe template/variant architecture
- ⏳ FinishedUnit/Bundle/Package hierarchy
- ⏳ Event planning with automatic batch calculation
- ⏳ Assembly feasibility checks (event-scoped)
- ⏳ UI for cascading ingredient selectors
- ⏳ UI for production plan display

**Phase 3 Success Criteria:**
- Materials management working
- Bundle-material associations
- Production execution depletes inventory (FIFO)
- Assembly completion checklist functional
- Shopping lists generate (ingredients + materials)
- Event-scoped production/assembly tracking

**Final Success:**
- Application reduces planning time by 50% vs spreadsheet
- Automatic batch calculation eliminates math errors
- Zero data loss or corruption
- User successfully completes one full holiday season cycle
- All Phase 2-3 features working reliably

---

## 8. User Workflows (Primary Use Cases) (Updated 2025-01-04)

### Workflow 1: Set Up Ingredient Catalog (Hierarchical)
1. Open **Ingredients** tab
2. Create L0 category: "Flour"
3. Create L1 subcategory: "All-Purpose Flour" (under Flour)
4. Create L2 ingredient: "King Arthur AP Flour" (under All-Purpose)
5. Set shelf life: 6 months (at L1 or L2)
6. Set density: 120 g/cup (at L1 or L2)
7. Open **Products** tab
8. Create product: "King Arthur AP 25lb bag"
   - Link to L2: "King Arthur AP Flour"
   - Package size: 25 lb
   - Purchase unit: "bag"
9. Mark as preferred product

### Workflow 2: Record Purchase (with FIFO Inventory)
1. Open **Purchases** tab
2. Click "Add Purchase"
3. Use cascading selector: Flour → All-Purpose → King Arthur
   - Or select product directly: "King Arthur AP 25lb bag"
4. Enter quantity: 1 bag
5. Enter price: $15.99
6. Enter purchase date: 2025-01-04
7. Optional: Override shelf life (defaults from product/ingredient)
8. Save → System creates inventory item with FIFO tracking
9. View computed expiration date
10. See freshness indicator: 🟢 FRESH (6 months remaining)

### Workflow 3: Create Recipe with Variants
1. Open **Recipes** tab
2. Click "Add Recipe Template"
3. Enter name: "Sugar Cookie"
4. Add base ingredients:
   - 2 cups flour (select L2: King Arthur AP)
   - 1 cup butter
   - 1 cup sugar
5. Define yield options:
   - 24 cookies (1x batch multiplier)
   - 48 cookies (2x batch multiplier)
   - 96 cookies (4x batch multiplier)
6. Create variants:
   - Variant A: "Chocolate Chip"
     - Produces: "Chocolate Chip Cookie" FinishedUnit
     - Add: 0.5 cup chocolate chips
   - Variant B: "Plain"
     - Produces: "Plain Cookie" FinishedUnit
     - No additional ingredients
7. View calculated cost (FIFO from purchases)
8. Save

### Workflow 4: Plan Event with Automatic Batch Calculation
1. Open **Events** tab
2. Create event: "Christmas 2025"
3. Select output mode: BUNDLED
4. Create/select bundles:
   - "Holiday Gift Bag" (6 cookies + 3 brownies + 1 cellophane bag)
5. Specify quantity: 50 gift bags needed
6. System automatically calculates:
   - **Explosion**: 50 × 6 = 300 cookies, 50 × 3 = 150 brownies
   - **Recipe Grouping**: Sugar Cookie (300), Brownie (150)
   - **Batch Calculation**:
     - Sugar Cookie: 48-cookie yield, 7 batches (336 total, 36 extra)
     - Brownie: 24-brownie yield, 7 batches (168 total, 18 extra)
   - **Ingredient Aggregation**: Total flour, chocolate, etc.
   - **Shopping List**: Compare vs inventory snapshot
7. View production plan:
   - Recipes to make: 7 batches Sugar Cookie, 7 batches Brownie
   - Ingredients needed: [shopping list]
   - Materials needed: 50 cellophane bags
8. Export shopping list to CSV

### Workflow 5: Execute Production & Track Assembly
1. **Production Phase**:
   - Execute production runs in app
   - System depletes ingredient inventory (FIFO)
   - Records actual yields
2. **Assembly Feasibility Check**:
   - After production, view assembly checklist
   - System validates: ✅ 336 cookies available (need 300)
   - System validates: ✅ 168 brownies available (need 150)
   - Status: ✅ Can assemble 50 gift bags
3. **Assembly Phase** (Phase 2 Minimal):
   - View assembly checklist
   - As bundles assembled, check off completed
   - [ ] 50 Holiday Gift Bags → ✅ 50 Holiday Gift Bags
   - System records confirmation (no inventory transactions Phase 2)
4. **Delivery Phase**:
   - Mark packages delivered to recipients
   - Track actual costs

### Workflow 6: Manage Materials
1. Open **Materials** tab
2. Click "Add Material"
3. Enter: "Cellophane Bags - Large"
4. Category: "Bags"
5. Purchase unit: "pack of 100"
6. Current quantity: 2 packs
7. Unit cost: $8.99 per pack
8. Shelf life: none
9. Save
10. In **Bundles** tab:
    - Edit bundle: "Holiday Gift Bag"
    - Add material: "Cellophane Bags - Large" × 1
    - System includes in bundle cost
    - System includes in shopping list

---

## 9. Open Questions & Future Enhancements

**Open Questions:**
- Default L0 categories for ingredients? (Flour/Grains, Sugar/Sweeteners, Dairy, Chocolate, Nuts, Spices, Fats/Oils)
- Default recipe categories? (Cookies, Cakes, Candies, Breads, Bars)
- Default material categories? (Bags, Ribbon, Boxes, Wrapping, Labels)
- Should Phase 2 include any cross-event inventory features?
- When to transition from Phase 2 (event-scoped) to Phase 3 (cross-event)?

**Future Enhancement Ideas (Phase 3+):**
- **Cross-Event Inventory**: Use existing FinishedUnit inventory across events
- **Production Shortfall**: Calculate "need 300 cookies, have 120, produce 180"
- **Assembly Inventory Transactions**: Actual inventory depletion on assembly
- **Full Assembly Workflow**: Material selection, batch assembly, tracking
- **Multi-Event Planning**: Aggregate shopping across events
- **Cost Optimization**: Cheapest production plan
- **Schedule Optimization**: Production timing
- **Recipe Scaling**: Dynamic yield adjustment
- **Bulk Import**: CSV import for ingredients/recipes
- **Flexible Terminology**: Packages/Servings/Plates by event type
- **Category UIDs**: Add/rename categories without data loss
- **Mobile App**: Shopping list companion
- **Barcode Scanning**: UPC/GTIN for purchases

---

## Document History

- **v1.0** (2024) - Initial draft based on user stories
- **v1.1** (2024) - Updated with technical decisions: CustomTkinter, unit conversion strategy, inventory snapshots
- **v1.2** (2025-11-10) - Updated with Ingredient/Product refactor, Materials, Production tracking
- **v1.3** (2025-01-04) - Major update incorporating:
  - Hierarchical ingredient architecture (L0/L1/L2)
  - Recipe template/variant system
  - FinishedUnit/Bundle/Package hierarchy
  - Automatic batch calculation algorithm
  - Event-scoped planning (Phase 2)
  - FIFO inventory with shelf life tracking
  - Requirements document references
  - Updated implementation phases
  - Phase 2 vs Phase 3 scope clarity

**Document Status:** Living document, updated as requirements evolve

**Current Phase:** Phase 2 (Core Architecture Refactor) in progress  
**Next Phase:** Phase 3 (Production & Assembly Tracking)
