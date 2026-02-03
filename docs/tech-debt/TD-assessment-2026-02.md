# Technical Debt Assessment: F091-F093 Context

**Assessment Date**: 2026-02-02
**Context**: Evaluating TD items in relation to F091-F093 implementation sequence

---

## Assessment Summary

| TD# | Title | Current Priority | Relevance to F091-F093 | Recommendation | New Priority |
|-----|-------|-----------------|----------------------|----------------|--------------|
| **TD-012** | Import slug upgrade | High (deferred) | LOW - Multi-tenant concern | KEEP DEFERRED | Deferred |
| **TD-011** | Consolidate slug utils | Low | NONE - Code cleanup | DO LATER | Low |
| **TD-010** | Purchase service boundaries | Low | **HIGH** - Session + boundaries | **DO WITH F091** | High |
| **TD-008** | Materials composition layering | Low | **MEDIUM** - Layering + errors | **DO WITH F091-F093** | Medium |

---

## Detailed Analysis

### TD-012: Import Slug Upgrade via previous_slug

**Current Status:** Deferred until multi-tenant migration (Q2 2026)

**Relationship to F091-F093:**
- ❌ Not related to transaction documentation (F091)
- ❌ Not related to pagination DTOs (F092)
- ❌ Not related to API standardization (F093)
- ✅ Related to service layer architecture (uses service functions)

**Assessment:**
- **Keep deferred** - This is explicitly scoped for multi-tenant migration
- Not urgent for current desktop app
- Properly documented with clear acceptance criteria
- Timeline is appropriate (Q2 2026 when multi-tenant prep starts)

**Action:** ✅ No change - remains deferred

**Reason:** Desktop app doesn't import renamed entities across exports, so duplicate risk is theoretical. Multi-tenant migration is the actual trigger.

---

### TD-011: Consolidate Slug Utils

**Current Status:** Low priority, small effort

**Relationship to F091-F093:**
- ❌ Not related to transaction documentation (F091)
- ❌ Not related to pagination DTOs (F092)
- ❌ Not related to API standardization (F093)
- ⚠️ Minor code quality improvement (DRY principle)

**Assessment:**
- **Do later** - Pure refactoring with no functional impact
- No interaction with F091-F093
- Can be done anytime (or never)
- Very low risk, very low value

**Action:** ✅ Keep as low priority, defer indefinitely

**Reason:** F091-F093 are about architecture, patterns, and standards. Consolidating two similar functions doesn't improve those areas and can wait until someone is already touching slug_utils.py for another reason.

---

### TD-010: Purchase Service Boundary Violations

**Current Status:** Low priority (2.5-3 hours)

**Relationship to F091-F093:**
- ✅ **HIGHLY RELEVANT to F091** - Involves session parameter pattern
- ✅ **HIGHLY RELEVANT to F093** - Exception pattern (ProductNotFound)
- ✅ **HIGHLY RELEVANT to architecture** - Service boundary violations
- ✅ Related to session management best practices

**Assessment:**
- **DO WITH F091** - Exemplifies the exact patterns F091 documents
- **DO WITH F093** - Will benefit from exception standardization
- Low effort (2.5-3 hours)
- Demonstrates proper service boundaries
- Shows correct session handling in practice

**Issues in purchase_service.py:**

1. **Direct model query instead of service:**
```python
# ANTI-PATTERN (current)
product = session.query(Product).filter_by(id=product_id).first()
if not product:
    raise ProductNotFound(product_id)

# CORRECT PATTERN (should be)
product = product_catalog_service.get_product(product_id, session=session)
```

2. **Inline entity creation instead of service:**
```python
# ANTI-PATTERN (current)
supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
if not supplier:
    supplier = Supplier(name=store_name, city="Unknown", state="XX", zip_code="00000")
    session.add(supplier)
    session.flush()

# CORRECT PATTERN (should be)
supplier = supplier_service.get_or_create_supplier(name=store_name, session=session)
```

**Why do with F091:**
- F091 documents transaction boundaries and session parameter patterns
- `purchase_service.record_purchase()` is a multi-step operation that should be documented per F091
- Fixing boundary violations demonstrates the patterns F091 prescribes
- Creates working examples for F091 documentation

**Why do with F093:**
- F093 standardizes exception handling (ProductNotFound pattern)
- Demonstrates proper service delegation
- Type hints will be added (product_catalog_service.get_product return type)

**Action:** ⚠️ **UPGRADE TO HIGH PRIORITY - Do as part of F091 implementation**

**Rationale:** This TD directly demonstrates the architecture patterns that F091-F093 are documenting and standardizing. Fixing it provides concrete examples and validates the patterns work correctly.

---

### TD-008: Materials Composition Layering & Quantity Validation

**Current Status:** Low priority (3-6 hours)

**Relationship to F091-F093:**
- ✅ **RELEVANT to F091** - Session management (model calls services)
- ✅ **RELEVANT to F093** - Error handling (swallows exceptions)
- ✅ **RELEVANT to architecture** - Model/service boundary violations
- ⚠️ More complex than TD-010 (3-6 hours vs 2.5-3 hours)

**Assessment:**
- **Consider doing with F091-F093** - Related but not critical path
- **Could defer** - Core workflows functional, this is polish
- Medium effort (3-6 hours)
- Impacts model/service boundaries

