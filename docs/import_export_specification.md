# Import/Export Specification for Ingredients and Recipes

**Version:** 1.0
**Date:** 2025-11-04
**Status:** Design Specification (Not Implemented)

## Purpose

This specification defines the import/export format for ingredients and recipes in the Seasonal Baking Tracker. The primary goals are:

1. **Testing Efficiency**: Capture ingredient and recipe data during testing for reuse
2. **AI Generation**: Enable AI tools to generate bulk import files, reducing manual data entry
3. **Data Portability**: Allow backup, migration, and sharing of recipe collections
4. **Batch Operations**: Support bulk import of large ingredient/recipe sets

## Supported Formats

### Primary Format: JSON

**Rationale**: JSON is chosen as the primary format because:
- Structured and hierarchical (handles nested recipe ingredients well)
- Human-readable and editable
- Easy to generate via AI tools
- Native Python support (no additional libraries)
- Preserves data types (numbers, strings, booleans)

### Alternative Format: CSV

**Rationale**: CSV as a secondary format for:
- Simpler ingredient-only imports
- Spreadsheet compatibility (Excel, Google Sheets)
- Quick manual edits

**Limitation**: CSV has difficulty representing nested recipe-ingredient relationships, so it's best suited for ingredient imports only.

## JSON Schema Specifications

### 1. Ingredients Import/Export

#### Single Ingredient Schema

```json
{
  "name": "All-Purpose Flour",
  "brand": "King Arthur",
  "category": "Flour",
  "purchase_quantity": 25.0,
  "purchase_unit": "lb",
  "quantity": 2.0,
  "unit_cost": 18.99,
  "package_type": "bag",
  "volume_equivalents": [
    {
      "volume_unit": "cup",
      "volume_quantity": 1.0,
      "weight_quantity": 120.0,
      "weight_unit": "g"
    }
  ],
  "notes": "Store in cool, dry place"
}
```

#### Bulk Ingredients File

```json
{
  "version": "1.0",
  "export_date": "2025-11-04T12:00:00Z",
  "source": "Seasonal Baking Tracker v0.1.0",
  "ingredients": [
    {
      "name": "All-Purpose Flour",
      "brand": "King Arthur",
      "category": "Flour",
      "purchase_quantity": 25.0,
      "purchase_unit": "lb",
      "quantity": 2.0,
      "unit_cost": 18.99,
      "package_type": "bag",
      "volume_equivalents": [
        {
          "volume_unit": "cup",
          "volume_quantity": 1.0,
          "weight_quantity": 120.0,
          "weight_unit": "g"
        }
      ],
      "notes": "Store in cool, dry place"
    },
    {
      "name": "White Granulated Sugar",
      "brand": "Costco",
      "category": "Sugar",
      "purchase_quantity": 25.0,
      "purchase_unit": "lb",
      "quantity": 1.5,
      "unit_cost": 16.99,
      "package_type": "bag",
      "volume_equivalents": [
        {
          "volume_unit": "cup",
          "volume_quantity": 1.0,
          "weight_quantity": 200.0,
          "weight_unit": "g"
        }
      ]
    }
  ]
}
```

**Field Specifications:**

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | Yes | Max 200 chars | Must be unique per brand |
| `brand` | string | No | Max 200 chars | Optional brand identifier |
| `category` | string | Yes | Valid category | Must match INGREDIENT_CATEGORIES |
| `purchase_quantity` | number | Yes | > 0 | Amount per package |
| `purchase_unit` | string | Yes | Valid unit | Standard unit (lb, oz, g, kg, etc.) |
| `quantity` | number | Yes | >= 0 | Number of packages in inventory |
| `unit_cost` | number | Yes | >= 0 | Cost per package |
| `package_type` | string | No | Max 50 chars | bag, box, jar, etc. |
| `volume_equivalents` | array | No | See below | Volume-weight conversions |
| `notes` | string | No | Max 2000 chars | Additional notes |

**Volume Equivalents Sub-Schema:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `volume_unit` | string | Yes | Valid volume unit (cup, tbsp, tsp, etc.) |
| `volume_quantity` | number | Yes | > 0 |
| `weight_quantity` | number | Yes | > 0 |
| `weight_unit` | string | Yes | Valid weight unit (g, oz, lb, kg) |

### 2. Recipes Import/Export

#### Single Recipe Schema

