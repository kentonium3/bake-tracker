# Seasonal Baking Tracker - Requirements Document v1.1

## Executive Summary

A desktop application for managing holiday baking inventory, recipes, and gift package planning. Built with Python, SQLite, and CustomTkinter for a single Windows user with cross-platform compatibility.

**Technology Stack:** Python 3.10+, SQLite, CustomTkinter, SQLAlchemy, Pandas

---

## 1. Application Requirements

### 1.1 Data Model Requirements

**Ingredients**
- Unique identifier, name, brand, size/package unit (with value), purchase unit type, recipe unit type, category
- Current quantity in purchase units
- Unit cost (per purchase unit)
- Purchase unit to recipe unit conversion factor (e.g., 50 lb bag = 200 cups)
- Last updated date, purchase history
- Support for partial units (e.g., 0.5 bags, 2.75 cups)
- Unit types: oz, lb, g, kg, tsp, tbsp, cup, ml, l, count/each

**Inventory Snapshots**
- Snapshot date, description
- Copy of all ingredient quantities at snapshot time
- References which events use this snapshot
- Auto-create on first event planning for a period

**Recipes**
- Unique identifier, name, category, source, date added, last modified, estimated time
- Ingredient list with quantities and units (supports both imperial and metric)
- Yield specification (quantity, unit, and description of finished goods)
- Notes field
- Calculated cost based on ingredient unit conversions

**Finished Goods**
- Derived from recipes with calculated ingredient costs
- Production records: date, actual quantity produced, notes
- Link to source recipe

**Bundles**
- Name, description
- List of finished goods with quantities per bundle
- Calculated cost based on component costs
- Can include single-item bundles (e.g., "1 Cake")

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

**FR1: Inventory Management**
- Display current inventory with filtering by category, name, brand
- Edit quantities with undo (last 8 edits)
- Update unit costs with date tracking
- Add/delete inventory items with cascade warnings
- Search across name, brand, size fields
- Display both purchase units and equivalent recipe units
- Manual conversion factor entry or calculator helper
- Calculate total inventory value
- Create inventory snapshot with name/date

**FR2: Unit Conversion System**
- Maintain conversion tables for standard units
- Store custom conversion per ingredient (purchase → recipe unit)
- Display helper showing "1 bag (50 lb) = X cups" based on conversion factor
- Validation that recipe units are compatible with ingredient's recipe unit type
- Support mixed unit systems (imperial + metric) within same recipe

**FR3: Recipe Management**
- CRUD operations for recipes
- Link ingredients with quantities and units
- Automatic unit conversion for cost calculation (recipe units → purchase units → cost)
- Display yield information
- Calculate and display recipe cost
- Filter/search by category, name, ingredients
- Show all recipes using a specific ingredient
- Display estimated time and source

**FR4: Bundle & Package Management**
- CRUD for bundles (collections of finished goods)
- CRUD for packages (collections of bundles)
- Auto-calculate costs at each level
- Mark packages as templates for reuse
- Clone existing bundles/packages
- Validation preventing circular references

**FR5: Event Planning**
- Create event with name, year, date range
- Select or create inventory snapshot for event
- Assign packages to recipients
- Calculate and display required:
  - Packages by type (count)
  - Bundles by type (count)
  - Finished goods by type (count)
  - Recipe batches needed (count, by recipe)
  - Ingredient quantities needed (in purchase units)
  - Estimated total cost
- Show ingredient availability: current inventory vs required
- Generate shopping list showing shortfall by category
- Color coding: sufficient (green), low (yellow), insufficient (red)

**FR6: Production Tracking**
- Record actual production of finished goods (date, quantity)
- Mark packages as assembled
- Mark packages as delivered to recipients
- Track actual costs vs estimates
- Inventory depletion tracking (manual or automatic)
- Update event status (planning → in-progress → completed)

**FR7: Reporting & Analysis**
- **Dashboard**: Current event summary, upcoming tasks, recent activity
- **Inventory Report**: Current stock, value, items below threshold
- **Event Summary**: Planned vs actual packages, costs, production
- **Year-over-Year Comparison**: Costs, quantities, recipients by event type
- **Recipient History**: What each person received, by event/year
- **Cost Analysis**: By package type, recipient, finished good, ingredient
- **Shopping List**: Exportable by category with quantities
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

### 2.3 File Structure

