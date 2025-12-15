# Seasonal Baking Tracker - Requirements Document v1.2

## Executive Summary

A desktop application for managing holiday baking inventory, recipes, and gift package planning. Built with Python, SQLite, and CustomTkinter for a single Windows user with cross-platform compatibility.

**Technology Stack:** Python 3.10+, SQLite, CustomTkinter, SQLAlchemy, Pandas

---

## 1. Application Requirements

### 1.1 Data Model Requirements

**Ingredients** (Refactored in v0.4.0 - Generic Ingredient Catalog)
- Unique identifier (UUID), name (with auto-generated slug), category
- Recipe unit type (canonical unit for recipes to reference)
- Density (g/ml) for volume-weight conversions
- Optional: industry standard identifiers (FoodOn, FDC, FoodEx2, LanguaL)
- Optional: allergen information, physical properties
- Support for ingredient aliases and crosswalks to external taxonomies
- Unit types: oz, lb, g, kg, tsp, tbsp, cup, ml, l, count/each

**Products** (v0.4.0 - Brand/Package Specific Items)
- Links to parent Ingredient (generic concept)
- Brand, package size, UPC/GTIN barcode
- Purchase unit type and quantity (e.g., "bag", 25 lb)
- Supplier/source information
- Preferred product flag (for shopping recommendations)
- Calculated properties: display_name, total_inventory_quantity, average_price

**Inventory Items** (v0.4.0 - Actual Inventory with FIFO Support)
- Links to Product (specific brand/package)
- Quantity in product's package_unit
- Purchase date (for FIFO consumption), expiration date
- Storage location (e.g., "Main Pantry", "Basement")
- Notes field
- Supports lot/batch tracking via separate records

**Purchase History** (v0.4.0 - Price Tracking)
- Links to Product
- Purchase date, quantity purchased, unit cost, supplier
- Total cost calculation
- Enables price trend analysis and cost forecasting

**Materials** (New - Packaging/Assembly Supplies)
- Unique identifier, name, category (e.g., "Cellophane Bags", "Ribbon", "Boxes")
- Purchase unit type, current quantity
- Unit cost (per purchase unit)
- Last updated date, purchase history
- Tracked like ingredients but associated with bundles (not recipes)
- Examples: cellophane bags, ribbon, plastic wrap, tin foil, boxes, tags, stickers
- Support for partial units

**Inventory Snapshots** (Updated for Materials)
- Snapshot date, description
- Copy of all ingredient quantities at snapshot time (aggregated by ingredient across products)
- Copy of all material quantities at snapshot time
- References which events use this snapshot
- Auto-create on first event planning for a period

**Recipes** (Updated for Auto-Creation of Finished Goods)
- Unique identifier, name, category, source, date added, last modified, estimated time
- Ingredient list with quantities and units (supports both imperial and metric)
- References generic Ingredients (not specific Products) for brand flexibility
- Yield specification (quantity, unit, and description of finished goods)
- **Discrete yield flag**: When set, automatically creates corresponding Finished Good record
- Notes field
- Calculated cost based on FIFO pantry consumption or preferred product pricing

**Finished Goods** (Updated - Auto-Created or Manual)
- Can be auto-created from recipe with discrete yield, or manually created
- Link to source recipe (optional for manual finished goods)
- Derived cost from recipe ingredients (FIFO costing)
- Production records: date, actual quantity produced, notes
- **Production tracking**: Checkoff status for event tracking (planned vs. actual)

**Bundles** (Updated for Materials)
- Name, description
- List of finished goods with quantities per bundle
- **List of materials** with quantities per bundle (e.g., "1 cellophane bag", "2 feet ribbon")
- Calculated cost based on component costs (finished goods + materials)
- Can include single-item bundles (e.g., "1 Cake")
- **Assembly tracking**: Checkoff status for event tracking (planned vs. actual assembled)

**Gift Packages**
- Name, description
- List of bundles with quantities
- Calculated total cost
- Template flag (reusable across events)

