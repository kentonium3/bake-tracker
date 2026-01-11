# HOTFIX: Add slug Fields to Materials System (F047)

**Urgency**: HIGH - Fix before production use
**Scope**: Minimal schema changes + import/export updates
**Effort**: 2-3 hours implementation
**Risk**: LOW (additive changes only, no breaking changes)

---

## Problem Statement

Current F047 implementation uses `display_name` for import/export references:
- **MUTABLE** field used as **IMMUTABLE** reference
- Renaming a material breaks all imports
- Blocks future multi-user/web/e-commerce evolution

---

## Solution: Add Immutable slug Fields

Add `slug` field to 4 models as **stable references**:
1. MaterialCategory
2. MaterialSubcategory  
3. Material
4. MaterialProduct (optional but recommended)

---

## Schema Changes (Minimal)

### 1. MaterialCategory
```python
class MaterialCategory(BaseModel):
    # Existing fields (unchanged)
    id: int
    display_name: str
    notes: str
    created_at: DateTime
    updated_at: DateTime
    
    # NEW FIELD
    slug: str = Column(String(100), unique=True, nullable=False)
```

**Migration:**
```sql
ALTER TABLE material_categories ADD COLUMN slug VARCHAR(100) UNIQUE NOT NULL;
CREATE UNIQUE INDEX idx_material_categories_slug ON material_categories(slug);
```

### 2. MaterialSubcategory
```python
class MaterialSubcategory(BaseModel):
    # Existing fields (unchanged)
    id: int
    category_id: int
    display_name: str
    notes: str
    created_at: DateTime
    updated_at: DateTime
    
    # NEW FIELD
    slug: str = Column(String(100), nullable=False)
    
    # Updated constraint
    __table_args__ = (
        UniqueConstraint('category_id', 'display_name'),
        UniqueConstraint('category_id', 'slug'),  # NEW
    )
```

**Migration:**
```sql
ALTER TABLE material_subcategories ADD COLUMN slug VARCHAR(100) NOT NULL;
CREATE UNIQUE INDEX idx_material_subcategories_slug 
    ON material_subcategories(category_id, slug);
```

### 3. Material
```python
class Material(BaseModel):
    # Existing fields (unchanged)
    id: int
    subcategory_id: int
    display_name: str
    notes: str
    created_at: DateTime
    updated_at: DateTime
    
    # NEW FIELD
    slug: str = Column(String(100), nullable=False)
    
    # Updated constraint
    __table_args__ = (
        UniqueConstraint('subcategory_id', 'display_name'),
        UniqueConstraint('subcategory_id', 'slug'),  # NEW
    )
```

**Migration:**
```sql
ALTER TABLE materials ADD COLUMN slug VARCHAR(100) NOT NULL;
CREATE UNIQUE INDEX idx_materials_slug 
    ON materials(subcategory_id, slug);
```

### 4. MaterialProduct (Optional)
```python
class MaterialProduct(BaseModel):
    # Existing fields (unchanged)
    id: int
    material_id: int
    display_name: str
    default_unit: str
    inventory_count: Decimal
    current_unit_cost: Decimal
    supplier_id: int
    notes: str
    created_at: DateTime
    updated_at: DateTime
    
    # NEW FIELD (optional but recommended)
    slug: str = Column(String(100), unique=True, nullable=True)  # Nullable for now
```

**Migration:**
```sql
ALTER TABLE material_products ADD COLUMN slug VARCHAR(100) UNIQUE;
CREATE UNIQUE INDEX idx_material_products_slug ON material_products(slug);
```

---

## Import/Export Changes

### Updated Import Format

**BACKWARD COMPATIBLE**: Support both slug AND display_name (slug preferred)

```json
{
  "version": "4.2",
  "material_categories": [
    {
      "slug": "boxes",                    // NEW - preferred reference
      "display_name": "Boxes",
      "notes": "..."
    }
  ],
  "material_subcategories": [
    {
      "category_slug": "boxes",           // NEW - preferred reference
      "slug": "window_boxes",             // NEW
      "display_name": "Window Boxes",
      "notes": "..."
    }
  ],
  "materials": [
    {
      "subcategory_slug": "window_boxes", // NEW - preferred reference
      "slug": "box_window_cake_10x10",    // NEW
      "display_name": "Box Window Cake 10x10",
      "notes": "..."
    }
  ],
  "material_products": [
    {
      "material_slug": "box_window_cake_10x10",  // NEW - preferred reference
      "slug": "amazon_10x10_cake_box_25pk",      // NEW (optional)
      "display_name": "Amazon 10x10 Cake Window Box 25pk",
      "default_unit": "each",
      "supplier": "Amazon",
      "notes": "..."
    }
  ]
}
```

### Import Resolution Logic (Backward Compatible)

