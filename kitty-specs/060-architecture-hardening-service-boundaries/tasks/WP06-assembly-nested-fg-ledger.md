---
work_package_id: "WP06"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Assembly Nested Finished Goods Ledger"
phase: "Phase 2 - Parallel Track"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "17206"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Assembly Nested Finished Goods Ledger

## Implementation Command

```bash
spec-kitty implement WP06 --base WP01
```

Depends on WP01 (follows assembly_service session pattern).

**Codex Parallelizable**: YES - This WP can be assigned to Codex for parallel execution with WP04, WP05, WP07 after WP01 completes.

---

## Objectives & Success Criteria

**Primary Objective**: Create consumption records for nested FinishedGood consumption in assembly operations.

**Success Criteria**:
1. Consumption records created when nested FG consumed in assembly
2. Cost snapshotted at consumption time (not calculated later)
3. Lot tracking included for nested finished goods
4. Export includes nested consumption records
5. Audit trail complete for all assembly components

**Key Acceptance Checkpoints**:
- [ ] Assembly with nested FG creates consumption record
- [ ] Consumption record has cost snapshot
- [ ] Lot ID tracked when applicable
- [ ] Export/import preserves nested consumption records

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 5 (Assembly Nested FG Ledger Gap)
- **Data Model**: `kitty-specs/060-architecture-hardening-service-boundaries/data-model.md` - New Consumption Records section
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP06 section

### Current State (from research)

Assembly service creates consumption records for:
- Packaging products (`AssemblyPackagingConsumption`)
- Materials (`material_consumption_service`)
- Finished units (`AssemblyFinishedUnitConsumption`)

**GAP**: Nested finished goods consumed but NO ledger entry created.

### Pattern to Follow (lines 456-464)

```python
for pkg_data in pkg_consumptions:
    consumption = AssemblyPackagingConsumption(
        assembly_run_id=assembly_run.id,
        product_id=pkg_data["product_id"],
        quantity_consumed=pkg_data["quantity_consumed"],
        unit=pkg_data["unit"],
        total_cost=pkg_data["total_cost"],  # Cost snapshot
    )
    session.add(consumption)
```

### Understanding "Nested Finished Goods"

A nested finished good is when one FinishedGood (e.g., "Gift Basket") contains another FinishedGood (e.g., "Cookie Tin") as a component. When assembling the Gift Basket, we consume from the Cookie Tin inventory, but currently no consumption record is created.

---

## Subtasks & Detailed Guidance

### Subtask T028 – Identify nested FG consumption points in assembly_service.py

**Purpose**: Understand exactly where nested FinishedGoods are consumed and how.

**Steps**:

1. Open `src/services/assembly_service.py`

2. Locate `_record_assembly_impl()` (around line 320)

3. Find where components are processed:
   ```python
   # Look for loops processing assembly components
   for component in finished_good.components:
       # Some components may be other FinishedGoods
       pass
   ```

4. Identify nested FG consumption:
   ```python
   # Nested FG would be a component that is itself a FinishedGood
   # Not an ingredient, not packaging, not material - another assembled good
   ```

5. Check the component model to understand relationships:
   - Does Composition link to FinishedGood as a component type?
   - Or is there a separate "nested FG" relationship?

6. Document findings:
   ```markdown
   ## Nested FG Consumption Analysis

   - Location: `_record_assembly_impl()` line XXX
   - Pattern: Components can be FinishedGoods
   - Current behavior: Inventory decremented, no ledger record
   - Proposed change: Add consumption record creation
   ```

**Files**:
- `src/services/assembly_service.py` (read-only analysis)
- `src/models/composition.py` (understand relationship)
- `src/models/finished_good.py` (understand components)

**Parallel?**: No - foundational research

**Notes**:
- This subtask is primarily analysis, not implementation
- Understand the data model before writing code
- May need to check if FinishedGood can reference other FinishedGoods

---

### Subtask T029 – Create consumption records with cost snapshot

**Purpose**: Add ledger entries when nested FG is consumed in assembly.

**Steps**:

1. Based on T028 findings, identify where to add consumption record creation

2. Determine which model to use:
   - Option A: Use existing `AssemblyFinishedUnitConsumption` if it fits
   - Option B: Create new `AssemblyNestedFGConsumption` model if needed

3. If using existing model, verify it has required fields:
   ```python
   # Required fields
   - assembly_run_id: FK to AssemblyRun
   - finished_good_id (or finished_unit_id): FK to consumed item
   - quantity_consumed: How much was consumed
   - unit: Unit of measure
   - total_cost: Cost snapshot at consumption time
   ```