**Recipients**
- Name, household name/identifier, notes
- Delivery history: event, year, package sent, date delivered, actual cost

**Events**
- Name (Christmas 2025, Easter 2026, etc.), year, date range
- References inventory snapshot used for planning
- Planning status: planning, in-progress, completed
- Package assignments to recipients
- Planned vs actual tracking

**Edit History (for Undo)**
- Table/entity modified, record ID, field, old value, new value, timestamp
- Keep last 8 edits per entity type in memory
- User can undo sequentially

### 1.2 Functional Requirements

**FR1: Inventory Management** (Updated for Ingredient/Product/Inventory Architecture)
- **Ingredient Catalog**: Manage generic ingredients (brand-agnostic)
  - Add/edit/delete ingredients with category, recipe unit, density
  - Manage products for each ingredient (brand, package, UPC, supplier)
  - Mark preferred product per ingredient for shopping recommendations
  - Search across ingredient names, categories, aliases
- **Inventory Management**: Track actual inventory by product
  - Add inventory items with product, purchase date, expiration, location
  - Display inventory aggregated by ingredient or detailed by product/lot
  - FIFO consumption algorithm for cost accuracy
  - Expiration alerts and location tracking
- **Materials Management**: Track packaging/assembly supplies
  - Add/edit/delete materials with category, purchase unit, quantity
  - Update quantities and unit costs
  - Search and filter by category, name
  - Calculate total materials inventory value
- **Inventory Snapshots**: Create point-in-time snapshots
  - Capture ingredient quantities (aggregated across all products/inventory items)
  - Capture material quantities
  - Associate with events for planning
- Edit quantities with undo (last 8 edits)
- Calculate total inventory value (ingredients + materials)

**FR2: Unit Conversion System**
- Maintain conversion tables for standard units
- Store custom conversion per ingredient (purchase → recipe unit)
- Display helper showing "1 bag (50 lb) = X cups" based on conversion factor
- Validation that recipe units are compatible with ingredient's recipe unit type
- Support mixed unit systems (imperial + metric) within same recipe

**FR3: Recipe Management** (Updated for Auto-Creation of Finished Goods)
- CRUD operations for recipes
- Link generic ingredients (not specific products) with quantities and units
- **Discrete yield flag**: When enabled, automatically creates/updates linked Finished Good record
  - Finished good name matches recipe name
  - Finished good updates when recipe yield changes
  - Optional: user can override finished good name
- Automatic unit conversion for cost calculation using FIFO or preferred product
- Display yield information (quantity, unit, description)
- Calculate and display recipe cost (FIFO from pantry, fallback to preferred product)
- Filter/search by category, name, ingredients
- Show all recipes using a specific ingredient
- Display estimated time and source

**FR4: Bundle & Package Management** (Updated for Materials)
- CRUD for bundles (collections of finished goods)
  - **Add materials to bundles** (e.g., cellophane bags, ribbon, boxes)
  - Specify quantity of each material per bundle
  - Auto-calculate costs including materials
- CRUD for packages (collections of bundles)
- Auto-calculate costs at each level (finished goods + materials)
- Mark packages as templates for reuse
- Clone existing bundles/packages
- Validation preventing circular references

**FR5: Event Planning** (Updated for Consolidated Summary & Quick Inventory)
- Create event with name, year, date range
- Select or create inventory snapshot for event
- Assign packages to recipients
- **Consolidated Event Summary** (User Story 2): Display comprehensive planning view
  - Total ingredients needed (aggregated across all recipes/packages)
  - Ingredient availability status (in pantry vs. needed)
  - Shopping list (what needs to be purchased with quantities)
  - Recipe batches needed (count by recipe)
  - Finished goods quantities required (count by type)
  - Bundles to assemble (count by type)
  - **Materials needed** (aggregated across all bundles)
  - Materials availability status (in inventory vs. needed)
  - Estimated total cost (ingredients + materials)
