---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "CATALOG Mode"
phase: "Phase 1 - Mode Implementation"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-05"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - CATALOG Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement CATALOG mode with dashboard and 6 existing tabs migrated.

**Success Criteria**:
- CATALOG mode shows dashboard with entity counts (FR-007)
- All 6 tabs accessible: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages (FR-018)
- All existing tab functionality preserved (FR-019)
- Tab switching within CATALOG mode works correctly

**User Story**: US4 - CATALOG Mode for Definitions (Priority P2)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes), WP02 (Main Window Navigation)

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - User Story 4, FR-007, FR-018, FR-019
- `kitty-specs/038-ui-mode-restructure/data-model.md` - CatalogMode definition
- Existing tabs in `src/ui/`

**Existing Tab Files**:
- `src/ui/ingredients_tab.py` (58KB)
- `src/ui/products_tab.py` (37KB)
- `src/ui/recipes_tab.py` (19KB)
- `src/ui/finished_units_tab.py` (27KB)
- `src/ui/finished_goods_tab.py` (14KB)
- `src/ui/packages_tab.py` (17KB)

**Constraints**:
- Minimal changes to existing tabs - use composition
- No business logic in UI layer
- Preserve all CRUD operations

**Parallelization**: This work package can be done in parallel with WP04 (OBSERVE Mode).

## Subtasks & Detailed Guidance

### Subtask T014 - Create CatalogDashboard

**Purpose**: Show entity counts for CATALOG mode (FR-007).

**Steps**:
1. Create `src/ui/dashboards/catalog_dashboard.py`
2. Extend BaseDashboard
3. Display counts: ingredients, products, recipes, finished units, finished goods, packages

**Files**: `src/ui/dashboards/catalog_dashboard.py`

**Implementation**:
```python
class CatalogDashboard(BaseDashboard):
    def __init__(self, master):
        super().__init__(master)
        self._create_stats()

    def _create_stats(self):
        self.add_stat("Ingredients", "0")
        self.add_stat("Products", "0")
        self.add_stat("Recipes", "0")
        self.add_stat("Finished Units", "0")
        self.add_stat("Finished Goods", "0")
        self.add_stat("Packages", "0")

    def refresh(self):
        # Use service methods to get counts
        from services.ingredient_service import get_all_ingredients
        from services.product_catalog_service import get_all_products
        # ... update stat labels
```

**Parallel?**: No - needed for T015.

### Subtask T015 - Create CatalogMode

**Purpose**: Container for CATALOG mode with dashboard and tabs.

**Steps**:
1. Create `src/ui/modes/catalog_mode.py`
2. Extend BaseMode
3. Set up dashboard and CTkTabview
4. Integrate tabs from T016-T021

**Files**: `src/ui/modes/catalog_mode.py`

**Implementation**:
```python
class CatalogMode(BaseMode):
    def __init__(self, master):
        super().__init__(master, name="CATALOG")
        self.dashboard = CatalogDashboard(self)
        self.dashboard.pack(fill="x", padx=10, pady=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self._setup_tabs()

    def _setup_tabs(self):
        self.tabview.add("Ingredients")
        self.tabview.add("Products")
        self.tabview.add("Recipes")
        self.tabview.add("Finished Units")
        self.tabview.add("Finished Goods")
        self.tabview.add("Packages")
```

**Parallel?**: No - needed before tab integration.

### Subtask T016 - Integrate ingredients_tab.py [P]

**Purpose**: Add Ingredients tab to CATALOG mode.

**Steps**:
1. Review existing `ingredients_tab.py` structure
2. Instantiate IngredientsTab in CatalogMode
3. Add to "Ingredients" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/ingredients_tab.py` (may need minor adjustments)

**Integration Pattern**:
```python
# In CatalogMode._setup_tabs()
ingredients_frame = self.tabview.tab("Ingredients")
self.ingredients_tab = IngredientsTab(ingredients_frame)
self.ingredients_tab.pack(fill="both", expand=True)
```

**Verification**: Test Add, Edit, Delete, Search, Filter operations.

**Parallel?**: Yes - different file from other tab integrations.

### Subtask T017 - Integrate products_tab.py [P]

**Purpose**: Add Products tab to CATALOG mode.

**Steps**:
1. Review existing `products_tab.py` structure
2. Instantiate ProductsTab in CatalogMode
3. Add to "Products" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/products_tab.py` (may need minor adjustments)

**Verification**: Test Add, Edit, Delete, Search, Filter, brand/pricing display.

**Parallel?**: Yes.

### Subtask T018 - Integrate recipes_tab.py [P]

**Purpose**: Add Recipes tab to CATALOG mode.

**Steps**:
1. Review existing `recipes_tab.py` structure
2. Instantiate RecipesTab in CatalogMode
3. Add to "Recipes" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/recipes_tab.py` (may need minor adjustments)

**Verification**: Test Add, Edit, Delete, ingredient linking.

**Parallel?**: Yes.

### Subtask T019 - Integrate finished_units_tab.py [P]

**Purpose**: Add Finished Units tab to CATALOG mode.

**Steps**:
1. Review existing `finished_units_tab.py` structure
2. Instantiate FinishedUnitsTab in CatalogMode
3. Add to "Finished Units" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/finished_units_tab.py` (may need minor adjustments)

**Parallel?**: Yes.

### Subtask T020 - Integrate finished_goods_tab.py [P]

**Purpose**: Add Finished Goods tab to CATALOG mode.

**Steps**:
1. Review existing `finished_goods_tab.py` structure
2. Instantiate FinishedGoodsTab in CatalogMode
3. Add to "Finished Goods" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/finished_goods_tab.py` (may need minor adjustments)

**Parallel?**: Yes.

### Subtask T021 - Integrate packages_tab.py [P]

**Purpose**: Add Packages tab to CATALOG mode.

**Steps**:
1. Review existing `packages_tab.py` structure
2. Instantiate PackagesTab in CatalogMode
3. Add to "Packages" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/catalog_mode.py` (modify)
- `src/ui/packages_tab.py` (may need minor adjustments)

**Parallel?**: Yes.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large tab files may have hidden dependencies | Review imports carefully; test thoroughly |
| Tab parent reference issues | Ensure correct parent frame passed |
| Performance with large data | Dashboard uses service methods with limits |

## Definition of Done Checklist

- [ ] CatalogDashboard shows all 6 entity counts
- [ ] CatalogMode contains all 6 tabs
- [ ] Ingredients tab: Add, Edit, Delete, Search, Filter work
- [ ] Products tab: All CRUD operations work
- [ ] Recipes tab: All CRUD operations work
- [ ] Finished Units tab: All operations work
- [ ] Finished Goods tab: All operations work
- [ ] Packages tab: All operations work
- [ ] Tab switching within mode works
- [ ] Dashboard refreshes correctly

## Review Guidance

- Test each tab's CRUD operations
- Verify dashboard counts match actual data
- Check for visual regressions
- Ensure no functionality was lost

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-05T22:40:43Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-05T22:43:11Z – system – shell_pid= – lane=for_review – Moved to for_review