```json
{
  "name": "Chocolate Chip Cookies",
  "category": "Cookies",
  "source": "Grandma's Recipe Box",
  "yield_quantity": 24,
  "yield_unit": "cookies",
  "yield_description": "2-inch diameter cookies",
  "estimated_time_minutes": 45,
  "notes": "Flatten slightly before baking",
  "ingredients": [
    {
      "ingredient_name": "All-Purpose Flour",
      "ingredient_brand": "King Arthur",
      "quantity": 2.5,
      "unit": "cup",
      "notes": "Sifted"
    },
    {
      "ingredient_name": "White Granulated Sugar",
      "ingredient_brand": "Costco",
      "quantity": 1.0,
      "unit": "cup"
    },
    {
      "ingredient_name": "Semi-Sweet Chocolate Chips",
      "ingredient_brand": "Nestle",
      "quantity": 2.0,
      "unit": "cup"
    }
  ]
}
```

#### Bulk Recipes File

```json
{
  "version": "1.0",
  "export_date": "2025-11-04T12:00:00Z",
  "source": "Seasonal Baking Tracker v0.1.0",
  "recipes": [
    {
      "name": "Chocolate Chip Cookies",
      "category": "Cookies",
      "source": "Grandma's Recipe Box",
      "yield_quantity": 24,
      "yield_unit": "cookies",
      "yield_description": "2-inch diameter cookies",
      "estimated_time_minutes": 45,
      "notes": "Flatten slightly before baking",
      "ingredients": [
        {
          "ingredient_name": "All-Purpose Flour",
          "ingredient_brand": "King Arthur",
          "quantity": 2.5,
          "unit": "cup",
          "notes": "Sifted"
        },
        {
          "ingredient_name": "White Granulated Sugar",
          "ingredient_brand": "Costco",
          "quantity": 1.0,
          "unit": "cup"
        }
      ]
    },
    {
      "name": "Sugar Cookies",
      "category": "Cookies",
      "yield_quantity": 36,
      "yield_unit": "cookies",
      "estimated_time_minutes": 60,
      "ingredients": [
        {
          "ingredient_name": "All-Purpose Flour",
          "quantity": 3.0,
          "unit": "cup"
        }
      ]
    }
  ]
}
```

**Recipe Field Specifications:**

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | Yes | Max 200 chars | Must be unique |
| `category` | string | Yes | Valid category | Must match RECIPE_CATEGORIES |
| `source` | string | No | Max 500 chars | Recipe origin |
| `yield_quantity` | number | Yes | > 0 | Amount produced |
| `yield_unit` | string | Yes | Max 50 chars | cookies, cakes, servings, etc. |
| `yield_description` | string | No | Max 200 chars | Size/portion details |
| `estimated_time_minutes` | integer | No | >= 0 | Prep + bake time |
| `notes` | string | No | Max 2000 chars | Instructions, tips |
| `ingredients` | array | Yes | Min 1 item | Recipe ingredient list |

**Recipe Ingredient Sub-Schema:**

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `ingredient_name` | string | Yes | Max 200 chars | Must match existing ingredient |
| `ingredient_brand` | string | No | Max 200 chars | For disambiguation if needed |
| `quantity` | number | Yes | > 0 | Amount needed |
| `unit` | string | Yes | Valid unit | Must be valid unit type |
| `notes` | string | No | Max 500 chars | Preparation notes (sifted, melted, etc.) |

### 3. Combined Import File

For convenience, a single file can contain both ingredients and recipes:

```json
{
  "version": "1.0",
  "export_date": "2025-11-04T12:00:00Z",
  "source": "Seasonal Baking Tracker v0.1.0",
  "ingredients": [
    { /* ingredient objects */ }
  ],
  "recipes": [
    { /* recipe objects */ }
  ]
}
```

## CSV Format Specification

### Ingredients CSV

**File**: `ingredients.csv`

```csv
name,brand,category,purchase_quantity,purchase_unit,quantity,unit_cost,package_type,notes
All-Purpose Flour,King Arthur,Flour,25.0,lb,2.0,18.99,bag,"Store in cool, dry place"
White Granulated Sugar,Costco,Sugar,25.0,lb,1.5,16.99,bag,
Semi-Sweet Chocolate Chips,Nestle,Chocolate/Candies,72.0,oz,0.5,12.99,bag,
```

**Limitations:**
- Cannot represent volume equivalents (would need separate CSV)
- Quotes required for fields containing commas
- No nested structures

### Recipes CSV (Not Recommended)

Recipes are **not suitable** for CSV format due to:
- One-to-many relationship (recipe has multiple ingredients)
- Would require either:
  - Multiple rows per recipe (confusing, error-prone)
  - Separate CSV files (recipes.csv + recipe_ingredients.csv with foreign keys)
  - Column explosion (ingredient1, ingredient2, etc.)

**Recommendation**: Use JSON for recipe import/export.

## Import Process Flow

### High-Level Import Flow

