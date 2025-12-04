---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Models Layer - Package & Junction"
phase: "Phase 1 - Models Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "6511"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Models Layer - Package & Junction

## Objectives & Success Criteria

- Create the PackageFinishedGood junction model that replaces the removed PackageBundle
- Update the Package model to use the new relationship
- Implement cost calculation that chains to FinishedGood.total_cost
- All models import successfully without errors

**Success Criteria**:
- PackageFinishedGood model exists with correct foreign keys and indexes
- Package.package_finished_goods relationship works
- Package.calculate_cost() returns correct sum of FinishedGood costs
- `from src.models import Package, PackageFinishedGood` works

## Context & Constraints

**Architecture Decision**: Per research decision D1, the Bundle concept is eliminated. Package directly references FinishedGood assemblies via the new PackageFinishedGood junction table.

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/plan.md` - Implementation phases
- `kitty-specs/006-event-planning-restoration/data-model.md` - Entity relationships and field definitions
- `kitty-specs/006-event-planning-restoration/contracts/package_service.md` - Service interface
- `.kittify/memory/constitution.md` - Architecture principles

**Constraints**:
- Must follow layered architecture (models define schema only, no business logic beyond calculated properties)
- Foreign keys: package_id (CASCADE on delete), finished_good_id (RESTRICT on delete)
- Must integrate with existing FinishedGood model from Features 002-004

## Subtasks & Detailed Guidance

### Subtask T001 - Create PackageFinishedGood model in `src/models/package.py`

**Purpose**: Replace the removed PackageBundle model with a new junction linking Package to FinishedGood.

**Steps**:
1. Open `src/models/package.py`
2. Add the PackageFinishedGood class after Package class definition
3. Define columns:
   - `id` (Integer, PK, autoincrement)
   - `package_id` (Integer, FK -> packages.id, nullable=False)
   - `finished_good_id` (Integer, FK -> finished_goods.id, nullable=False)
   - `quantity` (Integer, nullable=False, default=1)
4. Add foreign key constraints:
   - `package_id`: ondelete='CASCADE'
   - `finished_good_id`: ondelete='RESTRICT'
5. Add relationships:
   - `package`: back_populates Package.package_finished_goods
   - `finished_good`: links to FinishedGood model
6. Add indexes per data-model.md:
   - `idx_package_fg_package` on package_id
   - `idx_package_fg_finished_good` on finished_good_id
7. Inherit from BaseModel for UUID and timestamp fields

**Files**: `src/models/package.py`

**Example structure**:
```python
class PackageFinishedGood(BaseModel):
    __tablename__ = "package_finished_goods"

    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)

    # Relationships
    package = relationship("Package", back_populates="package_finished_goods")
    finished_good = relationship("FinishedGood")
```

### Subtask T002 - Update Package model relationship from `package_bundles` to `package_finished_goods`

**Purpose**: Change the Package model to use the new PackageFinishedGood junction instead of the removed PackageBundle.

**Steps**:
1. In Package class, find the existing relationship (may be `package_bundles` or commented out)
2. Replace/add:
   ```python
   package_finished_goods = relationship("PackageFinishedGood", back_populates="package", cascade="all, delete-orphan")
   ```
3. Remove any references to PackageBundle or Bundle
4. Ensure lazy loading strategy is appropriate (consider `lazy="selectin"` for performance)

**Files**: `src/models/package.py`

### Subtask T003 - Update Package.calculate_cost() to use FinishedGood.total_cost

**Purpose**: Cost calculation must chain through FinishedGood to get FIFO-accurate costs.

**Steps**:
1. Find the existing calculate_cost() method in Package class
2. Update to sum FinishedGood.total_cost * quantity for all package_finished_goods:
   ```python
   def calculate_cost(self) -> Decimal:
       """Calculate total cost from FinishedGood costs."""
       total = Decimal("0")
       for pfg in self.package_finished_goods:
           fg_cost = pfg.finished_good.total_cost or Decimal("0")
           total += fg_cost * pfg.quantity
       return total
   ```
3. Handle None/null total_cost gracefully (treat as zero or "Cost unavailable")
4. Ensure Decimal precision is maintained

**Files**: `src/models/package.py`

**Integration**: This chains to FinishedGood.calculate_component_cost() which uses RecipeService.calculate_actual_cost() for FIFO costing (FR-028).

### Subtask T004 - Add Package.get_item_count() method

**Purpose**: Provide a method to count FinishedGoods in a package (renamed from the old get_bundle_count).

**Steps**:
1. Add method to Package class:
   ```python
   def get_item_count(self) -> int:
       """Return count of FinishedGoods in this package."""
       return len(self.package_finished_goods)
   ```
2. Consider also providing get_total_quantity() that sums quantities:
   ```python
   def get_total_quantity(self) -> int:
       """Return total quantity of items across all FinishedGoods."""
       return sum(pfg.quantity for pfg in self.package_finished_goods)
   ```

**Files**: `src/models/package.py`

### Subtask T005 - Update `src/models/__init__.py` to export PackageFinishedGood

**Purpose**: Make PackageFinishedGood importable from src.models.

**Steps**:
1. Open `src/models/__init__.py`
2. Find the Package import line (likely commented out)
3. Update to:
   ```python
   from .package import Package, PackageFinishedGood
   ```
4. Add to `__all__` list if present
5. Do NOT yet enable Event, EventRecipientPackage (that's WP02)

**Files**: `src/models/__init__.py`

**Note**: Import carefully to avoid circular imports. Package should be importable independently.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import with FinishedGood | Use string references in ForeignKey/relationship |
| Missing finished_goods table | Verify Features 002-004 are complete |
| Cost calculation returns None | Handle null total_cost gracefully |

## Definition of Done Checklist

- [ ] PackageFinishedGood model created with correct schema
- [ ] Indexes added for package_id and finished_good_id
- [ ] Package.package_finished_goods relationship works
- [ ] Package.calculate_cost() returns correct Decimal sum
- [ ] Package.get_item_count() method works
- [ ] `from src.models import Package, PackageFinishedGood` works without import errors
- [ ] No references to Bundle or PackageBundle remain in package.py
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify foreign key constraints are correct (CASCADE vs RESTRICT)
- Check that cost calculation handles edge cases (empty package, null costs)
- Ensure relationship back_populates are symmetric
- Test import from src.models

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:27:39Z – claude – shell_pid=6511 – lane=doing – Started implementation