- **Quick Inventory Update** (User Story 3):
  - Display only ingredients/materials needed for this specific event
  - Update pantry quantities for event-specific items
  - Highlight missing or low inventory items
  - Generate focused shopping list for just this event's needs
- Generate shopping list showing shortfall by category (ingredients and materials)
- Color coding: sufficient (green), low (yellow), insufficient (red)
- Export shopping list to CSV

**FR6: Production Tracking** (Updated for Checkoff Workflow)
- **Finished Goods Production Tracking** (User Story 4):
  - Display list of finished goods needed for event with quantities
  - Check off completed finished goods as they are produced
  - Update actual quantity produced (may differ from planned)
  - Show progress: completed vs. remaining to make
  - Record production date and notes
- **Bundle Assembly Tracking** (User Story 5):
  - Display list of bundles needed for event by type with quantities
  - Check off bundles as they are assembled
  - Show progress: assembled vs. remaining for each bundle type
  - Validate materials availability before marking complete
- Mark packages as delivered to recipients
- Track actual costs vs estimates
- Inventory depletion tracking (manual or automatic via FIFO consumption)
- Update event status (planning → in-progress → completed)

**FR7: Reporting & Analysis** (Updated for Materials)
- **Dashboard**: Current event summary, upcoming tasks, recent activity, production progress
- **Inventory Report**: Current stock for ingredients and materials, value, items below threshold
- **Event Summary**: Planned vs actual packages, costs, production (ingredients + materials)
- **Year-over-Year Comparison**: Costs, quantities, recipients by event type
- **Recipient History**: What each person received, by event/year
- **Cost Analysis**: By package type, recipient, finished good, ingredient, and materials
- **Shopping List**: Exportable by category with quantities (ingredients and materials separately)
- **Materials Usage Report**: Materials consumed per event, cost per bundle type
- All reports viewable on-screen with export to CSV option

**FR8: Navigation & UI (CustomTkinter)**
- Main window with tabbed interface or sidebar navigation
- Sections: Dashboard, Inventory, Recipes, Bundles, Packages, Recipients, Events, Reports
- Consistent styling using CustomTkinter widgets
- Forms with validation and clear error messages
- Confirmation dialogs for deletions
- Search/filter bars in list views
- Sortable table/list views
- Status bar showing last save time, current event

### 1.3 Non-Functional Requirements

**NFR1: Performance**
- UI response time < 200ms for typical operations
- Support for 500+ ingredients, 100+ recipes, 50+ recipients, 10+ years of events
- Database queries optimized with indexes

**NFR2: Usability**
- Minimal clicks to common operations
- Tab navigation through forms
- Tooltip help on complex fields
- Clear visual hierarchy
- Consistent button placement (Save/Cancel)
- Confirmation on destructive actions

**NFR3: Data Integrity**
- Foreign key constraints in SQLite
- Prevent deletion of referenced items (show dependencies, cascade with confirmation)
- Input validation: non-negative quantities/costs, required fields, valid units
- Transaction-based saves (all-or-nothing)
- Auto-save indicators

**NFR4: Extensibility**
- Event-agnostic data model (any event type, any date)
- Food-agnostic (supports any recipe type)
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

### 2.3 File Structure (Updated 2025-11-10)

