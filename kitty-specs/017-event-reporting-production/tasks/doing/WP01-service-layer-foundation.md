---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Service Layer Foundation"
phase: "Phase 1 - Service Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "30686"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-11T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer Foundation

## Objectives & Success Criteria

**Objective**: Add CSV export and cost analysis service methods that UI components will depend on.

**Success Criteria**:
- `export_shopping_list_csv(event_id, file_path)` creates valid CSV file with shopping list data
- `get_event_cost_analysis(event_id)` returns production/assembly costs with estimated vs actual variance
- `get_recipient_history(recipient_id)` includes `fulfillment_status` in returned data
- All new service methods have unit tests
- All existing 680+ tests continue passing
- New methods have >80% coverage (SC-006)

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md`
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`
- Data Model: `kitty-specs/017-event-reporting-production/data-model.md`

**Architectural Constraints**:
- All business logic in services, not UI (Layered Architecture)
- Use `cost_at_time` from consumption records for actual costs (not current prices)
- Session management: Pass `session` parameter if calling from other service functions
- UTF-8 encoding for CSV export

**Existing Methods to Use**:
- `get_shopping_list(event_id)` - returns items, total_estimated_cost, items_count
- `get_production_progress(event_id)` - returns production targets with progress
- `get_assembly_progress(event_id)` - returns assembly targets with progress
- `get_event_overall_progress(event_id)` - returns aggregated progress

## Subtasks & Detailed Guidance

### Subtask T001 - Add export_shopping_list_csv()

**Purpose**: Enable CSV export of shopping list for offline access (printing, phone).

**Steps**:
1. Add import at top of `src/services/event_service.py`:
   ```python
   import csv
   from pathlib import Path
   ```

2. Add function after existing shopping list functions (~line 1118):
   ```python
   def export_shopping_list_csv(event_id: int, file_path: str) -> bool:
       """
       Export shopping list to CSV file.

       Args:
           event_id: Event ID
           file_path: Destination file path

       Returns:
           True if successful

       Raises:
           EventNotFoundError: If event not found
           IOError: If file write fails
       """
       # Get shopping list data
       shopping_data = get_shopping_list(event_id, include_packaging=True)

       if not shopping_data["items"] and not shopping_data.get("packaging"):
           # Nothing to export
           return True

       try:
           with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
               writer = csv.writer(csvfile)

               # Header row (FR-008)
               writer.writerow([
                   'Ingredient',
                   'Quantity Needed',
                   'On Hand',
                   'To Buy',
                   'Unit',
                   'Preferred Brand',
                   'Estimated Cost'
               ])

               # Data rows
               for item in shopping_data["items"]:
                   brand = ""
                   cost = ""
                   if item.get("product_recommendation"):
                       brand = item["product_recommendation"].get("display_name", "")
                       cost = str(item["product_recommendation"].get("total_cost", ""))

                   writer.writerow([
                       item["ingredient_name"],
                       str(item["quantity_needed"]),
                       str(item["quantity_on_hand"]),
                       str(item["shortfall"]),
                       item["unit"],
                       brand,
                       cost
                   ])

               # Packaging section if present
               if shopping_data.get("packaging"):
                   writer.writerow([])  # Blank row
                   writer.writerow(['--- Packaging Materials ---', '', '', '', '', '', ''])
                   for pkg in shopping_data["packaging"]:
                       writer.writerow([
                           pkg["ingredient_name"],
                           str(pkg["total_needed"]),
                           str(pkg["on_hand"]),
                           str(pkg["to_buy"]),
                           pkg["unit"],
                           pkg["product_name"],
                           ""
                       ])

           return True

       except (IOError, OSError) as e:
           raise IOError(f"Failed to write CSV file: {str(e)}")
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: No (must complete before T004)
**Notes**: Use `utf-8-sig` encoding for Excel compatibility (adds BOM).

---

### Subtask T002 - Add get_event_cost_analysis()

**Purpose**: Provide cost breakdown for planned vs actual comparison.

**Steps**:
1. Add function after `get_event_overall_progress()` (~line 1948):
   ```python
   def get_event_cost_analysis(event_id: int) -> Dict[str, Any]:
       """
       Get cost breakdown for an event.

       Calculates actual costs from ProductionRun.total_cost and AssemblyRun.total_cost,
       which are derived from cost_at_time in consumption records.

       Args:
           event_id: Event ID

       Returns:
           Dict with:
           - production_costs: List[{recipe_name, run_count, total_cost}]
           - assembly_costs: List[{finished_good_name, run_count, total_cost}]
           - total_production_cost: Decimal
           - total_assembly_cost: Decimal
           - grand_total: Decimal
           - estimated_cost: Decimal (from shopping list)
           - variance: Decimal (estimated - actual)
       """
       try:
           with session_scope() as session:
               # Get production costs grouped by recipe
               from sqlalchemy import func

               prod_costs = (
                   session.query(
                       Recipe.name,
                       func.count(ProductionRun.id).label('run_count'),
                       func.coalesce(func.sum(ProductionRun.total_cost), Decimal('0')).label('total_cost')
                   )
                   .join(ProductionRun, ProductionRun.recipe_id == Recipe.id)
                   .filter(ProductionRun.event_id == event_id)
                   .group_by(Recipe.id, Recipe.name)
                   .all()
               )

               production_costs = [
                   {"recipe_name": name, "run_count": count, "total_cost": Decimal(str(cost))}
                   for name, count, cost in prod_costs
               ]
               total_production_cost = sum(p["total_cost"] for p in production_costs)

               # Get assembly costs grouped by finished good
               asm_costs = (
                   session.query(
                       FinishedGood.display_name,
                       func.count(AssemblyRun.id).label('run_count'),
                       func.coalesce(func.sum(AssemblyRun.total_cost), Decimal('0')).label('total_cost')
                   )
                   .join(AssemblyRun, AssemblyRun.finished_good_id == FinishedGood.id)
                   .filter(AssemblyRun.event_id == event_id)
                   .group_by(FinishedGood.id, FinishedGood.display_name)
                   .all()
               )

               assembly_costs = [
                   {"finished_good_name": name, "run_count": count, "total_cost": Decimal(str(cost))}
                   for name, count, cost in asm_costs
               ]
               total_assembly_cost = sum(a["total_cost"] for a in assembly_costs)

               # Grand total
               grand_total = total_production_cost + total_assembly_cost

               # Get estimated cost from shopping list
               shopping_data = get_shopping_list(event_id, include_packaging=False)
               estimated_cost = shopping_data["total_estimated_cost"]

               # Variance (positive = under budget, negative = over budget)
               variance = estimated_cost - grand_total

               return {
                   "production_costs": production_costs,
                   "assembly_costs": assembly_costs,
                   "total_production_cost": total_production_cost,
                   "total_assembly_cost": total_assembly_cost,
                   "grand_total": grand_total,
                   "estimated_cost": estimated_cost,
                   "variance": variance,
               }

       except SQLAlchemyError as e:
           raise DatabaseError(f"Failed to get event cost analysis: {str(e)}")
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (after T001, independent section)
**Notes**: Uses `cost_at_time` from consumption records via `total_cost` on runs.