```python
def resolve_material_category(reference: dict) -> MaterialCategory:
    """Resolve category by slug (preferred) or display_name (fallback)"""
    
    # Try slug first (preferred)
    if 'slug' in reference:
        category = session.query(MaterialCategory).filter(
            MaterialCategory.slug == reference['slug']
        ).first()
        if category:
            return category
    
    # Fallback to display_name (legacy)
    category = session.query(MaterialCategory).filter(
        MaterialCategory.display_name == reference['display_name']
    ).first()
    
    if category:
        logger.warning(f"Using display_name reference (deprecated): {reference['display_name']}")
        return category
    
    raise ImportError(f"MaterialCategory not found: {reference}")

def resolve_material_subcategory(category_id: int, reference: dict) -> MaterialSubcategory:
    """Resolve subcategory by slug or display_name"""
    
    # Try category_slug + slug first
    if 'category_slug' in reference and 'slug' in reference:
        category = resolve_material_category({'slug': reference['category_slug']})
        subcat = session.query(MaterialSubcategory).filter(
            MaterialSubcategory.category_id == category.id,
            MaterialSubcategory.slug == reference['slug']
        ).first()
        if subcat:
            return subcat
    
    # Fallback to display_name
    subcat = session.query(MaterialSubcategory).filter(
        MaterialSubcategory.category_id == category_id,
        MaterialSubcategory.display_name == reference['display_name']
    ).first()
    
    if subcat:
        logger.warning(f"Using display_name reference (deprecated)")
        return subcat
    
    raise ImportError(f"MaterialSubcategory not found: {reference}")

# Similar for Material and MaterialProduct...
```

---

## Service Layer Changes

### Add Slug Generation Helper

```python
def generate_slug(display_name: str) -> str:
    """Generate URL-safe slug from display_name"""
    import re
    
    # Lowercase
    slug = display_name.lower()
    
    # Replace spaces and special chars with underscores
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '_', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    
    return slug

# Example:
# "Box Window Cake 10x10" → "box_window_cake_10x10"
# "3/16\" Curling Ribbon" → "3_16_curling_ribbon"
```

### Add Slug Validation

```python
def validate_slug(slug: str) -> bool:
    """Validate slug format"""
    import re
    
    # Lowercase alphanumeric + underscore/hyphen only
    pattern = r'^[a-z0-9_-]+$'
    
    if not re.match(pattern, slug):
        raise ValueError(f"Invalid slug format: {slug}")
    
    if len(slug) > 100:
        raise ValueError(f"Slug too long (max 100 chars): {slug}")
    
    return True
```

### Update Create Services

```python
class MaterialCategoryService:
    def create_category(self, display_name: str, slug: str = None, notes: str = None):
        """Create category with auto-generated slug if not provided"""
        
        # Auto-generate slug if not provided
        if not slug:
            slug = generate_slug(display_name)
        
        # Validate slug
        validate_slug(slug)
        
        # Check uniqueness
        existing = session.query(MaterialCategory).filter(
            MaterialCategory.slug == slug
        ).first()
        
        if existing:
            raise ValueError(f"Slug already exists: {slug}")
        
        category = MaterialCategory(
            slug=slug,
            display_name=display_name,
            notes=notes
        )
        
        session.add(category)
        return category
```

---

## UI Changes (Minimal)

### Materials Catalog UI

**Add slug field to forms (read-only or auto-generated):**

```
┌─ Create Material Category ──────────────────────────┐
│                                                       │
│ Display Name: [Boxes_______________________]        │
│                                                       │
│ Slug:         [boxes_______________________]        │
│               (auto-generated, read-only)            │
│                                                       │
│ Notes: [____________________________________]         │
│                                                       │
│                           [Cancel] [Create]          │
└───────────────────────────────────────────────────────┘
```

**OR allow manual editing with validation:**

```
┌─ Create Material ───────────────────────────────────┐
│                                                       │
│ Display Name: [Box Window Cake 10x10_______________]│
│                                                       │
│ Slug:         [box_window_cake_10x10_______________]│
│               ✓ Valid slug format                    │
│               [Auto-Generate]                        │
│                                                       │
│ Notes: [____________________________________]         │
│                                                       │
│                           [Cancel] [Create]          │
└───────────────────────────────────────────────────────┘
```

### Import/Export Dialog

**Show slug in preview:**

```
┌─ Import Materials Catalog ──────────────────────────┐
│                                                       │
│ Preview (first 3 items):                             │
│                                                       │
│ MaterialCategory:                                    │
│   - slug: "boxes"                                    │
│     display_name: "Boxes"                            │
│                                                       │
│ Material:                                            │
│   - slug: "box_window_cake_10x10"                   │
│     display_name: "Box Window Cake 10x10"           │
│     subcategory_slug: "window_boxes"                │
│                                                       │
│ [Import Mode: ADD_ONLY ▼] [Cancel] [Import]        │
└───────────────────────────────────────────────────────┘
```

---

## Migration Strategy

### For Existing F047 Implementations

**If no data exists yet:**
1. Add slug columns to schema
2. Deploy updated import service
3. Import fresh catalogs with slugs

**If data already exists:**