```
bake-tracker/
├── src/
│   ├── main.py                 # Application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            # SQLAlchemy base
│   │   ├── ingredient.py
│   │   ├── inventory_snapshot.py
│   │   ├── recipe.py
│   │   ├── finished_good.py
│   │   ├── bundle.py
│   │   ├── package.py
│   │   ├── recipient.py
│   │   ├── event.py
│   │   └── edit_history.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py        # DB connection, session
│   │   ├── inventory_service.py
│   │   ├── recipe_service.py
│   │   ├── planning_service.py # Event planning calculations
│   │   ├── reporting_service.py
│   │   ├── unit_converter.py  # Unit conversion logic
│   │   └── undo_service.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # Main app window
│   │   ├── dashboard_tab.py
│   │   ├── inventory_tab.py
│   │   ├── recipe_tab.py
│   │   ├── bundle_tab.py
│   │   ├── package_tab.py
│   │   ├── recipient_tab.py
│   │   ├── event_tab.py
│   │   ├── report_tab.py
│   │   └── widgets/           # Reusable UI components
│   │       ├── data_table.py
│   │       ├── search_bar.py
│   │       └── dialogs.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py          # App configuration
│   │   ├── validators.py      # Input validation
│   │   └── constants.py       # Unit types, categories
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_services.py
│       └── test_unit_converter.py
├── data/                       # Created at runtime
│   └── bake_tracker.db      # SQLite database (gitignored)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── USER_GUIDE.md
│   └── SCHEMA.md
├── .gitignore
├── README.md
├── REQUIREMENTS.md             # This document
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

## 4. Implementation Phases

### Phase 1: Foundation (MVP)
- Database schema and models
- Basic unit conversion system
- Ingredient CRUD with inventory management
- Simple recipe CRUD
- Basic CustomTkinter UI shell with navigation

### Phase 2: Core Planning
- Bundle and package creation
- Event creation and planning
- Recipient management
- Shopping list generation
- Basic reports

### Phase 3: Production Tracking
- Finished goods production recording
- Package assembly/delivery tracking
- Actual vs planned tracking
- Inventory depletion

### Phase 4: Polish & Reporting
- Advanced reports and analysis
- CSV export functionality
- Undo system refinement
- UI polish and usability improvements
- Comprehensive testing

### Phase 5: Nice-to-Haves
- PDF export for reports
- Inventory snapshot comparison tool
- Recipe scaling (if needed later)
- Bulk import from CSV

---

## 5. Key Technical Considerations

### 5.1 Unit Conversion Strategy

**Challenge:** Ingredients purchased in one unit (e.g., 50 lb bags) consumed in another (e.g., cups).

**Solution:**
- Each ingredient has `purchase_unit`, `recipe_unit`, and `conversion_factor`
- Example: Flour
  - Purchase unit: "bag" (50 lb)
  - Recipe unit: "cup"
  - Conversion factor: 200 (1 bag = 200 cups)
- Standard conversion table for common conversions (lb to oz, kg to g, etc.)
- User can override with custom conversion factors
- Recipe costs calculated: (recipe quantity in recipe units) ÷ (conversion factor) × (unit cost in purchase units)

### 5.2 Inventory Snapshot Strategy

**Challenge:** Multiple events may overlap temporally but need independent planning.

**Solution:**
- Snapshots capture ingredient quantities at a point in time
- Events reference a snapshot for planning (not live inventory)
- Actual consumption during production updates live inventory
- User can create new snapshot anytime to reflect current state
- Shopping lists compare planned needs vs snapshot quantities

### 5.3 Cost Calculation Hierarchy

```
Ingredient (unit cost) 
  ↓ (used in)
Recipe (calculated cost = sum of ingredient costs)
  ↓ (produces)
Finished Good (cost = recipe cost ÷ yield)
  ↓ (bundled in)
Bundle (cost = sum of finished good costs)
  ↓ (included in)
Package (cost = sum of bundle costs)
  ↓ (given to)
Recipient (total cost = sum of package costs)
```

### 5.4 Database Relationships

- **Ingredients** ↔ **Recipes**: Many-to-many (junction table with quantity/unit)
- **Recipes** → **Finished Goods**: One-to-many
- **Finished Goods** ↔ **Bundles**: Many-to-many (junction table with quantity)
- **Bundles** ↔ **Packages**: Many-to-many (junction table with quantity)
- **Packages** ↔ **Recipients**: Many-to-many through **Event Assignments**
- **Events** → **Inventory Snapshot**: Many-to-one
- **Events** → **Event Assignments**: One-to-many

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

## 7. Success Criteria

**Phase 1 Success:**
- User can add ingredients with purchase/recipe units
- User can create recipes with ingredients
- Basic UI navigates between Inventory and Recipes
- Database persists data correctly

**Phase 2 Success:**
- User can plan an event with packages for recipients
- System calculates shopping list with shortfall
- Reports show event summary

**Phase 3 Success:**
- User can track production and mark packages delivered
- System shows planned vs actual

**Final Success:**
- Application reduces planning time by 50% vs spreadsheet
- Zero data loss or corruption
- User successfully completes one full holiday season cycle
- All Phase 1-4 features working reliably

---

## 8. User Workflows (Primary Use Cases)

### Workflow 1: Annual Inventory Update
1. Open Inventory tab
2. Review last year's inventory
3. Adjust quantities for each ingredient
4. Update prices for repurchased items
5. Add new ingredients purchased
6. Create inventory snapshot for new season

### Workflow 2: Create New Recipe
1. Open Recipes tab
2. Click "Add Recipe"
3. Enter name, category, source, time
4. Add ingredients with quantities and units
5. Specify yield (e.g., "24 cookies")
6. View calculated cost
7. Save recipe

### Workflow 3: Plan Holiday Event
1. Open Events tab, create new event (e.g., "Christmas 2025")
2. Select inventory snapshot
3. Create/select gift packages
4. Assign packages to recipients
5. Review shopping list (shortfall report)
6. Export shopping list to CSV
7. Shop for missing ingredients

### Workflow 4: Track Production
1. Bake items, record production in Finished Goods
2. Assemble packages, mark as complete
3. Deliver packages, mark delivered with date
4. View planned vs actual report
5. Note variations for next year

---

## 9. Open Questions & Future Enhancements

**Open Questions:**
- Default categories for ingredients? (Flour/Grains, Sugar/Sweeteners, Dairy, Chocolate, Nuts, Spices, Fats/Oils, Other)
- Default categories for recipes? (Cookies, Cakes, Candies, Breads, Bars, Other)
- Should system auto-deplete inventory on production recording, or manual?
- Preferred date format for UI?

**Future Enhancement Ideas:**
- Mobile companion app for shopping list
- Recipe import from URL
- Nutrition information tracking
- Allergen tagging
- Cost trend analysis over years
- Recipe rating/favorites
- Timer integration for baking
- Photo attachments for finished goods

---

## Document History

- **v1.0** - Initial draft based on user stories
- **v1.1** - Updated with technical decisions: CustomTkinter, unit conversion strategy, inventory snapshots, clarified requirements based on user Q&A

**Document Status:** Approved for implementation

**Next Step:** Begin Phase 1 implementation with Claude Code