4. If creating new model (in `src/models/`):
   ```python
   class AssemblyNestedFGConsumption(BaseModel):
       __tablename__ = "assembly_nested_fg_consumption"

       id = Column(Integer, primary_key=True)
       assembly_run_id = Column(Integer, ForeignKey("assembly_run.id"), nullable=False)
       finished_good_id = Column(Integer, ForeignKey("finished_good.id"), nullable=False)
       quantity_consumed = Column(Numeric(10, 3), nullable=False)
       unit = Column(String(50), nullable=False)
       total_cost = Column(Numeric(10, 2), nullable=True)  # Cost snapshot
       lot_id = Column(Integer, ForeignKey("lot.id"), nullable=True)

       # Relationships
       assembly_run = relationship("AssemblyRun", back_populates="nested_fg_consumptions")
       finished_good = relationship("FinishedGood")
   ```

5. Add consumption record creation in `_record_assembly_impl()`:
   ```python
   # After consuming nested FG from inventory
   nested_fg_consumptions = []

   for component in nested_fg_components:
       # Calculate cost at consumption time
       current_cost = _calculate_nested_fg_cost(component.finished_good_id, session)

       nested_fg_consumptions.append({
           "finished_good_id": component.finished_good_id,
           "quantity_consumed": component.quantity * assembly_quantity,
           "unit": component.unit,
           "total_cost": current_cost,
           "lot_id": component.lot_id if hasattr(component, 'lot_id') else None
       })

   # Create records
   for consumption_data in nested_fg_consumptions:
       consumption = AssemblyNestedFGConsumption(
           assembly_run_id=assembly_run.id,
           **consumption_data
       )
       session.add(consumption)
   ```

6. Calculate cost snapshot (follow existing pattern):
   ```python
   def _calculate_nested_fg_cost(finished_good_id: int, session) -> Optional[Decimal]:
       """Calculate current cost of finished good for consumption snapshot."""
       # May use existing calculate_current_cost method
       # Or FIFO-based cost from inventory
       pass
   ```

**Files**:
- `src/services/assembly_service.py` (modify ~40 lines)
- `src/models/assembly_consumption.py` or similar (new or modify)
- If new model: Update `src/models/__init__.py`

**Parallel?**: No - depends on T028

**Notes**:
- Cost snapshot is critical - must capture at consumption time
- Follow existing packaging consumption pattern exactly
- Handle case where cost is unknown (set to None or 0)

---

### Subtask T030 – Include lot tracking for nested finished goods

**Purpose**: Track which specific lot of nested FG was consumed for traceability.

**Steps**:

1. Check if nested FG inventory has lot tracking:
   - Is there a `lot_id` on FinishedGood inventory records?
   - How does FIFO work for finished goods?

2. If lot tracking exists, capture in consumption record:
   ```python
   consumption = AssemblyNestedFGConsumption(
       # ... other fields ...
       lot_id=consumed_from_lot_id,  # Track which lot
   )
   ```

3. If lot tracking doesn't exist for FG inventory:
   - Leave lot_id as nullable
   - Document that lot tracking is not available for nested FG
   - Consider: Should lot tracking be added? (Out of scope for this WP)

4. Handle multiple lots consumed (FIFO may span lots):
   ```python
   # If consuming 10 units and lot A has 6, lot B has 4
   # May need multiple consumption records or aggregate differently
   ```

**Files**:
- `src/services/assembly_service.py` (within T029 implementation)
- May need to check inventory model for lot tracking

**Parallel?**: No - part of T029

**Notes**:
- Lot tracking may not be fully implemented for finished goods
- Don't block on this - make lot_id nullable
- Document limitations if lot tracking isn't available

---

### Subtask T031 – Update export to include nested consumption records

**Purpose**: Ensure nested FG consumption records are included in data export.

**Steps**:

1. Locate export logic in `src/services/import_export_service.py`

2. Find where AssemblyRun or AssemblyPackagingConsumption is exported

3. Add export for nested FG consumption:
   ```python
   # In export_assembly_runs() or similar
   def export_assembly_run(assembly_run, session):
       data = {
           "id": assembly_run.id,
           # ... existing fields ...
           "packaging_consumptions": [
               _export_packaging_consumption(c) for c in assembly_run.packaging_consumptions
           ],
           # NEW: Add nested FG consumptions
           "nested_fg_consumptions": [
               _export_nested_fg_consumption(c) for c in assembly_run.nested_fg_consumptions
           ],
       }
       return data

   def _export_nested_fg_consumption(consumption):
       return {
           "finished_good_id": consumption.finished_good_id,
           "quantity_consumed": float(consumption.quantity_consumed),
           "unit": consumption.unit,
           "total_cost": float(consumption.total_cost) if consumption.total_cost else None,
           "lot_id": consumption.lot_id,
       }
   ```

4. Add import logic:
   ```python
   def _import_assembly_run(data, session):
       # ... existing import ...

       # Import nested FG consumptions
       for consumption_data in data.get("nested_fg_consumptions", []):
           consumption = AssemblyNestedFGConsumption(
               assembly_run_id=assembly_run.id,
               **consumption_data
           )
           session.add(consumption)
   ```