**Issues in composition.py:**

1. **Model calls service functions:**
```python
# ANTI-PATTERN (current)
# In Composition model
def get_component_cost(self):
    try:
        return material_unit_service.get_current_cost(...)
    except Exception:
        return 0  # Swallows errors!
```

2. **Silent error masking:**
```python
# ANTI-PATTERN (current)
except Exception:
    return 0  # No logging, no user feedback
```

**Why consider doing with F091-F093:**
- Demonstrates proper model/service separation
- Shows correct error handling (F093)
- Shows correct session management (F091)
- Removes silent error swallowing

**Why might defer:**
- Not on critical path for F091-F093
- More complex (needs UI changes to compute cost/availability)
- Core workflows already functional
- 3-6 hours is non-trivial

**Action:** ⚠️ **CONDITIONAL - Do if time permits, otherwise defer**

**Rationale:** This TD is related to F091-F093 patterns but is not required for them to succeed. If F091-F093 implementation goes smoothly and TD-010 is resolved quickly, tackle this. Otherwise, defer as originally planned.

---

## Recommended Implementation Sequence

### Phase 1: F091 + TD-010 (4-5 days total)
```
Week 1:
├─ Day 1-3: F091 (Transaction Boundary Documentation)
│  ├─ Document all service function transaction boundaries
│  ├─ Audit multi-step operations
│  ├─ Create transaction patterns guide
│  └─ Update docstrings
│
└─ Day 3-4: TD-010 (Purchase Service Boundaries) - PARALLEL WITH F091
   ├─ Add supplier_service.get_or_create_supplier() [30-45 min]
   ├─ Update purchase_service.py [30 min]
   ├─ Add tests [45 min]
   ├─ Integration testing [30 min]
   └─ Document as F091 example [15 min]
```

**Rationale for parallel work:**
- TD-010 provides real-world validation of F091 patterns
- Purchase service becomes a documented example
- Small effort (2.5-3 hours) fits within F091 timeline
- Creates better documentation with concrete examples

### Phase 2: F092 (Pagination DTOs) - 4 hours
```
Day 5:
└─ F092 (Pagination DTOs Foundation)
   ├─ Create PaginationParams dataclass
   ├─ Create PaginatedResult[T] dataclass
   ├─ Document usage patterns
   └─ Add to service DTOs module
```

### Phase 3: F093 (Core API Standardization) - 3-5 days
```
Week 2:
├─ Day 1-2: Exception Pattern (~40 functions)
├─ Day 3: Eliminate Tuples (~15 functions)
└─ Day 4-5: Complete Type Hints (~60 functions)
```

### Phase 4: TD-008 (Optional) - 3-6 hours
```
Week 2-3 (if time permits):
└─ TD-008 (Materials Composition Layering)
   ├─ Remove service calls from Composition model
   ├─ Move cost/availability computation to service layer
   ├─ Fix error handling (no silent 0 returns)
   └─ Validate MaterialUnit quantities
```

**Or defer TD-008 until:**
- Next time someone works on materials/composition
- Broader service layer cleanup
- When error handling improvements are prioritized

---

## Summary of Recommendations

### ✅ Do Now (with F091-F093)

**TD-010: Purchase Service Boundary Violations**
- **New Priority:** HIGH
- **Timeline:** During F091 implementation (Week 1, Day 3-4)
- **Effort:** 2.5-3 hours
- **Why:** Validates F091 patterns, small effort, high alignment

### ⚠️ Consider (if time permits)

**TD-008: Materials Composition Layering**
- **Priority:** MEDIUM (conditional)
- **Timeline:** After F093, if time permits
- **Effort:** 3-6 hours
- **Why:** Related to patterns but not critical path

### ✅ Keep Deferred

**TD-012: Import Slug Upgrade**
- **Priority:** Deferred until Q2 2026 (multi-tenant prep)
- **Why:** Correctly scoped to actual use case

**TD-011: Consolidate Slug Utils**
- **Priority:** Low (indefinite deferral)
- **Why:** Low value, no interaction with F091-F093

---

## Updated Tech Debt Status

After this assessment:

### Active (Address Now)
- **TD-010** → Upgraded to HIGH, do with F091

### Conditional (If Time Permits)
- **TD-008** → Consider after F093 if timeline allows

### Deferred (No Change)
- **TD-012** → Remains deferred until multi-tenant migration
- **TD-011** → Remains low priority indefinitely

---

## Key Insights

1. **TD-010 is a perfect F091 companion** - It demonstrates the exact session handling and service boundary patterns that F091 documents. Fixing it during F091 creates concrete examples and validates the patterns.

2. **TD-008 is related but not critical** - It shares themes (layering, sessions, errors) but requires more work and isn't required for F091-F093 success. Good candidate for "if time permits" or future work.

3. **TD-012 and TD-011 are correctly deferred** - Neither interact with F091-F093. TD-012 is properly scoped to multi-tenant needs, TD-011 can wait indefinitely.

4. **Doing TD-010 with F091 creates better documentation** - The purchase service becomes a real-world example of proper transaction boundaries and service delegation, making F091 docs more valuable.

---

**END OF ASSESSMENT**