```
bake-tracker/
├── src/
│   ├── main.py                 # Application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            # SQLAlchemy base with UUID support
│   │   ├── ingredient.py      # Generic ingredient catalog (v0.4.0)
│   │   ├── product.py         # Brand/package specific items (v0.4.0)
│   │   ├── pantry_item.py     # Actual inventory with FIFO (v0.4.0)
│   │   ├── purchase.py        # Price history tracking (v0.4.0)
│   │   ├── material.py        # Packaging/assembly supplies (new)
│   │   ├── inventory_snapshot.py
│   │   ├── recipe.py          # With discrete yield flag (updated)
│   │   ├── finished_good.py   # With production tracking (updated)
│   │   ├── bundle.py          # With materials and assembly tracking (updated)
│   │   ├── package.py
│   │   ├── recipient.py
│   │   ├── event.py
│   │   └── edit_history.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py        # DB connection, session_scope()
│   │   ├── exceptions.py      # Service exception hierarchy (v0.4.0)
│   │   ├── ingredient_service.py  # Ingredient catalog CRUD (v0.4.0)
│   │   ├── product_service.py     # Product management (v0.4.0)
│   │   ├── pantry_service.py      # Pantry & FIFO consumption (v0.4.0)
│   │   ├── purchase_service.py    # Purchase history & trends (v0.4.0)
│   │   ├── material_service.py    # Materials management (new)
│   │   ├── recipe_service.py      # With auto-FG creation (updated)
│   │   ├── finished_good_service.py  # Production tracking (updated)
│   │   ├── package_service.py
│   │   ├── event_service.py       # Event planning with materials (updated)
│   │   ├── recipient_service.py
│   │   ├── import_export_service.py
│   │   ├── health_service.py      # System health check
│   │   ├── unit_converter.py      # Unit conversion with density support
│   │   └── inventory_service.py   # Legacy - being phased out
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Main app window
│   │   ├── dashboard_tab.py
│   │   ├── ingredients_tab.py     # Generic ingredient catalog (v0.4.0)
│   │   ├── inventory_tab.py       # Actual inventory by product (v0.4.0)
│   │   ├── materials_tab.py       # Materials management (new)
│   │   ├── recipe_tab.py
│   │   ├── finished_goods_tab.py  # With production checkoff (updated)
│   │   ├── bundle_tab.py          # With materials & assembly checkoff (updated)
│   │   ├── package_tab.py
│   │   ├── recipient_tab.py
│   │   ├── event_tab.py
│   │   ├── event_detail_window.py # Consolidated summary (updated)
│   │   ├── report_tab.py
│   │   └── widgets/               # Reusable UI components
│   │       ├── data_table.py
│   │       ├── search_bar.py
│   │       └── dialogs.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py              # App configuration
│   │   ├── validators.py          # Input validation
│   │   ├── slug_generator.py      # Slug generation (v0.4.0)
│   │   ├── migrate_to_ingredient_product.py  # Migration script (v0.4.0)
│   │   └── constants.py           # Unit types, categories
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_validators.py
│       ├── test_unit_converter.py
│       └── integration/           # Integration tests (v0.4.0)
│           ├── test_inventory_flow.py
│           ├── test_fifo_scenarios.py
│           └── test_purchase_flow.py
├── data/                          # Created at runtime
│   └── bake_tracker.db          # SQLite database (gitignored)
├── docs/
│   ├── architecture.md            # System architecture (updated)
│   ├── current_priorities.md      # Active development priorities (updated)
│   ├── development_status.md      # Complete project history (updated)
│   ├── requirements.md            # This document (updated)
│   ├── user_guide.md              # User documentation
│   ├── user_stories.md            # Latest user stories (new)
│   ├── schema_v0.3.md             # Legacy schema
│   ├── schema_v0.4_design.md      # Ingredient/Product refactor design
│   ├── ingredient_industry_standards.md  # External standards reference
│   ├── import_export_specification.md    # Data format v2.0
│   ├── packaging_options.md       # Materials/packaging reference
│   ├── web_migration_notes.md     # Future web architecture notes
│   ├── archive/                   # Historical documents
│   │   ├── README.md
│   │   ├── pause_point.md
│   │   └── refactor_status.md
│   ├── research/                  # Research documents
│   │   ├── README.md
│   │   └── ingredient_taxonomy_research.md
│   └── workflows/                 # Development workflows
│       ├── README.md
│       └── testing_workflow.md
├── kitty-specs/                   # Spec-Kitty task management
│   └── 002-service-layer-for/     # Feature 002 specs (completed)
├── examples/
│   ├── test_data_v2.json          # Test data (v2.0 format)
│   └── import/                    # Sample import data
├── .gitignore
├── README.md
├── CHANGELOG.md
├── requirements.txt
├── pyproject.toml
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

1. **README.md**: Project overview, installation, quick start, screenshots
2. **REQUIREMENTS.md**: This document
3. **ARCHITECTURE.md**: 
   - System architecture diagram
   - Database schema with ERD
   - Component interaction flow
   - Unit conversion logic explanation
4. **USER_GUIDE.md**:
   - Step-by-step workflows
   - Screenshot tutorials
   - Common tasks (adding recipe, planning event, generating shopping list)
   - Troubleshooting
5. **SCHEMA.md**: Detailed database schema with all fields, types, constraints
6. **CHANGELOG.md**: Version history with changes

### 3.3 Code Standards

- PEP 8 style guide
- Docstrings for all classes and public methods
- Type hints where beneficial
- Comments for complex logic
- Meaningful variable/function names

### 3.4 Testing Strategy

- Unit tests for services (business logic)
- Unit tests for unit converter
- Integration tests for database operations
- Manual UI testing (automated UI testing is complex for Tkinter)
- Test coverage goal: >70% for services layer

---

## 4. Implementation Phases (Updated 2025-11-10)

### Phase 1: Foundation (MVP) - ✅ COMPLETED
- Database schema and models
- Basic unit conversion system
- Ingredient CRUD with inventory management
- Simple recipe CRUD
- Basic CustomTkinter UI shell with navigation

### Phase 2: Finished Goods & Bundles - ✅ COMPLETED
- Bundle and package creation
- Finished good tracking
- Basic cost calculations

### Phase 3: Event Planning - ✅ COMPLETED
- Event creation and planning
- Recipient management
- Package assignments
- Shopping list generation
- Basic reports

### Phase 4: Ingredient/Product Refactor - 🔄 IN PROGRESS
- ✅ Models refactored (Ingredient, Product, InventoryItem, Purchase)
- ✅ Service layer implemented (Ingredient, Product, Inventory, Purchase services)
- ✅ FIFO consumption algorithm
- ✅ Price trend analysis
- ⏳ UI updates (My Ingredients, My Pantry tabs)
- ⏳ Migration from v0.3.0 schema
- ⏳ Recipe/Event service integration with new architecture

### Phase 5: Materials & Enhanced Production Tracking - 📋 PLANNED
- **Materials Model & Service**: Packaging/assembly supplies tracking
- **Bundle-Material Associations**: Link materials to bundles with quantities
- **Auto-Creation of Finished Goods**: Discrete yield flag on recipes
- **Production Checkoff Workflow**:
  - Track finished goods completion status
  - Track bundle assembly completion status
- **Consolidated Event Summary**: All-in-one planning view (ingredients + materials)
- **Quick Inventory Update**: Event-specific inventory updates
- **Materials in Snapshots**: Include materials in inventory snapshots
- **Materials in Shopping Lists**: Separate materials shopping list
- **Materials Cost Tracking**: Include in bundle and event costs

### Phase 6: Polish & Reporting
- Advanced reports and analysis
- Materials usage reports
- CSV export functionality
- Undo system refinement
- UI polish and usability improvements
- Comprehensive testing

### Phase 7: Nice-to-Haves (Future Features)
- PDF export for reports
- Inventory snapshot comparison tool
- Recipe scaling
- Bulk import from CSV
- **Flexible output terminology**: Packages/Servings/Plates (User Story 7)
- **Category management with UIDs**: Add/rename/retire categories without loss (User Story 8)

---

## 5. Key Technical Considerations

### 5.1 Unit Conversion Strategy

**Challenge:** Ingredients purchased in one unit (e.g., 50 lb bags) consumed in another (e.g., cups).

**Solution:**
- Each ingredient has `package_unit`, `recipe_unit`, and `conversion_factor`
- Example: Flour
  - Purchase unit: "bag" (50 lb)
  - Recipe unit: "cup"
  - Conversion factor: 200 (1 bag = 200 cups)
- Standard conversion table for common conversions (lb to oz, kg to g, etc.)
- User can override with custom conversion factors
- Recipe costs calculated: (recipe quantity in recipe units) ÷ (conversion factor) × (unit cost in purchase units)

### 5.2 Inventory Snapshot Strategy (Updated for Materials)

**Challenge:** Multiple events may overlap temporally but need independent planning.

**Solution:**
- Snapshots capture **ingredient quantities** at a point in time (aggregated across all products and inventory items)
- Snapshots capture **material quantities** at a point in time
- Events reference a snapshot for planning (not live inventory)
- Actual consumption during production updates live inventory (pantry items via FIFO for ingredients, direct quantity updates for materials)
- User can create new snapshot anytime to reflect current state
- Shopping lists compare planned needs vs snapshot quantities for both ingredients and materials
- **Quick Inventory Update** feature allows updating only event-specific items instead of full inventory

### 5.3 Cost Calculation Hierarchy (Updated for Materials)

```
Ingredient (unit cost via FIFO or preferred product)
  ↓ (used in)