---

### Subtask T003 - Enhance get_recipient_history()

**Purpose**: Include fulfillment_status in recipient history for UI display.

**Steps**:
1. Find `get_recipient_history()` function (~line 1449)
2. Update the return dict to include `fulfillment_status`:
   ```python
   return [
       {
           "event": assignment.event,
           "package": assignment.package,
           "quantity": assignment.quantity,
           "notes": assignment.notes,
           "fulfillment_status": assignment.fulfillment_status,  # Add this line
       }
       for assignment in assignments
   ]
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (independent from T001, T002)
**Notes**: `fulfillment_status` already exists on EventRecipientPackage model from Feature 016.

---

### Subtask T004 - Unit tests for export_shopping_list_csv()

**Purpose**: Verify CSV export functionality.

**Steps**:
1. Add tests to `src/tests/test_event_service.py`:
   ```python
   import tempfile
   import csv
   import os

   class TestExportShoppingListCSV:
       """Tests for export_shopping_list_csv()."""

       def test_export_shopping_list_csv_success(self, db_session, sample_event_with_packages):
           """Test successful CSV export."""
           event = sample_event_with_packages

           with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
               temp_path = f.name

           try:
               result = event_service.export_shopping_list_csv(event.id, temp_path)
               assert result is True

               # Verify file exists and has content
               assert os.path.exists(temp_path)

               with open(temp_path, 'r', encoding='utf-8-sig') as f:
                   reader = csv.reader(f)
                   rows = list(reader)

               # Verify header row
               assert rows[0] == [
                   'Ingredient', 'Quantity Needed', 'On Hand', 'To Buy',
                   'Unit', 'Preferred Brand', 'Estimated Cost'
               ]
           finally:
               os.unlink(temp_path)

       def test_export_shopping_list_csv_event_not_found(self, db_session):
           """Test export with nonexistent event."""
           with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
               temp_path = f.name

           try:
               # Should handle gracefully (empty shopping list)
               result = event_service.export_shopping_list_csv(99999, temp_path)
               assert result is True
           finally:
               if os.path.exists(temp_path):
                   os.unlink(temp_path)

       def test_export_shopping_list_csv_io_error(self, db_session, sample_event_with_packages):
           """Test export with invalid path."""
           event = sample_event_with_packages

           with pytest.raises(IOError):
               event_service.export_shopping_list_csv(event.id, '/nonexistent/path/file.csv')
   ```

**Files**: `src/tests/test_event_service.py`
**Parallel?**: Yes (after T001)
**Notes**: Uses tempfile for test isolation; cleans up after.

---

### Subtask T005 - Unit tests for get_event_cost_analysis()

**Purpose**: Verify cost analysis calculations.

**Steps**:
1. Add tests to `src/tests/test_event_service.py`:
   ```python
   class TestGetEventCostAnalysis:
       """Tests for get_event_cost_analysis()."""

       def test_get_event_cost_analysis_with_production(
           self, db_session, sample_event_with_production_runs
       ):
           """Test cost analysis with production data."""
           event = sample_event_with_production_runs

           result = event_service.get_event_cost_analysis(event.id)

           assert "production_costs" in result
           assert "assembly_costs" in result
           assert "total_production_cost" in result
           assert "total_assembly_cost" in result
           assert "grand_total" in result
           assert "estimated_cost" in result
           assert "variance" in result

           # Verify totals are Decimals
           assert isinstance(result["grand_total"], Decimal)

           # Verify grand_total = production + assembly
           assert result["grand_total"] == (
               result["total_production_cost"] + result["total_assembly_cost"]
           )

       def test_get_event_cost_analysis_no_production(self, db_session, sample_event):
           """Test cost analysis with no production data."""
           event = sample_event

           result = event_service.get_event_cost_analysis(event.id)

           assert result["production_costs"] == []
           assert result["assembly_costs"] == []
           assert result["total_production_cost"] == Decimal('0')
           assert result["total_assembly_cost"] == Decimal('0')
           assert result["grand_total"] == Decimal('0')
   ```

**Files**: `src/tests/test_event_service.py`
**Parallel?**: Yes (after T002)
**Notes**: May need to create fixture `sample_event_with_production_runs` if not exists.

---

### Subtask T006 - Unit tests for enhanced get_recipient_history()

**Purpose**: Verify fulfillment_status is included in history.

**Steps**:
1. Add/update tests in `src/tests/test_event_service.py`:
   ```python
   def test_get_recipient_history_with_fulfillment_status(
       self, db_session, sample_recipient_with_packages
   ):
       """Test that recipient history includes fulfillment_status."""
       recipient = sample_recipient_with_packages

       history = event_service.get_recipient_history(recipient.id)

       assert len(history) > 0

       for record in history:
           assert "fulfillment_status" in record
           # Status should be one of the valid values
           assert record["fulfillment_status"] in ['pending', 'ready', 'delivered', None]
   ```

**Files**: `src/tests/test_event_service.py`
**Parallel?**: Yes (after T003)
**Notes**: Check existing fixtures for recipient with package assignments.

---

## Test Strategy

**Run Tests**:
```bash
# Run just the new tests
pytest src/tests/test_event_service.py -v -k "export_shopping_list or cost_analysis or fulfillment_status"