5. Add round-trip test (see T032)

**Files**:
- `src/services/import_export_service.py` (modify ~40 lines)

**Parallel?**: Yes - can start once T029 is complete

**Notes**:
- Follow existing pattern for packaging consumptions
- Handle backward compatibility (old exports won't have this field)
- Use `.get("nested_fg_consumptions", [])` for safe import

---

### Subtask T032 – Add tests for ledger completeness

**Purpose**: Verify nested FG consumption creates proper audit trail.

**Steps**:

1. Add test for consumption record creation:
   ```python
   def test_assembly_creates_nested_fg_consumption():
       """Verify assembly with nested FG creates consumption record."""
       with session_scope() as session:
           # Create nested FG structure
           inner_fg = _create_finished_good("cookie-tin", session)
           outer_fg = _create_finished_good("gift-basket", session)
           _add_nested_fg_component(outer_fg, inner_fg, quantity=1, session=session)

           # Add inventory of inner FG
           _add_finished_good_inventory(inner_fg.id, quantity=10, session=session)

           # Assemble outer FG
           result = assembly_service.record_assembly(
               finished_good_id=outer_fg.id,
               quantity=2,
               session=session
           )

           # Verify consumption record created
           consumptions = session.query(AssemblyNestedFGConsumption).filter(
               AssemblyNestedFGConsumption.assembly_run_id == result["assembly_run_id"]
           ).all()

           assert len(consumptions) == 1
           assert consumptions[0].finished_good_id == inner_fg.id
           assert consumptions[0].quantity_consumed == 2  # 2 baskets * 1 tin each
   ```

2. Add test for cost snapshot:
   ```python
   def test_nested_fg_cost_snapshotted():
       """Verify cost captured at consumption time."""
       with session_scope() as session:
           # Create and assemble
           result = assembly_service.record_assembly(...)

           consumption = session.query(AssemblyNestedFGConsumption).first()
           original_cost = consumption.total_cost

           # Change the FG cost
           _update_finished_good_cost(inner_fg.id, original_cost * 2)

           # Reload consumption
           session.refresh(consumption)

           # Cost should NOT have changed
           assert consumption.total_cost == original_cost
   ```

3. Add test for export/import:
   ```python
   def test_nested_fg_consumption_export_import():
       """Verify consumption records survive export/import."""
       # Create assembly with nested FG consumption
       # Export
       # Reset database
       # Import
       # Verify consumption records restored
       pass
   ```

4. Add test for audit trail completeness:
   ```python
   def test_assembly_audit_trail_complete():
       """Verify all component types have consumption records."""
       # Create assembly with:
       # - Packaging products
       # - Materials
       # - Finished units
       # - Nested finished goods

       # Verify ALL have consumption records
       pass
   ```

**Files**:
- `src/tests/services/test_assembly_service.py` (add ~100 lines)
- `src/tests/services/test_import_export_service.py` (add ~30 lines)

**Parallel?**: No - depends on T029-T031

**Notes**:
- May need to create test fixtures for nested FG structure
- Test cost snapshot with time-based verification
- Ensure backward compatibility with assemblies that have no nested FG

---

## Test Strategy

**Required Tests**:
1. Nested FG assembly creates consumption record
2. Cost snapshotted at consumption time
3. Lot ID captured when available
4. Export/import round-trip works
5. Audit trail complete for all component types

**Test Commands**:
```bash
# Run assembly service tests
./run-tests.sh src/tests/services/test_assembly_service.py -v

# Run import/export tests
./run-tests.sh src/tests/services/test_import_export_service.py -v

# Run all tests
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Nested FG structure unclear | T028 is pure analysis first |
| Cost calculation complex | Follow existing packaging pattern |
| Lot tracking not available | Make lot_id nullable, document |
| New model needed | Follow existing consumption model pattern |

---

## Definition of Done Checklist

- [ ] T028: Nested FG consumption points identified and documented
- [ ] T029: Consumption records created with cost snapshot
- [ ] T030: Lot tracking included (or documented as unavailable)
- [ ] T031: Export/import includes nested consumption records
- [ ] T032: Tests verify ledger completeness
- [ ] Full test suite passes

---

## Review Guidance

**Key Review Checkpoints**:
1. Follows packaging consumption pattern exactly
2. Cost is snapshotted at consumption time (not calculated later)
3. Export/import handles new records
4. Tests verify audit trail complete

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-21T04:05:06Z – claude-opus – shell_pid=17206 – lane=doing – Started implementation via workflow command
- 2026-01-21T04:17:08Z – claude-opus – shell_pid=17206 – lane=for_review – Ready for review: Added AssemblyFinishedGoodConsumption model, updated assembly_service to create ledger records, added export/import support, 5 new tests. All 2562 tests pass.
