# Research: MaterialUnit Schema Refactor

**Feature**: 085-material-unit-schema-refactor
**Date**: 2026-01-30
**Status**: Complete

## Research Questions

### RQ-1: Current MaterialUnit FK Pattern

**Question**: How is MaterialUnit currently linked to Material?

**Finding**: MaterialUnit has `material_id` FK to Material with CASCADE delete:
```python
# src/models/material_unit.py
material_id = Column(
    Integer,
    ForeignKey("materials.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
material = relationship("Material", back_populates="units")
```

**Decision**: Replace with `material_product_id` FK using same pattern.

---

### RQ-2: Target FK Pattern (FinishedUnit→Recipe)

**Question**: What pattern should we follow for MaterialUnit→MaterialProduct?

**Finding**: FinishedUnit uses this pattern for Recipe parent:
```python
# src/models/finished_unit.py
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
recipe = relationship("Recipe", back_populates="finished_units", lazy="joined")

# src/models/recipe.py
finished_units = relationship("FinishedUnit", back_populates="recipe")
```

**Decision**: Apply identical pattern:
- `material_product_id` FK with CASCADE delete
- `lazy="joined"` on child side for eager loading
- `cascade="all, delete-orphan"` on parent side

---

### RQ-3: Composition XOR Constraint

**Question**: How is the current 5-way XOR constraint implemented?

**Finding**: CheckConstraint with explicit OR conditions:
```python
# src/models/composition.py
CheckConstraint(
    "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND ...) OR "
    "(...material_id IS NOT NULL)",
    name="ck_composition_exactly_one_component",
),
```

**Decision**: Remove material_id from all conditions → 4-way XOR.

---

### RQ-4: Slug Auto-Generation Pattern

**Question**: How do other services generate unique slugs?

**Finding**: Three patterns exist:

1. **recipe_service.py** (hyphens, 200 char limit):
   ```python
   slug = re.sub(r"[\s_]+", "-", slug)
   slug = re.sub(r"[^a-z0-9-]", "", slug)
   ```

2. **material_catalog_service.py** (underscores):
   ```python
   slug = re.sub(r"[\s\-]+", "_", slug)
   slug = re.sub(r"[^a-z0-9_]", "", slug)
   ```

3. **finished_unit_service.py** (hyphens, 90 char limit):
   ```python
   slug = re.sub(r"[\s_-]+", "-", slug)
   ```

**Decision**: Use hyphen pattern (recipe_service style) for consistency with MaterialUnit being consumption-focused like recipes.

**Uniqueness approach**: All use counter suffix (-2, -3, etc.) with max 1000 attempts.

---

### RQ-5: Export/Import FK Resolution

**Question**: How do export/import services resolve FK references?

**Finding**: FKs exported as slug strings, resolved via lookup dictionaries:
```python
# Export
"material_slug": product.material.slug if product.material else None

# Import
material_lookup = {row.slug: row.id for row in session.query(Material).all()}
material_id = material_lookup.get(item["material_slug"])
if material_id is None:
    result.add_error(..., f"Material '{item['material_slug']}' not found")
```

**Decision**: Change `material_slug` to `material_product_slug` in MaterialUnit export/import.

---

### RQ-6: Session Management Pattern

**Question**: How should auto-generation handle session management?

**Finding**: All services accept optional `session` parameter:
```python
def create_category(
    name: str,
    session: Optional[Session] = None,
) -> MaterialCategory:
    def _impl(sess: Session) -> MaterialCategory:
        # Implementation

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)
```

**Decision**: Auto-generation must use the same session as product creation to ensure atomic transaction.

---

### RQ-7: MaterialProduct Type Detection

**Question**: How to detect if product is "each" type vs linear/area?

**Finding**: MaterialProduct has mutually exclusive fields:
- `package_count` (Integer) - for discrete items (bags, boxes)
- `package_length_m` (Float) - for linear materials (ribbon, tape)
- `package_sq_m` (Float) - for area materials (fabric, paper)

**Decision**: Auto-generate MaterialUnit only when:
- `package_count IS NOT NULL`
- AND `package_length_m IS NULL`
- AND `package_sq_m IS NULL`

---

### RQ-8: UI Sub-Form Pattern

**Question**: How do other tabs display sub-sections with related records?

**Finding**: Recipe tab displays FinishedUnits in a CTkScrollableFrame with:
- Treeview for listing items
- Add/Edit buttons
- Dialog forms for CRUD operations

**Decision**: Apply same pattern for MaterialUnits in MaterialProduct form.

---

## Research Summary

| Topic | Current Pattern | New Pattern |
|-------|-----------------|-------------|
| MaterialUnit FK | `material_id` → Material | `material_product_id` → MaterialProduct |
| Composition XOR | 5-way (includes material_id) | 4-way (material_id removed) |
| Slug generation | Varies by service | Hyphen style from recipe_service |
| Export FK | `material_slug` | `material_product_slug` |
| Auto-generation | N/A | On product create if package_count only |
| UI sub-form | Recipe→FinishedUnits pattern | Apply to MaterialProduct→MaterialUnits |

## Alternatives Considered

### Alt-1: Keep material_id as optional fallback
- **Rejected**: Adds complexity, contradicts goal of removing ambiguity
- **Chosen**: Complete removal of material_id from Composition

### Alt-2: Many-to-many bridge table for MaterialUnit↔MaterialProduct
- **Rejected**: Over-engineering for current needs; complicates queries
- **Chosen**: Direct FK with duplication accepted during migration

### Alt-3: Auto-sync MaterialUnit name with product name changes
- **Rejected**: User may have customized the unit name
- **Chosen**: Auto-generate once on creation; user manages after that
