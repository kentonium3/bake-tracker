# Quickstart: UI Mode Restructure

**Feature**: 038-ui-mode-restructure
**Date**: 2026-01-05

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Virtual environment

### Setup

```bash
# Navigate to feature worktree
cd .worktrees/038-ui-mode-restructure

# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### Running the Application

```bash
python src/main.py
```

### Running Tests

```bash
# All tests
pytest src/tests -v

# UI tests only (when created)
pytest src/tests/ui -v

# With coverage
pytest src/tests -v --cov=src
```

## Development Workflow

### 1. Base Classes First

Before implementing modes, create base classes:

```bash
# Create directories
mkdir -p src/ui/base src/ui/modes src/ui/dashboards src/ui/tabs

# Create __init__.py files
touch src/ui/base/__init__.py
touch src/ui/modes/__init__.py
touch src/ui/dashboards/__init__.py
touch src/ui/tabs/__init__.py
```

**Order of implementation**:
1. `src/ui/base/standard_tab_layout.py` - Tab layout pattern
2. `src/ui/base/base_mode.py` - Mode container base
3. Mode implementations (can parallelize after base classes)

### 2. Testing Strategy

**Unit tests for base classes**:
- `test_standard_tab_layout.py` - Verify region creation, button placement
- `test_base_mode.py` - Verify tab state preservation, activation/deactivation

**Integration tests**:
- Mode switching preserves tab selection
- Keyboard shortcuts work (Ctrl+1-5)
- Dashboard data loads within 1 second

### 3. Mode Implementation Order

Recommended sequence (based on dependencies):

1. **Base classes** (blocking)
2. **CATALOG mode** (most tabs, good for testing pattern)
3. **OBSERVE mode** (parallel with CATALOG - independent)
4. **PLAN mode** (after patterns established)
5. **SHOP mode** (new tabs needed)
6. **PRODUCE mode** (new tabs needed)
7. **main_window.py integration** (after all modes work)

## Key Files

### New Files to Create

| File | Purpose |
|------|---------|
| `src/ui/base/base_mode.py` | BaseMode abstract class |
| `src/ui/base/standard_tab_layout.py` | StandardTabLayout class |
| `src/ui/modes/catalog_mode.py` | CATALOG mode |
| `src/ui/modes/plan_mode.py` | PLAN mode |
| `src/ui/modes/shop_mode.py` | SHOP mode |
| `src/ui/modes/produce_mode.py` | PRODUCE mode |
| `src/ui/modes/observe_mode.py` | OBSERVE mode |
| `src/ui/dashboards/catalog_dashboard.py` | CATALOG dashboard |
| `src/ui/dashboards/plan_dashboard.py` | PLAN dashboard |
| `src/ui/dashboards/shop_dashboard.py` | SHOP dashboard |
| `src/ui/dashboards/produce_dashboard.py` | PRODUCE dashboard |
| `src/ui/dashboards/observe_dashboard.py` | OBSERVE dashboard |
| `src/ui/tabs/shopping_lists_tab.py` | Shopping Lists tab |
| `src/ui/tabs/purchases_tab.py` | Purchases tab |
| `src/ui/tabs/assembly_tab.py` | Assembly tab |
| `src/ui/tabs/packaging_tab.py` | Packaging tab |
| `src/ui/tabs/event_status_tab.py` | Event Status tab |

### Files to Modify

| File | Changes |
|------|---------|
| `src/ui/main_window.py` | Replace flat tabs with mode bar + mode container |
| `src/ui/ingredients_tab.py` | Integrate with mode structure |
| `src/ui/products_tab.py` | Integrate with mode structure |
| `src/ui/recipes_tab.py` | Integrate with mode structure |
| `src/ui/finished_units_tab.py` | Integrate with mode structure |
| `src/ui/finished_goods_tab.py` | Integrate with mode structure |
| `src/ui/packages_tab.py` | Integrate with mode structure |
| `src/ui/events_tab.py` | Integrate with mode structure |
| `src/ui/inventory_tab.py` | Integrate with mode structure |
| `src/ui/production_tab.py` | Merge with production_dashboard_tab.py |
| `src/ui/dashboard_tab.py` | Enhance for OBSERVE mode |

## Parallelization Guide

### Safe to Parallelize

After base classes are complete:

**Stream A (Claude)**:
- PRODUCE mode (produce_mode.py)
- Assembly tab (assembly_tab.py)
- Packaging tab (packaging_tab.py)
- main_window.py integration

**Stream B (Gemini)**:
- CATALOG mode (catalog_mode.py)
- OBSERVE mode (observe_mode.py)
- Event Status tab (event_status_tab.py)
- Tab migrations within those modes

### Not Safe to Parallelize

- Base classes must complete before any mode work
- main_window.py integration must wait for all modes
- Files in same mode should be done sequentially or by same agent

## Testing Checklist

Before marking complete:

- [ ] All 5 modes accessible via mode bar
- [ ] Keyboard shortcuts Ctrl+1-5 work
- [ ] Tab selection preserved when switching modes
- [ ] Dashboards load within 1 second
- [ ] All existing functionality works after migration
- [ ] Default mode is OBSERVE on launch
- [ ] All existing tests pass
- [ ] New base class tests pass