```
1. File Selection (UI)
   ↓
2. Format Detection (JSON/CSV)
   ↓
3. Schema Validation
   ↓
4. Duplicate Detection
   ↓
5. Dependency Resolution (Recipes → Ingredients)
   ↓
6. Conflict Resolution (UI Prompt)
   ↓
7. Database Transaction
   ↓
8. Import Report (Success/Errors)
```

### Validation Steps

#### Step 1: Schema Validation
- Verify JSON structure matches specification
- Check required fields present
- Validate data types
- Check field constraints (max length, min/max values)

#### Step 2: Business Rule Validation
- Verify categories against valid lists
- Verify units against valid lists
- Check for logical consistency (purchase_quantity > 0, etc.)
- Validate ingredient references in recipes exist

#### Step 3: Duplicate Detection

**Ingredients:**
- Check for existing ingredient with same `name` + `brand` combination
- Options:
  - Skip (keep existing)
  - Replace (overwrite existing)
  - Update quantity only (add to existing inventory)
  - Rename (create as new)

**Recipes:**
- Check for existing recipe with same `name`
- Options:
  - Skip (keep existing)
  - Replace (overwrite existing)
  - Rename (create as new)

#### Step 4: Dependency Resolution

For recipes:
1. Identify all referenced ingredients
2. Check if ingredients exist in database
3. If missing:
   - **Option A**: Auto-create placeholder ingredients (with user confirmation)
   - **Option B**: Mark recipe as "pending" until ingredients added
   - **Option C**: Fail import with error message

### Error Handling Strategy

**Error Categories:**

1. **Fatal Errors** (stop import):
   - Invalid JSON syntax
   - Unsupported version
   - Missing required top-level fields

2. **Record Errors** (skip record, continue):
   - Invalid field values
   - Constraint violations
   - Missing required fields
   - Invalid references

3. **Warnings** (import with notification):
   - Duplicates found
   - Optional fields missing
   - Category not in standard list (but valid)

**Error Report Format:**

```json
{
  "import_status": "partial_success",
  "total_records": 50,
  "successful": 45,
  "skipped": 3,
  "failed": 2,
  "errors": [
    {
      "record_type": "ingredient",
      "record_name": "Unknown Flour",
      "error_type": "validation_error",
      "error_message": "Invalid category: 'FlourTypes'. Must be one of: Flour, Sugar, Dairy, ...",
      "line_number": 15
    },
    {
      "record_type": "recipe",
      "record_name": "Chocolate Cake",
      "error_type": "missing_dependency",
      "error_message": "Ingredient 'Dutch Cocoa' not found in database",
      "line_number": 42
    }
  ],
  "warnings": [
    {
      "record_type": "ingredient",
      "record_name": "All-Purpose Flour",
      "warning_type": "duplicate",
      "warning_message": "Ingredient already exists. Skipped.",
      "line_number": 3
    }
  ]
}
```

## Export Process Flow

### Export Options

1. **Full Export**: All ingredients and recipes
2. **Filtered Export**:
   - By category
   - By date range
   - Selected items only
3. **Template Export**: Empty schema for AI generation

### Export Format Options

```python
export_options = {
    "format": "json",  # or "csv" (ingredients only)
    "include_ingredients": True,
    "include_recipes": True,
    "include_metadata": True,  # version, date, source
    "pretty_print": True,  # formatted JSON
    "filter": {
        "ingredient_categories": ["Flour", "Sugar"],
        "recipe_categories": ["Cookies"],
        "date_added_after": "2025-01-01"
    }
}
```

## Implementation Requirements

### 1. File I/O Layer

**Responsibilities:**
- Read/write JSON files
- Read/write CSV files
- Character encoding handling (UTF-8)
- Large file handling (streaming for huge imports)

**Implementation Notes:**
- Use Python's `json` module for JSON
- Use Python's `csv` module for CSV
- Consider `pandas` for advanced CSV operations (optional)
- Implement file size limits to prevent memory issues

**Estimated Effort:** 4-6 hours

### 2. Validation Layer

**Responsibilities:**
- Schema validation against specification
- Business rule validation
- Type checking and conversion
- Constraint validation

**Implementation Notes:**
- Create `validators.py` module
- Use `jsonschema` library for JSON validation (optional)
- Implement custom validators for business rules
- Return detailed validation results with line numbers

**Estimated Effort:** 8-12 hours

### 3. Service Layer Extensions

**New Functions Needed:**

