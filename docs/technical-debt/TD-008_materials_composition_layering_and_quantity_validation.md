# TD-008: Materials Composition Layering & Quantity Validation Polish

| Attribute | Value |
|-----------|-------|
| **Status** | Open |
| **Priority** | Low |
| **Created** | 2026-01-11 |
| **Related Features** | F047 (Materials Management System) |
| **Location** | `src/models/composition.py`, `src/services/material_consumption_service.py` |

## Description

Two minor issues remain after F047/F047A that are unlikely to break core workflows, but reduce debuggability and clarity:

1. **Model/service layering leak + error masking**: `Composition` calls service-layer functions to compute material costs/availability and swallows exceptions by returning `0`.
2. **MaterialUnit quantity semantics**: MaterialUnit-based component quantities are effectively “counts”, but validation/rounding semantics are not explicit, which can hide invalid inputs.

## Current Behavior

### 1) Composition calls services and hides failures
- `Composition.get_component_cost()` and `Composition.get_component_availability()` import service functions (e.g., `material_unit_service.get_current_cost`, `get_available_inventory`) and on any exception return `0`.
- These service calls may create their own sessions and can be invoked in bulk (lists/tables), increasing query load.

### 2) MaterialUnit quantities are not strictly validated as integer counts
- MaterialUnit compositions use a float `component_quantity` and compute needed units by arithmetic with `assembly_quantity`, then round/convert.
- If non-integer quantities slip into a “count-like” field, behavior can be surprising (rounding rather than explicit validation error).

## Expected Behavior

### 1) Clean layering and actionable failures
- `Composition` (model) should not call service-layer functions or manage sessions.
- UI/service layers should compute material cost/availability using an existing session and should surface errors as actionable messages (not silently as `0`).

### 2) Clear “count vs continuous” rules for MaterialUnit compositions
- For MaterialUnit-based composition entries, quantities should be treated as **integer counts**.
- Non-integer values should be rejected with a clear validation error (or explicitly supported and documented).

## Impact

- **Debuggability**: silent `0` cost/availability can hide real issues and lead to confusing “everything is free / unavailable” displays.
- **Performance**: per-row service calls can lead to extra sessions/queries in list views.
- **Data correctness clarity**: rounding a count-like value can hide invalid data entry and make inventory/cost math hard to reason about.

## Suggested Implementation

### 1) Remove service calls from `Composition`
1. Replace `Composition.get_component_cost()` and `get_component_availability()` material-unit branches with either:
   - purely relationship-based lookups (no service calls), or
   - removal of these helpers entirely in favor of service methods that accept a session.
2. Remove blanket `except Exception` fallbacks; if a computation fails, either raise (in service layer) or display a specific error indicator in UI.

### 2) Enforce integer semantics for MaterialUnit composition quantities
1. Validate that MaterialUnit-based `component_quantity` is integer-like at input boundaries (UI form and/or `composition_service`).
2. In consumption validation, prefer explicit integer checks over rounding (or only allow rounding with a clear UI warning).

## Workaround

- Users typically enter whole-number counts; issues tend to appear only with unusual values or when an internal calculation fails.
- If cost/availability displays as `0`, operators can still attempt assembly; the assembly-time consumption validation should enforce “hard stop” rules.

## Effort Estimate

3-6 hours

## Reason for Deferral

Core F047 workflows are functional after F047A; this is polish aimed at maintainability and clearer invariants rather than a user-blocking bug.

