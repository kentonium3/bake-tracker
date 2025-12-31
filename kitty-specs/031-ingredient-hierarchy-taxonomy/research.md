# Research: Ingredient Hierarchy Taxonomy

**Feature**: 031-ingredient-hierarchy-taxonomy
**Date**: 2025-12-30
**Status**: Complete

---

## Executive Summary

Research validates the three-tier self-referential hierarchy approach for ingredient taxonomy. The existing codebase patterns, SQLAlchemy capabilities, and CustomTkinter widget options all support the proposed design with minimal friction.

---

## Decision Log

### D1: Hierarchy Data Model Approach

**Decision**: Self-referential single table with `parent_ingredient_id` FK

**Rationale**:
- Simpler than separate Category/Subcategory tables
- SQLAlchemy natively supports self-referential relationships
- Existing `Ingredient` model already has infrastructure (BaseModel, to_dict, etc.)
- Matches constitution principle III (future-proof schema) - can extend depth later if needed

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Separate Category table | Adds complexity, requires migration of existing ingredient references |
| Nested Set model | Over-engineered for 3-level depth; complex insert/update logic |
| Closure Table | Better for arbitrary depth; overkill for fixed 3 levels |
| Materialized Path | String manipulation complexity; SQLite text comparison issues |

**Evidence**: See source-register.csv #001-003

---

### D2: Hierarchy Level Enforcement

**Decision**: Hard constraint of 3 levels (0, 1, 2) via CHECK constraint and service validation

**Rationale**:
- Matches user mental model (Category → Type → Specific Ingredient)
- Simplifies UI (fixed tree depth)
- Can be relaxed later if domain expands (constitution VII)
- Validation at both DB and service layer provides defense in depth

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Unlimited depth | UI complexity, user confusion, no current need |
| 2 levels only | Insufficient granularity (Chocolate → Chips misses Dark/Milk distinction) |
| 4+ levels | Exceeds baking domain needs; adds UI navigation friction |

**Evidence**: Design document section 10 (Q1), user scenario analysis

---

### D3: Tree Widget Implementation

**Decision**: Use tkinter.ttk.Treeview wrapped in CustomTkinter styling

**Rationale**:
- tkinter.ttk.Treeview is native Python, well-documented, performant
- CustomTkinter can style ttk widgets via CTkFrame containers
- Supports expand/collapse, item selection, and search integration
- No external dependencies required

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Custom canvas-based widget | High development effort; reinventing wheel |
| Third-party tree library | Adds dependency; may conflict with CustomTkinter theming |
| Flat list with indentation | Poor UX; doesn't support expand/collapse behavior |

**Evidence**: See source-register.csv #004-005, CustomTkinter documentation review

---

### D4: AI Categorization Integration

**Decision**: Hybrid approach - tooling accepts pre-generated JSON

**Rationale**:
- Avoids API key management complexity in desktop app
- User can choose any AI tool (Claude.ai, ChatGPT, Gemini, etc.)
- Migration tooling focuses on data transformation, not AI integration
- Matches constitution principle I (user-centric) - user controls the process

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Claude API integration | Requires API key setup; adds dependency |
| Gemini API integration | Same issues; also network requirement |
| Fully manual categorization | 487 ingredients × manual work = weeks of effort |

**Evidence**: User input during planning phase

---

### D5: Existing Data Migration Strategy

**Decision**: Export → External AI → Transform → Import (per constitution VI)

**Rationale**:
- Follows constitution VI (Schema Change Strategy for Desktop)
- Existing export/import infrastructure (F030) provides foundation
- AI suggestions reviewed before import (human-in-the-loop)
- Rollback is simple: restore from pre-migration export

**Migration Steps**:
1. Export all ingredients to JSON (existing capability)
2. User runs AI categorization externally, gets suggested hierarchy JSON
3. Transform script merges suggestions with existing data
4. Review/edit transformed JSON (manual review step)
5. Delete database, recreate with new schema columns
6. Import transformed data

**Evidence**: Constitution VI, F030 export/import implementation

---

### D6: Leaf-Only Product Assignment

**Decision**: Only Level 2 (leaf) ingredients can have Products and be used in Recipes

**Rationale**:
- Prevents ambiguity (is "Dark Chocolate" a product or category?)
- Matches real-world semantics (you buy specific ingredients, not categories)
- Simplifies product catalog management
- Clear validation rule for service layer

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Any level can have products | Ambiguous; user confusion about which level to use |
| Level 1 and 2 can have products | Still ambiguous; complicates queries |

