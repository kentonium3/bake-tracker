# Phase 1 Implementation Plan

## Overview

Phase 1 establishes the foundation of the Seasonal Baking Tracker by implementing core data models, basic business logic, and a functional UI shell. This MVP will allow users to manage ingredients and recipes with a working database and user interface.

**Goal:** Create a working application where users can add ingredients, create recipes, and see calculated costs.

**Estimated Timeline:** 2-3 weeks

---

## Phase 1 Components

1. Database schema and models
2. Basic unit conversion system
3. Ingredient CRUD with inventory management
4. Simple recipe CRUD
5. Basic CustomTkinter UI shell with navigation

---

## Implementation Strategy

### Approach: Bottom-Up with Incremental Testing

We'll build from the data layer up to the UI, testing each component before moving to the next. This ensures a solid foundation and allows for early validation of core concepts (especially unit conversion logic).

### Order of Implementation

```
Step 1: Foundation & Configuration
  └─> Step 2: Database Models
       └─> Step 3: Unit Conversion System
            └─> Step 4: Service Layer (Business Logic)
                 └─> Step 5: UI Shell & Basic Navigation
                      └─> Step 6: Ingredient Management UI
                           └─> Step 7: Recipe Management UI
                                └─> Step 8: Integration & Testing
```

---

## Detailed Implementation Plan

### Step 1: Foundation & Configuration (Day 1)

**Objective:** Set up database configuration and utility modules.

#### Tasks:

