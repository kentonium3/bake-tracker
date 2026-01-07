# Research Decision Log

## Summary

- **Feature**: 041-manual-inventory-adjustments
- **Date**: 2026-01-07
- **Researchers**: Claude (lead), Kent Gale (stakeholder)
- **Open Questions**: None - all clarifications resolved during planning interrogation

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Create new InventoryDepletion model | Design doc assumed existing model; codebase has no depletion audit trail | Grep search: no Depletion model exists; consume_fifo() modifies qty directly | final |
| Add DepletionReason enum to enums.py | Need extensible reason tracking; aligns with existing enum patterns (ProductionStatus, LossCategory) | src/models/enums.py uses str(Enum) pattern | final |
| Depletions-only scope | Inventory increases must go through Purchase workflow for proper FIFO costing | Spec clarification 2026-01-07; aligns with Constitution Principle II | final |
| Hardcode user identifier as "desktop-user" | Single-user desktop app; no auth system | Planning interrogation answer; spec assumption | final |
| Parallel development: Claude (service) / Gemini (UI) | Layered architecture enables clean separation; minimizes conflict risk | Constitution Principle V; CLAUDE.md architecture rules | final |
| Service method accepts session parameter | Follows established session management pattern per CLAUDE.md | CLAUDE.md Session Management section; inventory_item_service.py patterns | final |

## Evidence Highlights

- **Codebase has no InventoryDepletion model** - Searched `src/models/` and found no depletion tracking. ProductionConsumption tracks production, but no general depletion audit trail exists.
- **consume_fifo() modifies quantity without audit** - `inventory_item_service.py:396` directly decrements `item.quantity` without creating audit records.
- **Existing enum pattern** - `src/models/enums.py` uses `class X(str, Enum)` pattern which we'll follow for DepletionReason.
- **Session management pattern established** - CLAUDE.md documents the `session=None` pattern for composable transactions.

## Risks / Concerns

- **FIFO integration**: Manual adjustments deplete from a specific InventoryItem (user-selected), not FIFO across multiple items. This is intentional - user knows which physical item they're adjusting.
- **Retroactive production consumption**: Existing ProductionConsumption records don't link to new InventoryDepletion model. This is acceptable - we're not retrofitting existing data.

## Next Actions

1. Proceed to Phase 1: Design & Contracts
2. Generate data-model.md with InventoryDepletion entity
3. Define service method contract for manual_adjustment()
4. Update agent context for parallel development