**Evidence**: Design document section 10 (Q2)

---

## Technical Research

### R1: SQLAlchemy Self-Referential Pattern

**Finding**: SQLAlchemy natively supports self-referential relationships via `relationship()` with `remote_side` parameter.

```python
# Pattern from SQLAlchemy documentation
class Ingredient(Base):
    __tablename__ = 'ingredients'
    id = Column(Integer, primary_key=True)
    parent_ingredient_id = Column(Integer, ForeignKey('ingredients.id'))

    children = relationship("Ingredient",
                           backref=backref('parent', remote_side=[id]))
```

**Implication**: No special handling needed; standard SQLAlchemy patterns apply.

---

### R2: Tree Traversal Query Patterns

**Finding**: For 3-level fixed depth, simple recursive queries are efficient.

**Get all descendants (recursive CTE)**:
```sql
WITH RECURSIVE descendants AS (
    SELECT id, display_name, parent_ingredient_id, hierarchy_level
    FROM ingredients WHERE id = :ancestor_id
    UNION ALL
    SELECT i.id, i.display_name, i.parent_ingredient_id, i.hierarchy_level
    FROM ingredients i
    INNER JOIN descendants d ON i.parent_ingredient_id = d.id
)
SELECT * FROM descendants WHERE id != :ancestor_id;
```

**Get ancestors (path to root)**:
```sql
WITH RECURSIVE ancestors AS (
    SELECT id, display_name, parent_ingredient_id, hierarchy_level
    FROM ingredients WHERE id = :leaf_id
    UNION ALL
    SELECT i.id, i.display_name, i.parent_ingredient_id, i.hierarchy_level
    FROM ingredients i
    INNER JOIN ancestors a ON a.parent_ingredient_id = i.id
)
SELECT * FROM ancestors;
```

**SQLite Compatibility**: SQLite 3.8.3+ supports recursive CTEs (confirmed available).

**Implication**: Can implement as SQLAlchemy text queries or pure Python recursion for small datasets.

---

### R3: CustomTkinter + ttk.Treeview Integration

**Finding**: CustomTkinter wraps tkinter but allows direct use of ttk widgets.

**Integration Pattern**:
```python
import customtkinter as ctk
from tkinter import ttk

class IngredientTreeWidget(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Configure ttk style for dark mode compatibility
        style = ttk.Style()
        style.theme_use('clam')  # Themeable base

        # Create Treeview inside CTkFrame
        self.tree = ttk.Treeview(self, selectmode='browse')
        self.tree.pack(fill='both', expand=True)
```

**Implication**: Standard tkinter Treeview tutorials and examples apply.

---

### R4: Existing Ingredient Model Analysis

**Current Model** (`src/models/ingredient.py`):
```python
class Ingredient(Base):
    id = Column(Integer, primary_key=True)
    display_name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    category = Column(String(100))  # WILL BE DEPRECATED
    # ... density fields, notes, etc.
```

**Required Additions**:
```python
parent_ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=True)
hierarchy_level = Column(Integer, nullable=False, default=2)
```

**Relationships to Add**:
```python
children = relationship("Ingredient", backref=backref('parent', remote_side=[id]))
```

**Implication**: Minimal model changes; existing fields preserved.

---

### R5: Existing Service Patterns

**Session Pattern**: Per CLAUDE.md, service functions accept optional `session` parameter.

**Existing ingredient_service functions**:
- `get_ingredient(slug, session=None)` - Returns dict
- `create_ingredient(data, session=None)` - Creates with validation
- `update_ingredient(slug, data, session=None)` - Updates with validation
- `delete_ingredient(slug, session=None)` - Deletes with cascade checks

**New Hierarchy Service**: Should follow same pattern, placed in `src/services/ingredient_hierarchy_service.py`.

---

## Open Questions

None - all major decisions resolved during planning phase.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI categorization produces poor suggestions | Low | Medium | Human review step before import; can manually edit JSON |
| ttk.Treeview styling conflicts with CustomTkinter | Medium | Low | Fallback to minimal styling; function over form |
| Recursive queries slow on 500+ ingredients | Low | Low | Fixed 3-level depth limits recursion; can cache if needed |
| User confused by tree navigation | Low | Medium | Design doc mockups tested mentally; real user testing planned |

---

## References

See `research/source-register.csv` for complete source list.