**1.1 Create Database Configuration**
- File: `src/utils/config.py`
- Define database path (user's Documents folder or data/)
- Configuration class for app settings
- Environment-based configuration (dev vs. production)

**1.2 Create Constants Module**
- File: `src/utils/constants.py`
- Define unit types: `WEIGHT_UNITS`, `VOLUME_UNITS`, `COUNT_UNITS`
- Define ingredient categories
- Define recipe categories
- UI constants (colors, fonts, sizes)

**1.3 Create Validators Module**
- File: `src/utils/validators.py`
- Validation functions for:
  - Non-negative numbers
  - Required fields
  - Valid unit types
  - Email/text formats

**1.4 Create Database Service**
- File: `src/services/database.py`
- Database connection manager
- Session factory
- Initialize database function
- WAL mode configuration
- Foreign key enforcement

**Deliverables:**
- [ ] `src/utils/config.py` - Application configuration
- [ ] `src/utils/constants.py` - System constants
- [ ] `src/utils/validators.py` - Input validation
- [ ] `src/services/database.py` - Database connection
- [ ] Unit tests: `src/tests/test_validators.py`

**Validation:** Run database initialization, create connection, verify SQLite settings.

---

### Step 2: Database Models (Days 2-3)

**Objective:** Implement SQLAlchemy models for Phase 1 entities.

#### Priority Order:
1. Base model class (common functionality)
2. Ingredient model (core entity)
3. Recipe and RecipeIngredient models (relationships)
4. InventorySnapshot models (for future use)

#### Tasks:

**2.1 Create Base Model**
- File: `src/models/base.py`
- SQLAlchemy declarative base
- Common fields (id, created_at, updated_at)
- Utility methods (to_dict, from_dict)

**2.2 Create Ingredient Model**
- File: `src/models/ingredient.py`
- All fields per SCHEMA.md:
  - name, brand, category
  - purchase_unit, purchase_unit_size, recipe_unit
  - conversion_factor
  - quantity, unit_cost
  - last_updated, notes
- Validation constraints
- Index definitions
- Calculated property for recipe unit quantity

**2.3 Create Recipe Models**
- File: `src/models/recipe.py`
- Recipe model with all fields
- RecipeIngredient junction table
- Relationships configured
- Cascade rules defined

**2.4 Create InventorySnapshot Models**
- File: `src/models/inventory_snapshot.py`
- Snapshot model
- SnapshotIngredient junction table
- Basic implementation (won't use until Phase 2)

**2.5 Database Initialization Script**
- Update `src/services/database.py`
- Create all tables
- Add indexes
- Sample data function (for testing)

**Deliverables:**
- [ ] `src/models/base.py` - Base model class
- [ ] `src/models/ingredient.py` - Ingredient model
- [ ] `src/models/recipe.py` - Recipe and junction models
- [ ] `src/models/inventory_snapshot.py` - Snapshot models
- [ ] Unit tests: `src/tests/test_models.py`
- [ ] Integration test: Create/read/update/delete each model

**Validation:**
- Create database tables
- Insert sample ingredient
- Query and verify data
- Test relationships (recipe with ingredients)

---

### Step 3: Unit Conversion System (Day 4)

**Objective:** Implement conversion logic between units.

#### Tasks:

**3.1 Create Unit Converter**
- File: `src/services/unit_converter.py`
- Standard conversion tables:
  - Weight: oz ↔ lb ↔ g ↔ kg
  - Volume: tsp ↔ tbsp ↔ cup ↔ ml ↔ l
- Conversion functions:
  - `convert_standard_units(value, from_unit, to_unit)`
  - `convert_ingredient_units(ingredient, quantity, to_unit)`
- Helper function to display conversion (e.g., "1 bag = 200 cups")

**3.2 Cost Calculation Utilities**
- Same file or `src/services/cost_calculator.py`
- Calculate ingredient cost in recipe:
  - `calculate_ingredient_cost(ingredient, recipe_quantity, recipe_unit)`
  - Formula: `(unit_cost / conversion_factor) * recipe_quantity`
- Calculate recipe total cost

**Deliverables:**
- [ ] `src/services/unit_converter.py` - Conversion logic
- [ ] Unit tests: `src/tests/test_unit_converter.py` (extensive tests!)
  - Test all standard conversions
  - Test custom ingredient conversions
  - Test edge cases (zero, negative, invalid units)
  - Test cost calculations

**Validation:**
- Convert 1 lb to oz (should be 16)
- Convert 1 cup to ml (should be ~237)
- Test ingredient conversion: 2 cups from bag with factor 200 = 0.01 bags
- Verify cost calculation accuracy

---

### Step 4: Service Layer (Days 5-6)

**Objective:** Implement business logic for ingredient and recipe management.

#### Tasks:

**4.1 Create Inventory Service**
- File: `src/services/inventory_service.py`
- CRUD operations:
  - `create_ingredient(data)` - Add new ingredient
  - `get_ingredient(id)` - Retrieve by ID
  - `get_all_ingredients(filters)` - List with optional filtering
  - `update_ingredient(id, data)` - Update fields
  - `delete_ingredient(id)` - Delete with dependency check
- Search/filter functions:
  - By category
  - By name (partial match)
  - Low stock (configurable threshold)
- Validation before database operations
- Error handling with meaningful messages

**4.2 Create Recipe Service**
- File: `src/services/recipe_service.py`
- CRUD operations:
  - `create_recipe(recipe_data, ingredients_data)` - Create recipe with ingredients
  - `get_recipe(id)` - Retrieve with ingredients
  - `get_all_recipes(filters)` - List recipes
  - `update_recipe(id, data)` - Update recipe and ingredients
  - `delete_recipe(id)` - Delete with confirmations
- Cost calculation:
  - `calculate_recipe_cost(recipe_id)` - Total cost
  - `get_recipe_with_costs(recipe_id)` - Recipe with per-ingredient costs
- Filter functions:
  - By category
  - By ingredient (recipes using specific ingredient)
  - By name search

**4.3 Service Layer Utilities**
- Exception classes: `IngredientNotFound`, `RecipeNotFound`, etc.
- Common query helpers
- Transaction management

**Deliverables:**
- [ ] `src/services/inventory_service.py` - Ingredient business logic
- [ ] `src/services/recipe_service.py` - Recipe business logic
- [ ] Unit tests: `src/tests/test_services.py`
  - Test each CRUD operation
  - Test filters and searches
  - Test cost calculations
  - Test error conditions
- [ ] Integration tests with database

**Validation:**
- Create ingredient via service
- Update quantity
- Create recipe with 3 ingredients
- Calculate recipe cost
- Verify cost matches manual calculation

---

### Step 5: UI Shell & Navigation (Day 7)

**Objective:** Create main application window with tabbed navigation.

#### Tasks:

**5.1 Create Main Entry Point**
- File: `src/main.py`
- Application initialization
- Database initialization check
- Launch main window
- Error handling for startup failures

**5.2 Create Main Window**
- File: `src/ui/main_window.py`
- CustomTkinter main window setup
- Title, size, icon
- Menu bar (File → Exit, Help → About)
- Status bar at bottom
- Tabbed interface using CTkTabview:
  - Dashboard tab (placeholder)
  - Inventory tab (placeholder)
  - Recipes tab (placeholder)
  - Bundles tab (grayed out)
  - Packages tab (grayed out)
  - Recipients tab (grayed out)
  - Events tab (grayed out)
  - Reports tab (grayed out)

**5.3 Create Dashboard Tab**
- File: `src/ui/dashboard_tab.py`
- Simple placeholder showing:
  - Welcome message
  - Phase 1 status
  - Quick stats (ingredient count, recipe count)
  - Recent activity (placeholder for now)

**5.4 Create Reusable Widgets**
- File: `src/ui/widgets/dialogs.py`
  - Confirmation dialog
  - Error dialog
  - Success dialog
- File: `src/ui/widgets/search_bar.py`
  - Search/filter bar component
- File: `src/ui/widgets/data_table.py`
  - Table widget for displaying lists (will be used extensively)

**Deliverables:**
- [ ] `src/main.py` - Application entry point
- [ ] `src/ui/main_window.py` - Main window with tabs
- [ ] `src/ui/dashboard_tab.py` - Simple dashboard
- [ ] `src/ui/widgets/dialogs.py` - Common dialogs
- [ ] `src/ui/widgets/search_bar.py` - Search component
- [ ] `src/ui/widgets/data_table.py` - Table widget
- [ ] Manual testing: App launches, tabs switch

**Validation:**
- Run application
- Window opens with proper size
- All tabs visible (some disabled)
- Can switch between active tabs
- Status bar shows information
- App closes cleanly

---

### Step 6: Ingredient Management UI (Days 8-9)

**Objective:** Complete ingredient CRUD functionality in UI.

#### Tasks:

**6.1 Create Inventory Tab**
- File: `src/ui/inventory_tab.py`
- Layout:
  - Top: Search bar, Add button, Refresh button
  - Center: Data table showing ingredients:
    - Columns: Name, Brand, Category, Quantity, Unit Cost, Total Value
  - Bottom: Edit, Delete, View Details buttons
- Connect to `inventory_service`
- Load and display ingredients
- Search/filter functionality

**6.2 Create Ingredient Form Dialog**
- File: `src/ui/widgets/ingredient_form.py` (or inline in inventory_tab.py)
- Form fields:
  - Name (required)
  - Brand
  - Category (dropdown from constants)
  - Purchase Unit (dropdown)
  - Purchase Unit Size (text)
  - Recipe Unit (dropdown)
  - Conversion Factor (number with helper)
  - Quantity (number)
  - Unit Cost (currency)
  - Notes (text area)
- Validation on save
- Show conversion helper: "1 [purchase_unit] = X [recipe_units]"
- Two modes: Add New, Edit Existing

**6.3 Ingredient Details View**
- Show all ingredient information
- Display calculated values:
  - Total value (quantity × unit_cost)
  - Available recipe units (quantity × conversion_factor)
- Show recipes using this ingredient (future enhancement)
- Edit and Delete buttons

**6.4 Delete Confirmation**
- Check for dependencies (recipes using ingredient)
- Show warning if used
- Confirm deletion
- Cascade options

**Deliverables:**
- [ ] `src/ui/inventory_tab.py` - Inventory management UI
- [ ] Ingredient form (add/edit)
- [ ] Ingredient details view
- [ ] Delete confirmation
- [ ] Manual testing checklist

**Validation:**
- Add a new ingredient with all fields
- Search for ingredient by name
- Edit ingredient quantity
- View ingredient details
- Delete unused ingredient
- Verify can't delete ingredient used in recipe (once recipes exist)

---

### Step 7: Recipe Management UI (Days 10-11)

**Objective:** Complete recipe CRUD functionality in UI.

#### Tasks:

**7.1 Create Recipe Tab**
- File: `src/ui/recipe_tab.py`
- Layout:
  - Top: Search bar, Add Recipe button, Filter by Category
  - Center: Data table showing recipes:
    - Columns: Name, Category, Yield, Cost, Time
  - Bottom: Edit, Delete, View buttons
- Connect to `recipe_service`
- Load and display recipes

**7.2 Create Recipe Form Dialog**
- File: `src/ui/widgets/recipe_form.py`
- Multi-step or tabbed form:
  - **Basic Info:**
    - Name (required)
    - Category (dropdown)
    - Source
    - Estimated time
    - Yield (quantity, unit, description)
    - Notes
  - **Ingredients Section:**
    - List of ingredient entries
    - Each entry: Dropdown (ingredient), Quantity, Unit
    - Add Ingredient button
    - Remove Ingredient button
    - Unit dropdown filtered to ingredient's recipe_unit
  - **Cost Display:**
    - Show calculated cost as ingredients are added
    - Per-ingredient cost breakdown
    - Total recipe cost
    - Cost per unit (cost / yield)
- Validation:
  - At least one ingredient required
  - Valid quantities
  - Units match ingredient's recipe unit
- Two modes: Add New, Edit Existing

**7.3 Recipe Details View**
- Show complete recipe information
- Ingredient list with quantities and costs
- Total cost prominently displayed
- Cost per unit
- Edit and Delete buttons
- "Use in New Recipe" button (clone)

**7.4 Recipe Cost Calculation Integration**
- Real-time cost updates as ingredients added
- Color coding for cost ranges (optional)
- Alert if ingredient missing cost data

**Deliverables:**
- [ ] `src/ui/recipe_tab.py` - Recipe management UI
- [ ] `src/ui/widgets/recipe_form.py` - Recipe form
- [ ] Recipe details view
- [ ] Cost calculation display
- [ ] Manual testing checklist

**Validation:**
- Add a new recipe with 3 ingredients
- Verify cost calculation matches expected
- Edit recipe to add another ingredient
- Delete ingredient from recipe
- Search for recipe by name
- Filter recipes by category
- Delete recipe

---

### Step 8: Integration, Testing & Polish (Days 12-14)

**Objective:** Comprehensive testing, bug fixes, and final polish.

#### Tasks:

**8.1 Integration Testing**
- Complete workflow tests:
  - Add 5 ingredients
  - Create 3 recipes using those ingredients
  - Edit ingredient price, verify recipe cost updates
  - Delete ingredient not in use
  - Try to delete ingredient in use (should fail)
- Test error conditions:
  - Invalid data entry
  - Database connection issues
  - Empty states (no data)
- Test edge cases:
  - Very large numbers
  - Zero quantities
  - Special characters in names

**8.2 Unit Test Coverage**
- Achieve >70% coverage on services layer
- Run: `dev test-cov`
- Fill gaps in test coverage
- Document known limitations

**8.3 Code Quality**
- Run linters: `dev lint`
- Fix all flake8 issues
- Fix mypy type issues (or add ignores with comments)
- Format code: `dev format`
- Add docstrings to all public methods
- Code review (self-review against requirements)

**8.4 UI Polish**
- Consistent styling across all windows
- Proper error messages (user-friendly)
- Loading indicators where needed
- Keyboard shortcuts (Tab navigation)
- Tooltips on complex fields
- Window sizing and responsiveness
- Icon/logo (if available)

**8.5 Documentation Updates**
- Update CHANGELOG.md with Phase 1 completion
- Screenshot the UI for README.md
- Update USER_GUIDE.md with Phase 1 features
- Add troubleshooting section
- Document known issues/limitations

**8.6 Sample Data**
- Create sample data script: `src/utils/sample_data.py`
- Populate with realistic ingredients and recipes
- Help with testing and demos

**Deliverables:**
- [ ] All tests passing
- [ ] >70% test coverage on services
- [ ] Zero linting errors
- [ ] Updated documentation
- [ ] Sample data script
- [ ] Phase 1 features list
- [ ] Known issues list

**Validation:**
- Complete end-to-end workflow without errors
- All tests pass
- Linters pass
- Code formatted
- Documentation accurate

---

## Success Criteria (Phase 1 Complete)

### Functional Requirements Met:
- ✅ User can add, edit, delete ingredients
- ✅ User can specify purchase/recipe units with conversion factor
- ✅ User can create recipes with multiple ingredients
- ✅ User can edit recipes (add/remove ingredients)
- ✅ System calculates recipe costs automatically
- ✅ System validates unit compatibility
- ✅ User can search/filter ingredients and recipes
- ✅ Application persists data in SQLite database
- ✅ UI provides tabbed navigation between sections

### Technical Requirements Met:
- ✅ Database schema implemented per SCHEMA.md
- ✅ Unit conversion system working correctly
- ✅ Service layer with clean separation of concerns
- ✅ CustomTkinter UI functional and responsive
- ✅ Test coverage >70% on services
- ✅ Code passes linting
- ✅ All code formatted with black
- ✅ Documentation updated

### User Acceptance:
- ✅ User can complete workflow: add ingredients → create recipe → see cost
- ✅ No crashes or data loss
- ✅ Calculations are accurate
- ✅ UI is intuitive (minimal learning curve)

---

## Risk Mitigation

### Risk 1: Unit Conversion Complexity
- **Mitigation:** Implement and test conversion system early (Step 3)
- **Validation:** Extensive unit tests with known conversions

### Risk 2: CustomTkinter Learning Curve
- **Mitigation:** Start with simple layouts, reference documentation/examples
- **Fallback:** Use standard Tkinter if CustomTkinter issues arise

### Risk 3: Database Design Changes
- **Mitigation:** Implement models early, validate with sample data
- **Plan:** Document any schema changes for migration

### Risk 4: Cost Calculation Errors
- **Mitigation:** Unit tests with manual verification
- **Validation:** Cross-check calculated costs with spreadsheet

### Risk 5: Time Overruns
- **Mitigation:** Focus on MVP features only
- **Defer:** Advanced features (undo, exports, etc.) to later phases

---

## Development Guidelines During Phase 1

### Daily Workflow:
1. Write tests first (TDD) for services
2. Implement feature
3. Run tests: `dev test`
4. Run linters: `dev lint`
5. Format code: `dev format`
6. Commit frequently with clear messages
7. Push to GitHub daily

### Commit Message Format:
```
feat(models): add Ingredient model with validation
fix(ui): correct cost calculation display
test(services): add inventory service tests
docs: update Phase 1 progress in CHANGELOG
```

### Testing Strategy:
- Unit tests for all services and utilities
- Integration tests for database operations
- Manual UI testing (checklist-based)
- Test with realistic data
- Test error conditions

### Code Review Checkpoints:
- After Step 2 (models)
- After Step 4 (services)
- After Step 7 (full UI)
- Before final commit

---

## Next Steps After Phase 1

Once Phase 1 is complete and validated:

1. **User Feedback:** Test with real-world use case
2. **Phase 2 Planning:** Plan bundle, package, and event management
3. **Performance Testing:** Test with 100+ ingredients, 50+ recipes
4. **Backup/Restore:** Add database backup functionality
5. **Enhancement Backlog:** Document nice-to-haves discovered during development

---

## Appendix: Key Files Summary

### Models Layer
```
src/models/
├── __init__.py
├── base.py                    # Base model class
├── ingredient.py              # Ingredient model
├── recipe.py                  # Recipe + RecipeIngredient
└── inventory_snapshot.py      # Snapshot models (basic)
```

### Services Layer
```
src/services/
├── __init__.py
├── database.py                # DB connection & session
├── unit_converter.py          # Unit conversion logic
├── inventory_service.py       # Ingredient CRUD
└── recipe_service.py          # Recipe CRUD
```

### UI Layer
```
src/ui/
├── __init__.py
├── main_window.py             # Main app window
├── dashboard_tab.py           # Dashboard placeholder
├── inventory_tab.py           # Ingredient management
├── recipe_tab.py              # Recipe management
└── widgets/
    ├── __init__.py
    ├── dialogs.py             # Common dialogs
    ├── search_bar.py          # Search component
    ├── data_table.py          # Table widget
    ├── ingredient_form.py     # Ingredient add/edit form
    └── recipe_form.py         # Recipe add/edit form
```

### Utils Layer
```
src/utils/
├── __init__.py
├── config.py                  # App configuration
├── constants.py               # System constants
├── validators.py              # Input validation
└── sample_data.py             # Sample data generator
```

### Tests
```
src/tests/
├── __init__.py
├── test_models.py             # Model tests
├── test_services.py           # Service tests
├── test_unit_converter.py     # Conversion tests
└── test_validators.py         # Validation tests
```

---

**Document Status:** Implementation plan for Phase 1
**Created:** 2025-11-02
**Target Completion:** 2-3 weeks from start