# Run all event service tests
pytest src/tests/test_event_service.py -v

# Run full suite to verify no regressions
pytest src/tests -v
```

**Expected Results**:
- All new tests pass
- All existing 680+ tests pass
- Coverage >80% for new methods

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CSV encoding issues | Use utf-8-sig for Excel compatibility |
| Cost calculation accuracy | Use cost_at_time from consumption records |
| Missing fixtures for tests | Create minimal fixtures if needed |
| Session management | Don't nest session_scope(); use single session |

## Definition of Done Checklist

- [ ] T001: `export_shopping_list_csv()` implemented and working
- [ ] T002: `get_event_cost_analysis()` implemented and working
- [ ] T003: `get_recipient_history()` includes fulfillment_status
- [ ] T004: CSV export unit tests pass
- [ ] T005: Cost analysis unit tests pass
- [ ] T006: Recipient history unit tests pass
- [ ] All 680+ existing tests pass
- [ ] Code follows session management guidelines from CLAUDE.md
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. CSV export creates valid file readable in Excel
2. Cost analysis uses historical costs (cost_at_time), not current prices
3. No nested session_scope() calls
4. All new methods have docstrings
5. Unit tests cover happy path, edge cases, and errors

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T22:27:00Z – claude – shell_pid=30686 – lane=doing – Started implementation
