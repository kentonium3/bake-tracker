# Research: FK Resolution in Transaction Import Service

**Date**: 2026-01-28
**Question**: How does transaction_import_service handle FK resolution? Can we add resolution modes?

## Findings

### Current Implementation

`transaction_import_service.py` does **NOT** use the `FKResolverCallback` protocol from `fk_resolver_service.py`. Instead, it has its own inline resolution logic:

1. **Product Resolution** (`_resolve_product_by_slug`, lines 193-278):
   - Tries composite slug format: `ingredient_slug:brand:qty:unit`
   - Falls back to: integer ID, UPC code, GTIN
   - If not found: attempts to create provisional product (`_try_create_provisional_from_slug`)
   - If creation fails: adds error to result

2. **Supplier Resolution** (`_resolve_supplier`, line 575):
   - Simple name-based lookup
   - Falls back to "Unknown" supplier

### Implications for FK Resolution Modes

The current behavior is closest to "auto" mode:
- Tries best-match (multiple resolution strategies)
- Creates provisional products when possible
- Falls back gracefully

**To implement the three modes:**

| Mode | Behavior | Implementation |
|------|----------|----------------|
| `interactive` | Prompt user on failure | Add callback parameter, use FKResolverCallback protocol |
| `auto` | Current behavior | No change needed |
| `strict` | Fail on any unresolved | Early exit on first resolution failure |

### Decision

For MVP (this feature), implement only **auto** and **strict** modes:
- `auto`: Current behavior (default for CLI - AI-friendly)
- `strict`: Fail on first unresolved FK (for validation workflows)

**Defer `interactive` mode** - it would require significant changes to pass callbacks through the service layer, and CLI interactive prompts are complex. The existing `aug-import` command already has interactive mode for catalog imports.

### Code Changes Required

1. **transaction_import_service.py**:
   - Add `strict_mode: bool = False` parameter to `import_purchases()` and `import_adjustments()`
   - In strict mode: return early on first product resolution failure
   - In auto mode: continue with provisional creation (current behavior)

2. **import_export_cli.py**:
   - Add `--resolve-mode` flag with choices: `auto` (default), `strict`
   - Pass `strict_mode=True` when `--resolve-mode=strict`

### Alternatives Considered

1. **Integrate FKResolverCallback**: Too invasive for this feature scope
2. **Full interactive support**: Requires CLI prompt infrastructure
3. **No resolution modes**: Misses strict validation use case

### Recommendation

Implement auto (default) and strict modes only. This covers:
- AI workflows: auto mode with JSON output
- Validation workflows: strict mode + dry-run
- Human interactive: Use existing `aug-import` command instead