1. **Add slug columns (nullable initially):**
```sql
ALTER TABLE material_categories ADD COLUMN slug VARCHAR(100);
ALTER TABLE material_subcategories ADD COLUMN slug VARCHAR(100);
ALTER TABLE materials ADD COLUMN slug VARCHAR(100);
ALTER TABLE material_products ADD COLUMN slug VARCHAR(100);
```

2. **Backfill slugs from display_name:**
```python
def backfill_slugs():
    """Generate slugs for existing records"""
    
    # Categories
    for category in session.query(MaterialCategory).all():
        if not category.slug:
            category.slug = generate_slug(category.display_name)
    
    # Subcategories
    for subcat in session.query(MaterialSubcategory).all():
        if not subcat.slug:
            subcat.slug = generate_slug(subcat.display_name)
    
    # Materials
    for material in session.query(Material).all():
        if not material.slug:
            material.slug = generate_slug(material.display_name)
    
    # Products (optional)
    for product in session.query(MaterialProduct).all():
        if not product.slug:
            product.slug = generate_slug(product.display_name)
    
    session.commit()
```

3. **Make slug columns NOT NULL + add constraints:**
```sql
-- After backfill
ALTER TABLE material_categories ALTER COLUMN slug SET NOT NULL;
CREATE UNIQUE INDEX idx_material_categories_slug ON material_categories(slug);

-- Similar for other tables...
```

---

## Testing Checklist

### Schema Tests
- [ ] slug columns exist on all 4 tables
- [ ] Unique constraints enforced (category slug, subcategory slug per category, material slug per subcategory)
- [ ] slug validation works (lowercase, alphanumeric + underscore/hyphen)

### Import Tests
- [ ] Import with slugs works (new format)
- [ ] Import with display_name works (legacy format)
- [ ] Import resolves slug preferentially over display_name
- [ ] Import fails gracefully if neither slug nor display_name found

### Service Tests
- [ ] Auto-generate slug from display_name
- [ ] Manual slug creation with validation
- [ ] Duplicate slug detection
- [ ] Invalid slug format rejection

### UI Tests
- [ ] Slug field appears in create/edit forms
- [ ] Auto-generate button works
- [ ] Slug validation feedback shown
- [ ] Import preview shows slugs

### Integration Tests
- [ ] Full workflow: Create category → subcategory → material → product
- [ ] Export → reimport preserves slugs
- [ ] Rename display_name does NOT break import (slug unchanged)

---

## Rollout Plan

### Phase 1: Schema Update (30 min)
1. Create migration script
2. Add slug columns
3. Backfill existing data (if any)
4. Add constraints

### Phase 2: Service Layer (45 min)
1. Add slug generation helper
2. Add slug validation
3. Update create/update services
4. Update import resolution logic

### Phase 3: Import/Export (30 min)
1. Update import format parser
2. Add backward compatibility logic
3. Update export format writer

### Phase 4: UI Updates (30 min)
1. Add slug field to forms
2. Add auto-generate button
3. Update import preview

### Phase 5: Testing (30 min)
1. Run test checklist
2. Test with real materials_catalog.json
3. Verify import/export round-trip

**Total: 2.5-3 hours**

---

## Risk Mitigation

### Risk 1: Breaking Existing Imports
**Mitigation**: Backward compatibility (try slug, fall back to display_name)

### Risk 2: Slug Generation Conflicts
**Mitigation**: Allow manual slug override + uniqueness validation

### Risk 3: Migration Data Loss
**Mitigation**: Backup database before migration, test backfill script

### Risk 4: UI Confusion
**Mitigation**: Auto-generate by default, show slug in read-only field

---

## Success Criteria

- [ ] All 4 models have slug fields
- [ ] Import works with both slug and display_name references
- [ ] Slug auto-generation works
- [ ] Renaming display_name does NOT break imports
- [ ] Export includes slugs
- [ ] UI shows slugs (at least in forms)
- [ ] No existing functionality broken
- [ ] materials_catalog.json imports successfully

---

## Files to Modify

**Models:**
- `models/material_category.py`
- `models/material_subcategory.py`
- `models/material.py`
- `models/material_product.py`

**Services:**
- `services/material_category_service.py`
- `services/material_subcategory_service.py`
- `services/material_service.py`
- `services/material_product_service.py`
- `services/import_service.py` (or equivalent)
- `services/export_service.py` (or equivalent)

**Utils:**
- `utils/slug_utils.py` (new file for slug generation/validation)

**UI:**
- Material catalog forms (categories, subcategories, materials, products)
- Import/export dialogs

**Migrations:**
- `migrations/add_material_slugs.py` (new migration script)

**Tests:**
- Unit tests for slug generation/validation
- Integration tests for import/export
- UI tests for forms

---

## Post-Deployment

1. **Update materials_catalog.json** to include slugs (user's file already has them!)
2. **Update material_products_catalog.json** to use `material_slug` references
3. **Document slug usage** in import/export guide
4. **Monitor imports** for display_name fallback warnings

---

**END OF HOTFIX SPECIFICATION**