Recipe (calculated cost = sum of ingredient costs)
  ↓ (produces)
Finished Good (cost = recipe cost ÷ yield)
  ↓ (bundled in)
Bundle (cost = sum of finished good costs + sum of material costs)
  ↑ (consumes)
Material (unit cost)
  ↓ (included in)
Package (cost = sum of bundle costs)
  ↓ (given to)
Recipient (total cost = sum of package costs)
  ↓ (aggregated in)
Event (total cost = sum of recipient package costs = ingredients + materials)
```

**Key Changes:**
- Ingredients use FIFO costing from pantry or fallback to preferred product pricing
- Materials added at bundle level (not recipes)
- Bundle cost now includes both finished goods AND materials
- Event cost aggregates all ingredient costs + all material costs

### 5.4 Database Relationships (Updated for Ingredient/Product Architecture & Materials)

**Ingredient/Product/Inventory Architecture (v0.4.0):**
- **Ingredient** → **Product**: One-to-many (generic ingredient has multiple brand/package versions)
- **Product** → **InventoryItem**: One-to-many (product can have multiple lot entries)
- **Product** → **Purchase**: One-to-many (product has purchase price history)
- **Ingredient** ↔ **Recipes**: Many-to-many (RecipeIngredient junction with quantity/unit)
  - Recipes reference generic Ingredients, not specific Products
  - Cost calculation at runtime uses FIFO from pantry or preferred product

**Materials Architecture (New):**
- **Material** (standalone entity, similar to legacy Ingredient model)
- **Material** ↔ **Bundles**: Many-to-many (BundleMaterial junction with quantity/unit)
  - Materials associated at bundle level (not recipes)

**Recipe & Production Relationships:**
- **Recipes** → **Finished Goods**: One-to-one or one-to-many
  - With discrete yield flag: auto-creates one Finished Good
  - Without flag: can manually create multiple Finished Goods from same recipe
- **Finished Goods** ↔ **Bundles**: Many-to-many (BundleFinishedGood junction with quantity)

**Event Planning Relationships:**
- **Bundles** ↔ **Packages**: Many-to-many (PackageBundle junction with quantity)
- **Packages** ↔ **Recipients**: Many-to-many through **EventRecipientPackage** (3-way junction)
- **Events** → **Inventory Snapshot**: Many-to-one
  - Snapshot includes both ingredient quantities and material quantities
- **Events** → **EventRecipientPackage**: One-to-many

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

---

## 7. Success Criteria (Updated 2025-11-10)

**Phase 1 Success:** ✅ ACHIEVED
- User can add ingredients with purchase/recipe units
- User can create recipes with ingredients
- Basic UI navigates between Inventory and Recipes
- Database persists data correctly

**Phase 2 Success:** ✅ ACHIEVED
- User can create bundles and packages
- Finished goods tracking
- Basic cost calculations working

**Phase 3 Success:** ✅ ACHIEVED
- User can plan an event with packages for recipients
- System calculates shopping list with shortfall
- Reports show event summary

**Phase 4 Success:** 🔄 IN PROGRESS
- ✅ Ingredient/Product separation working (models & services)
- ✅ FIFO costing accurate and tested
- ✅ Multiple brands/sources per ingredient supported
- ✅ Preferred product logic implemented
- ⏳ UI migration to new architecture
- ⏳ Data migration from v0.3.0 preserves all data
- ⏳ Cost calculations match v0.3.0

**Phase 5 Success Criteria (New User Stories 1-6):**
1. **Auto-Creation of Finished Goods** (User Story 1):
   - Recipe with discrete yield flag automatically creates/updates Finished Good
   - Finished Good name matches recipe name
   - System prevents duplicate finished goods

2. **Consolidated Event Summary** (User Story 2):
   - Single view shows: total ingredients needed, pantry availability, shopping list
   - Displays: recipe batches needed, finished goods quantities, bundle counts
   - Includes materials needed and availability
   - Shows estimated total cost (ingredients + materials)

3. **Quick Inventory Update** (User Story 3):
   - Can update only ingredients/materials needed for specific event
   - System highlights missing or low inventory items
   - Generates focused shopping list for event

4. **Finished Goods Production Tracking** (User Story 4):
   - Can check off completed finished goods during production
   - Shows progress: completed vs. remaining to make
   - Updates actual quantity produced

5. **Bundle Assembly Tracking** (User Story 5):
   - Can check off assembled bundles by type
   - Shows progress: assembled vs. remaining for each bundle type
   - Validates materials availability

6. **Materials Management** (User Story 6):
   - Can add materials (cellophane bags, ribbon, boxes, etc.)
   - Materials associated with bundles (not recipes)
   - Materials tracked in inventory like ingredients
   - Materials included in shopping lists and cost calculations
   - Materials consumed during bundle assembly

**Final Success:**
- Application reduces planning time by 50% vs spreadsheet
- Zero data loss or corruption
- User successfully completes one full holiday season cycle
- All Phases 1-5 features working reliably
- Materials and production tracking streamline event execution

---

## 8. User Workflows (Primary Use Cases) (Updated 2025-11-10)

### Workflow 1: Annual Inventory Update (Updated for Ingredient/Product/Materials)
1. Open **My Ingredients** tab
2. Review ingredient catalog, add new ingredients as needed
3. Open **My Inventory** tab
4. Review inventory (actual stock by product/lot)
5. Adjust quantities for inventory items (uses FIFO)
6. Open **Materials** tab
7. Review materials inventory (cellophane bags, ribbon, boxes, etc.)
8. Adjust material quantities
9. Create inventory snapshot for new season (captures ingredients + materials)

### Workflow 2: Create New Recipe with Auto-Created Finished Good
1. Open **Recipes** tab
2. Click "Add Recipe"
3. Enter name, category, source, time
4. Add ingredients with quantities and units (select generic ingredients, not specific brands)
5. Specify yield (e.g., "24 cookies")
6. **Enable "Discrete Yield" flag** (User Story 1)
7. View calculated cost (FIFO from pantry or preferred product)
8. Save recipe → System automatically creates matching Finished Good
9. Finished Good appears in Finished Goods tab with recipe name

### Workflow 3: Plan Holiday Event with Consolidated Summary
1. Open **Events** tab, create new event (e.g., "Christmas 2025")
2. Select inventory snapshot (ingredients + materials)
3. Create/select gift packages (with bundles containing finished goods + materials)
4. Assign packages to recipients
5. **View Consolidated Event Summary** (User Story 2):
   - Total ingredients needed (all recipes aggregated)
   - Ingredients in pantry vs. needed
   - Shopping list for ingredients
   - Recipe batches to make
   - Finished goods quantities needed
   - Bundles to assemble
   - **Materials needed** (all bundles aggregated)
   - **Materials in inventory vs. needed**
   - **Shopping list for materials**
   - Estimated total cost (ingredients + materials)
6. Export shopping lists to CSV (ingredients separate from materials)
7. Shop for missing items

### Workflow 4: Quick Inventory Check Before Event (New - User Story 3)
1. Open **Event Details** for upcoming event
2. Click "Quick Inventory Update" button
3. System displays **only** ingredients/materials needed for this event
4. Update quantities for event-specific items (no need to review entire inventory)
5. System highlights missing or low items in red/yellow
6. Generate focused shopping list for just this event's needs
7. Shop for highlighted items

### Workflow 5: Track Production During Event (Updated - User Stories 4 & 5)
1. **Baking Phase** (User Story 4):
   - Open **Event Details → Production Tab**
   - View list of finished goods needed with quantities
   - As items are baked, check off completed finished goods
   - Update actual quantity produced (if different from planned)
   - System shows progress: "Completed 15 of 20 batches"
2. **Assembly Phase** (User Story 5):
   - Switch to **Assembly Tab**
   - View list of bundles needed by type with quantities
   - As bundles are assembled, check off completed bundles
   - System validates materials availability before marking complete
   - System shows progress: "Assembled 8 of 12 Cookie Tins"
3. **Delivery Phase**:
   - Mark packages as delivered to recipients with date
4. **Wrap-Up**:
   - View planned vs actual report
   - Note variations for next year

### Workflow 6: Manage Materials (New - User Story 6)
1. Open **Materials** tab
2. Click "Add Material"
3. Enter name, category (e.g., "Cellophane Bags - Large")
4. Specify purchase unit (e.g., "bag of 100")
5. Enter current quantity and unit cost
6. Save material
7. In **Bundles** tab, add material to bundle:
   - Select bundle to edit
   - Add material with quantity per bundle (e.g., "1 cellophane bag", "2 feet ribbon")
8. Material now included in bundle cost and shopping lists

---

## 9. Open Questions & Future Enhancements

**Open Questions:**
- Default categories for ingredients? (Flour/Grains, Sugar/Sweeteners, Dairy, Chocolate, Nuts, Spices, Fats/Oils, Other)
- Default categories for recipes? (Cookies, Cakes, Candies, Breads, Bars, Other)
- Default categories for materials? (Bags, Ribbon, Boxes, Wrapping, Labels, Other)
- Should system auto-deplete inventory on production recording, or manual?
- Preferred date format for UI?

**Future Enhancement Ideas (Phase 7+):**
- **Flexible Output Terminology** (User Story 7): Allow events to describe outputs as "packages", "servings", or "plates" based on event type
- **Category Management with UIDs** (User Story 8): Add/rename/retire categories without data loss using UUID-based category system
- Mobile companion app for shopping list
- Recipe import from URL
- Nutrition information tracking
- Allergen tagging (partial support in ingredient model)
- Cost trend analysis over years (foundation exists with Purchase history)
- Recipe rating/favorites
- Timer integration for baking
- Photo attachments for finished goods
- Barcode scanning for ingredients (UPC/GTIN support exists)

---

## Document History

- **v1.0** (2024) - Initial draft based on user stories
- **v1.1** (2024) - Updated with technical decisions: CustomTkinter, unit conversion strategy, inventory snapshots, clarified requirements based on user Q&A
- **v1.2** (2025-11-10) - Major update incorporating:
  - Ingredient/Product/Inventory architecture (v0.4.0 refactor)
  - Materials tracking system (User Story 6)
  - Auto-creation of finished goods (User Story 1)
  - Consolidated event summary (User Story 2)
  - Quick inventory update (User Story 3)
  - Production checkoff workflows (User Stories 4 & 5)
  - Updated file structure reflecting actual implementation
  - Updated implementation phases with Phase 5 materials focus
  - Future features: Flexible output terminology (US 7), Category UIDs (US 8)

**Document Status:** Living document, updated as requirements evolve

**Current Phase:** Phase 4 (Ingredient/Product Refactor) in progress
**Next Phase:** Phase 5 (Materials & Enhanced Production Tracking)