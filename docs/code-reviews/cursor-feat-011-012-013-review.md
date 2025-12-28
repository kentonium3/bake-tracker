# Features 011-013 - Independent Code Review

**Reviewer:** Cursor (independent)
**Date:** 2025-12-10
**Scope:** Feature 011 (Packaging & BOM foundation), Feature 012 (Nested recipes), Feature 013 (Production & inventory tracking)
**Status:** Findings for follow-up (no code changes made)

---

## Summary

Features 011-013 largely extend the domain model (packaging flag on ingredients, recipe components, production/assembly ledgers) and add substantial service/test coverage. Overall layering and constraints look good, but I found several risks around transactional integrity, time zone handling, and auditability that could lead to data corruption or hard-to-debug state. Tests are strong for happy paths and validation, but miss rollback/atomicity cases.

---

## Findings

Severity legend: **Critical** (blocks release), **High** (likely data/behavior bugs), **Medium** (edge-case or maintainability), **Low** (minor consistency).

- **High — Non-atomic FIFO consumption in batch production**
  Ingredient consumption is executed in a different session/transaction (`consume_fifo` opens its own `session_scope` and commits), but the production run, finished unit increment, and ledger creation are in another session. If a later step fails (e.g., DB error creating `ProductionRun`), inventory remains consumed with no production record or finished units added. There is no compensating rollback.
  ```220:323:/Users/kentgale/Vaults-repos/bake-tracker/src/services/batch_production_service.py
        # Note: consume_fifo uses its own session_scope, so it commits independently
        for item in aggregated:
            ...
            result = inventory_item_service.consume_fifo(
                ingredient_slug, quantity_needed, dry_run=False
            )
            if not result["satisfied"]:
                raise InsufficientInventoryError(...)
        ...
        production_run = ProductionRun(...)
  ```

- **High — Packaging consumption can be partially committed on assembly failure**
  Assembly uses the same pattern: packaging is consumed via `consume_fifo` in a separate transaction before the `AssemblyRun` is persisted. Any failure after packaging consumption (e.g., DB error, validation on a later component) leaves packaging inventory decremented without an assembly record. Tests assert rollback for finished units but never verify packaging inventory.
  ```265:357:/Users/kentgale/Vaults-repos/bake-tracker/src/services/assembly_service.py
        elif comp.packaging_product_id:
            ...
            result = inventory_item_service.consume_fifo(
                ingredient_slug, needed, dry_run=False
            )
            if not result["satisfied"]:
                raise InsufficientPackagingError(...)
        ...
        assembly_run = AssemblyRun(...)
  ```

- **High — Mixed timezone-aware and naive timestamps for AssemblyRun**
  `AssemblyRun.assembled_at` is a plain `DateTime`, but the service uses `datetime.now(timezone.utc)` (aware). Other services use `datetime.utcnow()` (naive). SQLAlchemy will emit warnings or fail when inserting aware datetimes into naive columns, and the mix causes inconsistent serialization.
  ```348:354:/Users/kentgale/Vaults-repos/bake-tracker/src/services/assembly_service.py
        assembly_run = AssemblyRun(
            ...
            assembled_at=assembled_at or datetime.now(timezone.utc),
  ```

- **Medium — No ledger entries for nested FinishedGood components in assemblies**
  When a FinishedGood is used as a component of another FinishedGood, the service decrements inventory and includes the cost, but intentionally skips creating any consumption ledger entry. This breaks auditability for nested assemblies and makes cost reconstruction impossible from ledgers alone.
  ```293:312:/Users/kentgale/Vaults-repos/bake-tracker/src/services/assembly_service.py
            elif comp.finished_good_id:
                ...
                nested_fg.inventory_count -= needed
                total_component_cost += cost
                # Note: For now we don't create consumption records for nested FGs
  ```

- **Medium — Optional `session` parameters are ignored**
  Both `record_batch_production` and `record_assembly` accept `session=None` but immediately open their own `session_scope`, so callers cannot compose these operations inside a larger transaction. This makes it harder to guarantee atomic workflows or reuse an existing session.
  (Same locations as snippets above; `session` argument is unused.)

- **Low — Packaging validation is permissive**
  `Composition` allows any `Product` as packaging, and `assembly_service` only checks `product` exists, not `ingredient.is_packaging`. A mis-tagged product could be consumed as packaging, bypassing the domain guard introduced in Feature 011. Consider enforcing `ingredient.is_packaging` when `packaging_product_id` is set.

---

## Test Coverage Notes

- Strong coverage for nested recipes (circular/depth guards, cost aggregation) and for production/assembly happy paths, import/export, and validation errors.
- No tests verify that packaging/ingredient inventory is restored on assembly or production failures; because FIFO consumption runs in a separate transaction, partial state corruption would go unnoticed.
- No tests cover timezone handling for `AssemblyRun` timestamps.

---

## Recommendations

1. Make FIFO consumption part of the caller’s transaction (pass session into `consume_fifo` or provide a non-committing variant); ensure failures roll back both inventory and run records.
2. Standardize timestamps to naive UTC (`datetime.utcnow()`) or migrate columns to timezone-aware; be consistent across services.
3. Emit ledger entries for nested FinishedGood components or clearly document and test the limitation.
4. Enforce `ingredient.is_packaging` when creating packaging compositions and during assembly consumption.
5. Add regression tests for transactional rollback (packaging + ingredients) and for timestamp consistency.

No code was changed; this report is for follow-up action.