```python
# In inventory_service.py
def import_ingredients_from_json(file_path: str, options: Dict) -> ImportResult
def import_ingredients_from_csv(file_path: str, options: Dict) -> ImportResult
def export_ingredients_to_json(file_path: str, filter_options: Dict) -> ExportResult
def export_ingredients_to_csv(file_path: str, filter_options: Dict) -> ExportResult

# In recipe_service.py
def import_recipes_from_json(file_path: str, options: Dict) -> ImportResult
def export_recipes_to_json(file_path: str, filter_options: Dict) -> ExportResult

# Utility function
def import_bulk_data(file_path: str, options: Dict) -> ImportResult
```

**Estimated Effort:** 12-16 hours

### 4. Duplicate Resolution UI

**Requirements:**
- Dialog to present duplicate conflicts
- Options: Skip, Replace, Update (ingredients only), Rename
- Bulk actions (apply to all duplicates)
- Preview changes before applying

**Implementation Notes:**
- Create custom dialog: `DuplicateResolutionDialog`
- Display side-by-side comparison (existing vs. importing)
- Support "Apply to all" checkbox for batch operations

**Estimated Effort:** 6-8 hours

### 5. Import/Export UI Components

**Import Dialog:**
- File picker
- Format selection (auto-detect)
- Import options:
  - Duplicate handling strategy
  - Auto-create missing ingredients (for recipes)
  - Validation strictness level
- Progress bar for large imports
- Error/Warning display
- Import summary report

**Export Dialog:**
- File picker (save location)
- Format selection
- Filter options:
  - Select categories
  - Date range
  - Specific item selection
- Export preview (record count)
- Success confirmation

**Implementation Notes:**
- Create `ImportExportDialog` class
- Use threading for long-running imports (avoid UI freeze)
- Implement progress callbacks
- Display results in scrollable text area or table

**Estimated Effort:** 10-14 hours

### 6. Menu Integration

**New Menu Items:**

```
File Menu:
  ├── Import
  │   ├── Import Ingredients...
  │   ├── Import Recipes...
  │   └── Import All (Ingredients + Recipes)...
  └── Export
      ├── Export Ingredients...
      ├── Export Recipes...
      └── Export All...
```

**Keyboard Shortcuts:**
- Import: Ctrl+I
- Export: Ctrl+E

**Estimated Effort:** 2-4 hours

### 7. Testing Requirements

**Unit Tests:**
- Schema validation tests
- Import logic tests (various scenarios)
- Export logic tests
- Error handling tests
- Duplicate detection tests

**Integration Tests:**
- End-to-end import/export roundtrip
- Large file handling (1000+ records)
- Concurrent import handling
- Database transaction rollback on errors

**Test Data:**
- Sample valid import files (small, medium, large)
- Sample invalid import files (various error types)
- Edge case files (empty, single record, max size)

**Estimated Effort:** 12-16 hours

### 8. Documentation

**User Documentation:**
- Import/Export user guide
- File format examples
- Troubleshooting common errors
- AI prompt templates for generating import files

**Developer Documentation:**
- API documentation for import/export functions
- Schema specification (this document)
- Extension guide (adding new fields)

**Estimated Effort:** 4-6 hours

## Total Implementation Estimate

| Component | Hours |
|-----------|-------|
| File I/O Layer | 4-6 |
| Validation Layer | 8-12 |
| Service Layer Extensions | 12-16 |
| Duplicate Resolution UI | 6-8 |
| Import/Export UI | 10-14 |
| Menu Integration | 2-4 |
| Testing | 12-16 |
| Documentation | 4-6 |
| **Total** | **58-82 hours** |

**Recommended Phased Approach:**
- **Phase 1** (20-24 hours): Basic JSON import/export for ingredients only
- **Phase 2** (18-24 hours): Add recipe import/export with dependency resolution
- **Phase 3** (12-16 hours): Add CSV support and advanced filtering
- **Phase 4** (8-10 hours): Polish UI, add duplicate resolution, comprehensive error handling

## AI Generation Prompt Template

To facilitate AI-assisted import file generation:

### Example Prompt for AI

```
Generate a JSON import file for the Seasonal Baking Tracker application with the following requirements:

Format: Use the JSON schema specified in the import/export specification
Ingredients: Create 10 common baking ingredients with realistic:
- Names and brands (US market)
- Categories from: Flour, Sugar, Dairy, Oils/Butters, Chocolate/Candies, Nuts, Spices
- Purchase quantities and costs (Costco/bulk pricing)
- Package types (bag, box, jar, bottle)

Include volume equivalents for ingredients that are commonly measured by volume (flour, sugar).

Output only valid JSON, no markdown formatting.
```

### Example Template File

Create `templates/import_template.json`:

