# Code Review: Session Management and Transactionality (Feature 016)

## Issue List (ranked by severity)
- **High – Optional sessions ignored in orchestration flows**
  `src/services/batch_production_service.py` (`check_can_produce`, `record_batch_production`) and `src/services/assembly_service.py` (`check_can_assemble`, `record_assembly`) accept `session=None` but always open a new `session_scope`. Callers cannot wrap multi-step workflows in one transaction, and nested calls split work across sessions.
- **High – Detached objects returned from closed sessions**
  `recipe_service` (most getters/CRUD), `inventory_item_service.add_to_inventory`, `event_service` CRUD/query, and others return ORM objects after `session_scope` exits. Lazy access or subsequent writes will fail; objects cannot safely participate in broader transactions.
- **High – Cross-service calls open fresh sessions mid-transaction**
  Example: `inventory_item_service.add_to_inventory` calls `get_product`/`get_ingredient`, which open their own sessions while `add_to_inventory` uses another. This mixes identity maps and breaks atomicity on non-SQLite backends.
- **Medium – Availability/dry-run checks not session-consistent**
  Production/assembly availability checks call `consume_fifo` without passing a session; dry-run and execution cannot share the same transactional view.
- **Medium – Import/export flows create their own sessions**
  Production/assembly imports wrap per-run work in internal `session_scope`, so duplicate detection and inserts are not atomic with a caller’s transaction.

## Recurring Patterns
- Optional `session` parameters are ignored; new `session_scope()` is opened unconditionally.
- Service functions return live ORM instances after closing their session (detached object anti-pattern).
- Cross-service helper calls open new sessions instead of reusing caller-owned sessions.
- Multi-step operations (validate → consume FIFO → increment counts → ledger) are split across independent transactions.

## Recommended Fixes (prioritized)
1) **Honor caller sessions everywhere:** Only open `session_scope` when `session` is `None`; otherwise reuse the provided session. Thread the same session through all downstream calls (`consume_fifo`, `get_aggregated_ingredients`, `get_product`, `get_ingredient`, etc.).
2) **Refactor orchestration flows to be session-aware:** For production/assembly/event flows, expose a session-optional public wrapper that delegates to a session-required helper. Keep the entire workflow in one transaction when a session is supplied.
3) **Stop returning ORM objects from self-managed scopes:** Return DTOs/dicts, or require the caller to own the session lifecycle. Avoid handing out objects that will be detached.
4) **Align dry-run and execution contexts:** Allow availability/dry-run helpers to accept and pass through a session so the same transactional snapshot can be reused.
5) **Document conventions:** Add a short “Session & Transactions” section to `CLAUDE.md` or `docs/workflow-refactoring-spec.md` covering: (a) when to accept/require a session, (b) no returning ORM instances from closed scopes, (c) multi-step operations must be single-transaction.

## Test Gaps to Close
- Production/assembly: invoke `record_*` with a provided session and force an error after FIFO consumption to assert full rollback (inventory counts and ledger unchanged).
- Session pass-through: tests that `consume_fifo` and service helpers do not open new sessions when one is provided.
- Detached object guardrails: tests that accessing relationships on returned objects from closed scopes fails, prompting DTO-returning APIs.
- Event workflows: clone/assign/remove inside one session; induce a failure to ensure atomic rollback.

## Notes on Specific Files Reviewed
- `src/services/batch_production_service.py`: Ignores provided sessions; nested `get_aggregated_ingredients` and `consume_fifo` calls run in separate scopes.
- `src/services/assembly_service.py`: Same pattern as batch production; availability and execution both open new scopes and call FIFO without session pass-through.
- `src/services/recipe_service.py`: All getters/CRUD wrap their own scope and return ORM objects; detached on return.
- `src/services/inventory_item_service.py`: Returns ORM from closed scope; calls other services that open new sessions while inside its own scope.
- `src/services/ingredient_service.py` and `src/services/product_service.py`: Similar detached-return pattern; optional session not exposed.
- `src/services/event_service.py`: CRUD/queries return detached ORM; complex flows cannot share a transaction.
- `src/tests/conftest.py`: Uses an in-memory DB and monkeypatches the session factory, but no coverage for nested sessions, rollback paths, or session pass-through behaviors.

## Quick Wins
- Add `session` parameters to availability/dry-run helpers and forward them.
- Introduce DTO serializers for reads; keep ORM instances internal to session-managed contexts.
- Update production/assembly entrypoints to accept a session and to call FIFO/aggregation with that same session.