```json
{
  "version": "1.0",
  "export_date": "YYYY-MM-DDTHH:MM:SSZ",
  "source": "Import Template",
  "ingredients": [
    {
      "name": "INGREDIENT_NAME",
      "brand": "BRAND_NAME",
      "category": "CATEGORY",
      "purchase_quantity": 0.0,
      "purchase_unit": "UNIT",
      "quantity": 0.0,
      "unit_cost": 0.00,
      "package_type": "PACKAGE_TYPE",
      "volume_equivalents": [
        {
          "volume_unit": "cup",
          "volume_quantity": 1.0,
          "weight_quantity": 120.0,
          "weight_unit": "g"
        }
      ],
      "notes": "OPTIONAL_NOTES"
    }
  ],
  "recipes": [
    {
      "name": "RECIPE_NAME",
      "category": "CATEGORY",
      "source": "SOURCE",
      "yield_quantity": 0,
      "yield_unit": "UNIT",
      "yield_description": "DESCRIPTION",
      "estimated_time_minutes": 0,
      "notes": "INSTRUCTIONS",
      "ingredients": [
        {
          "ingredient_name": "INGREDIENT_NAME",
          "ingredient_brand": "BRAND_NAME",
          "quantity": 0.0,
          "unit": "UNIT",
          "notes": "PREP_NOTES"
        }
      ]
    }
  ]
}
```

## Security Considerations

### Input Validation
- **File Size Limits**: Prevent DoS via huge files (recommend 10MB max)
- **JSON Depth Limits**: Prevent deeply nested JSON attacks
- **Path Traversal**: Validate file paths to prevent directory traversal
- **Encoding**: Only accept UTF-8 encoding

### Data Sanitization
- Strip/escape special characters in text fields
- Validate URLs if source field contains links
- Prevent SQL injection via parameterized queries (already handled by SQLAlchemy)

### User Permissions
- Confirm destructive operations (Replace duplicates)
- Require admin role for bulk imports (future consideration)
- Log all import/export operations with timestamp and user

## Future Enhancements

### Version 2.0 Considerations

1. **Excel Format Support** (.xlsx)
   - Better for users familiar with spreadsheets
   - Can handle multiple sheets (ingredients, recipes, finished_goods)

2. **Recipe Image Import**
   - Include base64 encoded images in JSON
   - Or reference external image URLs

3. **Ingredient Supplier Data**
   - Purchase history
   - Multiple suppliers per ingredient
   - Price tracking over time

4. **Recipe Variations**
   - Import recipe with multiple variants
   - Share ingredient lists across variants

5. **Batch Import Scheduling**
   - Schedule imports to run automatically
   - Watch folder for new import files

6. **Cloud Sync**
   - Export to cloud storage (Dropbox, Google Drive)
   - Import from shared cloud links

7. **Recipe Sharing Platform**
   - Export to standardized recipe format (Schema.org Recipe)
   - Import from recipe websites (web scraping with permission)

## Appendix A: Valid Categories

### Ingredient Categories
```python
INGREDIENT_CATEGORIES = [
    "Flour", "Sugar", "Dairy", "Oils/Butters", "Nuts",
    "Spices", "Chocolate/Candies", "Cocoa Powders",
    "Dried Fruits", "Extracts", "Syrups", "Alcohol", "Misc"
]
```

### Recipe Categories
```python
RECIPE_CATEGORIES = [
    "Cookies", "Cakes", "Candies", "Bars", "Brownies",
    "Breads", "Pastries", "Pies", "Tarts", "Other"
]
```

## Appendix B: Valid Units

### Weight Units
```python
WEIGHT_UNITS = ["oz", "lb", "g", "kg"]
```

### Volume Units
```python
VOLUME_UNITS = ["tsp", "tbsp", "cup", "ml", "l", "fl oz", "pt", "qt", "gal"]
```

### Count Units
```python
COUNT_UNITS = ["each", "count", "piece", "dozen"]
```

### Package Units
```python
PACKAGE_UNITS = ["bag", "box", "bar", "bottle", "can", "jar", "packet", "container", "package", "case"]
```

## Appendix C: Example Files

Example import files are provided in the `examples/import/` directory:

- `simple_ingredients.json` - 5 basic ingredients
- `complete_ingredients.json` - 20 ingredients with all fields
- `simple_recipes.json` - 3 basic recipes
- `complete_recipes.json` - 10 recipes with full details
- `combined_import.json` - Ingredients + Recipes in one file
- `test_errors.json` - File with intentional errors for testing
- `ai_generated_sample.json` - Example of AI-generated import file

---

**Document Status**: Design Specification - Ready for Implementation
**Next Steps**: Review with stakeholders, prioritize phases, begin Phase 1 implementation
