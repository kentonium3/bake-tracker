# Finished Units Functionality & UI - Feature Specification

**Feature ID**: F044
**Feature Name**: Finished Units Functionality & UI
**Priority**: P1 - FOUNDATIONAL (blocks F045, F046, F047)
**Status**: Design Specification
**Created**: 2026-01-08
**Dependencies**: F037 (Recipe Redesign ✅), F042 (UI Polish ✅)
**Constitutional References**: Principle I (User-Centric Design), Principle V (Layered Architecture)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, UI mockups, and implementation patterns. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification

**The requirements are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

**Problem**: From 2026-01-07 user testing: **"Finished Units button goes nowhere"**. Users cannot define what finished products their recipes make, blocking the entire Plan → Make → Deliver workflow.

**Current State**: 
- FinishedUnit model exists in database
- No UI to create/edit/view finished units
- Recipe management has no yield type definitions
- Event planning cannot select specific finished units (blocked)

**Solution**: Implement minimal FinishedUnit management:
- Embed yield type management in Recipe Edit form
- Create read-only Finished Units catalog tab
- Enable Recipe → FinishedUnits relationship (one-to-many)

**Impact**:
- Unblocks event planning (can now specify "100 Large Cookies" not "100 cookies")
- Enables accurate batch calculations (yield-specific)
- Foundation for F045 (Finished Goods/Bundles), F046 (Shopping Lists), F047 (Assembly)

**Scope**:
- Recipe Edit form: Add "Yield Types" section with inline add/edit/delete
- Finished Units tab (CATALOG mode): Read-only view of all yield types across recipes
- Service layer: FinishedUnit CRUD operations
- Validation: Uniqueness, positive integers, referential integrity

---

## 1. Problem Statement

### 1.1 Missing Yield Type Definitions

**From user testing (2026-01-07):**
> "Finished Units button goes nowhere"

**Current Workflow (Broken):**
```
Baker: "I want to make 100 large cookies for the party"
System: "What's a 'large cookie'? I only know abstract 'Cookie Dough' recipe"
Baker: *Cannot proceed with event planning*
```

**Desired Workflow:**
```
Baker: Opens Recipe Edit for "Cookie Dough"
Baker: Defines yield types:
  - Large Cookie → 30 per batch
  - Medium Cookie → 48 per batch
  - Small Cookie → 72 per batch

Baker: Plans event, selects "Large Cookie", enters 100 needed
System: Calculates 100 ÷ 30 = 3.33 batches
System: Generates production plan: "Make 4 batches (yields 120, 20 extra)"
```

### 1.2 Real-World Use Cases

**Use Case 1: Cookie Batch Planning**
```
Recipe: Cookie Dough (1x batch)
Yield Types (user-defined):
  - Large Cookie (3-inch) → 30 per batch
  - Medium Cookie (2-inch) → 48 per batch
  - Small Cookie (1.5-inch) → 72 per batch

Event: Birthday Party
Needs: 120 large cookies

Calculation: 120 ÷ 30 = 4 batches
Cost: $12/batch × 4 = $48 total
```

**Use Case 2: Cake Size Options**
```
Recipe: Chocolate Cake (1x batch)
Yield Types (user-defined):
  - 11-inch Cake → 1 per batch (uses full batter)
  - 8-inch Cake → 2 per batch (split batter into 2 pans)
  - 6-inch Cake → 4 per batch (split batter into 4 pans)

Event: Wedding
Needs: 3 × 8-inch cakes

Calculation: 3 ÷ 2 = 1.5 batches
Cost: $24/batch × 1.5 = $36 total
```

**Use Case 3: Brownie Portioning**
```
Recipe: Brownie Batter (1x batch, 9x13 pan)
Yield Types (user-defined):
  - Large Brownie (2x3 inch) → 24 per batch
  - Medium Brownie (2x2 inch) → 36 per batch
  - Small Brownie (1.5x2 inch) → 48 per batch

Event: Bake Sale
Needs: 50 large brownies

Calculation: 50 ÷ 24 = 2.08 batches
Cost: $8/batch × 2.08 = $16.67 total
```

### 1.3 Why This Blocks Other Features

**F045 (Finished Goods/Bundles)**: Cannot create bundles without finished units
```
Cannot define: "Cookie Sampler Bundle contains 4 Large Cookies + 6 Small Cookies"
Blocked: Need to know what "Large Cookie" and "Small Cookie" are
```

**F046 (Shopping Lists)**: Cannot generate shopping lists without yield calculations
```
Cannot calculate: Ingredients needed for "100 Large Cookies"
Blocked: Don't know that 100 Large Cookies = 3.33 batches = X cups flour
```

**F047 (Assembly)**: Cannot track production without finished units
```
Cannot record: "Produced 120 Large Cookies on 1/8/2026"
Blocked: System doesn't know what "Large Cookie" is
```

---

## 2. Proposed Solution

### 2.1 Architecture Overview

**Two UI Entry Points:**

1. **Recipe Edit Form** (PRIMARY - for defining yield types)
   - Location: CATALOG mode → Recipes tab → [Edit Recipe]
   - Purpose: Add/edit/delete yield types for a recipe
   - Scope: Single recipe at a time

2. **Finished Units Tab** (SECONDARY - for browsing)
   - Location: CATALOG mode → Finished Units tab
   - Purpose: View all yield types across all recipes
   - Scope: Read-only catalog view

**Data Flow:**
```
Recipe Edit Form
  ↓ (user adds yield type)
FinishedUnit model (database)
  ↓ (appears automatically)
Finished Units Tab (catalog view)
  ↓ (user selects for event)
Event Planning → Production Plan
```

### 2.2 Recipe Edit Form Enhancements

**Add "Yield Types" section to Recipe Edit form:**

```
┌─ Edit Recipe: Cookie Dough ─────────────────────────────┐
│                                                          │
│  Recipe Name: [Cookie Dough________________]             │
│                                                          │
│  Ingredients:                                            │
│    • 2 cups flour                                        │
│    • 1 cup sugar                                         │
│    • ... (ingredient list)                               │
│                                                          │
│  Instructions:                                           │
│    1. Mix dry ingredients                                │
│    2. ... (instruction text)                             │
│                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  Yield Types (What can this recipe produce?)            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Name                    Per Batch   Actions        │ │
│  │ ─────────────────────   ─────────   ───────────    │ │
│  │ Large Cookie            30          [Edit] [Delete]│ │
│  │ Medium Cookie           48          [Edit] [Delete]│ │
│  │ Small Cookie            72          [Edit] [Delete]│ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  [+ Add Yield Type]                                      │
│                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  [Cancel]  [Save Recipe]                                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Add Yield Type Flow:**
```
User clicks [+ Add Yield Type]
  ↓
Inline row appears OR modal opens (implementation choice)
  ↓
User enters:
  - Name: "Large Cookie"
  - Items Per Batch: 30
  ↓
User clicks [Add] or [Save]
  ↓
Yield type added to list
  ↓
User clicks [Save Recipe] to persist
```

### 2.3 Finished Units Tab (Catalog View)

**Purpose**: Browse all yield types across all recipes (READ-ONLY)

```
┌─ CATALOG Mode → Finished Units Tab ─────────────────────┐
│                                                          │
│  CATALOG • 413 ingredients • 47 yield types              │
│  [Ingredients] [Products] [Recipes] [Finished Units]    │
│                                                          │
│  Search: [________]  Recipe: [All ▼]                     │
│                                                          │
│  ╔════════════════════════════════════════════════════╗  │
│  ║ Name              Recipe          Items/Batch     ║  │
│  ║ ─────────────     ─────────────   ──────────      ║  │
│  ║ Large Cookie      Cookie Dough    30              ║  │
│  ║ Medium Cookie     Cookie Dough    48              ║  │
│  ║ Small Cookie      Cookie Dough    72              ║  │
│  ║ 11-inch Cake      Chocolate Cake  1               ║  │
│  ║ 8-inch Cake       Chocolate Cake  2               ║  │
│  ║ 6-inch Cake       Chocolate Cake  4               ║  │
│  ║ Large Brownie     Brownie Batter  24              ║  │
│  ║ Medium Brownie    Brownie Batter  36              ║  │
│  ║ ...                                                ║  │
│  ║ (20+ rows visible)                                 ║  │
│  ╚════════════════════════════════════════════════════╝  │
│                                                          │
│  47 yield types defined                                  │
│                                                          │
│  ℹ️ To edit yield types, open the Recipe Edit form.     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Actions Available:**
- **Search**: Filter by yield type name
- **Filter by Recipe**: Show only yield types from specific recipe
- **Click row**: Opens parent Recipe Edit form (navigates to recipe management)

**NO Actions:**
- ❌ No [+ Add] button (add via Recipe Edit form)
- ❌ No [Edit] button (edit via Recipe Edit form)
- ❌ No [Delete] button (delete via Recipe Edit form)

### 2.4 UI Implementation Options

**Option A: Inline Row Entry (Recommended)**

Add yield type directly in the list:

```
Yield Types:

  Large Cookie        30    [Edit] [Delete]
  Medium Cookie       48    [Edit] [Delete]
  
  Name: [_____________]  Items/Batch: [___]  [Add]
```

**Pros:**
- Fast data entry (no modal pop-up)
- See all yield types while adding new one
- Fewer clicks

**Cons:**
- Takes more vertical space
- May feel cramped on small screens

**Option B: Modal Dialog**

Click [+ Add Yield Type] opens modal:

```
┌─ Add Yield Type ────────────────────────────┐
│                                             │
│  Yield Name: [Large Cookie_____________]    │
│    (e.g., "Large Cookie", "9-inch Cake")    │
│                                             │
│  Items Per Batch: [30]                      │
│    (How many does 1x recipe make?)          │
│                                             │
│  Preview: Cookie Dough → 30 Large Cookies   │
│           per batch                          │
│                                             │
│  [Cancel]  [Add]                            │
│                                             │
└─────────────────────────────────────────────┘
```

**Pros:**
- Cleaner Recipe Edit form (no always-visible entry row)
- More space for help text/preview
- Standard pattern (modals used elsewhere)

**Cons:**
- Extra click to open modal
- Context switch (modal covers recipe)

**Recommendation**: Start with **Option B (Modal)** since Recipe Edit form already has a lot going on. Can switch to inline if user testing shows modals are annoying.

---

## 3. Data Model

### 3.1 FinishedUnit Model (Already Exists)

**Current schema** (from `src/models/finished_unit.py`):

```python
class FinishedUnit(BaseModel):
    __tablename__ = "finished_units"
    
    # Primary key
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Core fields
    display_name = Column(String(200), nullable=False, index=True)
    items_per_batch = Column(Integer, nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"))
    
    # Additional fields (not used in F044, exist for future)
    description = Column(Text, nullable=True)
    yield_mode = Column(Enum(YieldMode), nullable=False)  # DISCRETE_COUNT, BATCH_PORTION
    item_unit = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    unit_cost = Column(Numeric(10, 4), default=0)
    inventory_count = Column(Integer, default=0)
    production_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="finished_units")
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
```

### 3.2 F044 Scope (Minimal Fields)

**For F044, we only use:**
- ✅ `display_name` - User-provided name ("Large Cookie", "9-inch Cake")
- ✅ `items_per_batch` - Yield quantity (30, 1, 24)
- ✅ `recipe_id` - Parent recipe

**Fields we ignore for now:**
- ⏳ `description` - Optional, can be added later
- ⏳ `yield_mode` - Set to DISCRETE_COUNT by default, ignored in UI
- ⏳ `item_unit` - Optional, for pluralization
- ⏳ `category` - Optional, for filtering
- ⏳ `unit_cost` - Calculated dynamically, not user-entered
- ⏳ `inventory_count` - Phase 3 (production tracking)
- ⏳ `production_notes` - Phase 3
- ⏳ `notes` - Optional

**Simplified F044 Data Model:**
```python
# What user sees/enters
{
    "display_name": "Large Cookie",
    "items_per_batch": 30,
    "recipe_id": 123  # Auto-set from parent recipe
}

# What gets saved (system fills defaults)
{
    "display_name": "Large Cookie",
    "items_per_batch": 30,
    "recipe_id": 123,
    "yield_mode": YieldMode.DISCRETE_COUNT,  # Default
    "unit_cost": 0.0,  # Calculated later
    "inventory_count": 0,  # Not used yet
    "slug": "large-cookie-cookie-dough",  # Auto-generated
    "uuid": "...",  # Auto-generated
}
```

### 3.3 Schema Changes Required

**NONE** - Model already exists with all needed fields.

**However**, need to ensure:
1. `Recipe` model has `back_populates="finished_units"` relationship
2. Constraints exist: `UniqueConstraint("recipe_id", "display_name")`
3. Check constraint: `items_per_batch > 0`

---

## 4. Service Layer

### 4.1 FinishedUnitService (New)

**File**: `src/services/finished_unit_service.py`

```python
class FinishedUnitService:
    """Service for managing finished units (yield types)."""
    
    def create_finished_unit(
        self,
        recipe_id: int,
        display_name: str,
        items_per_batch: int,
        session: Session
    ) -> FinishedUnit:
        """
        Create a new finished unit for a recipe.
        
        Args:
            recipe_id: Parent recipe ID
            display_name: Name of yield type (e.g., "Large Cookie")
            items_per_batch: Yield quantity per batch
            session: Database session
            
        Returns:
            Created FinishedUnit
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate recipe exists
        recipe = session.query(Recipe).get(recipe_id)
        if not recipe:
            raise ValidationError("Recipe not found")
        
        # Validate name not empty
        if not display_name or not display_name.strip():
            raise ValidationError("Yield name cannot be empty")
        
        # Validate items_per_batch positive
        if items_per_batch <= 0:
            raise ValidationError("Items per batch must be greater than zero")
        
        # Check uniqueness (recipe_id, display_name)
        existing = session.query(FinishedUnit).filter(
            FinishedUnit.recipe_id == recipe_id,
            FinishedUnit.display_name == display_name.strip()
        ).first()
        if existing:
            raise ValidationError(f"Yield type '{display_name}' already exists for this recipe")
        
        # Generate slug
        slug = self._generate_slug(display_name, recipe.name, session)
        
        # Create finished unit
        finished_unit = FinishedUnit(
            display_name=display_name.strip(),
            items_per_batch=items_per_batch,
            recipe_id=recipe_id,
            slug=slug,
            yield_mode=YieldMode.DISCRETE_COUNT,  # Default
            unit_cost=Decimal("0.0"),
            inventory_count=0
        )
        
        session.add(finished_unit)
        session.flush()
        
        return finished_unit
    
    def get_finished_units_by_recipe(
        self,
        recipe_id: int,
        session: Session
    ) -> List[FinishedUnit]:
        """Get all finished units for a recipe."""
        return session.query(FinishedUnit).filter(
            FinishedUnit.recipe_id == recipe_id
        ).order_by(FinishedUnit.display_name).all()
    
    def get_all_finished_units(
        self,
        session: Session,
        recipe_id: Optional[int] = None,
        search_query: Optional[str] = None
    ) -> List[FinishedUnit]:
        """
        Get all finished units with optional filters.
        
        Args:
            session: Database session
            recipe_id: Filter by recipe (None = all recipes)
            search_query: Filter by name (fuzzy match)
            
        Returns:
            List of FinishedUnit objects
        """
        query = session.query(FinishedUnit).join(Recipe)
        
        if recipe_id:
            query = query.filter(FinishedUnit.recipe_id == recipe_id)
        
        if search_query:
            query = query.filter(
                FinishedUnit.display_name.ilike(f"%{search_query}%")
            )
        
        return query.order_by(Recipe.name, FinishedUnit.display_name).all()
    
    def update_finished_unit(
        self,
        finished_unit_id: int,
        display_name: Optional[str] = None,
        items_per_batch: Optional[int] = None,
        session: Session
    ) -> FinishedUnit:
        """Update a finished unit."""
        finished_unit = session.query(FinishedUnit).get(finished_unit_id)
        if not finished_unit:
            raise ValidationError("Finished unit not found")
        
        if display_name is not None:
            if not display_name.strip():
                raise ValidationError("Yield name cannot be empty")
            
            # Check uniqueness if name changed
            if display_name.strip() != finished_unit.display_name:
                existing = session.query(FinishedUnit).filter(
                    FinishedUnit.recipe_id == finished_unit.recipe_id,
                    FinishedUnit.display_name == display_name.strip(),
                    FinishedUnit.id != finished_unit_id
                ).first()
                if existing:
                    raise ValidationError(f"Yield type '{display_name}' already exists")
            
            finished_unit.display_name = display_name.strip()
        
        if items_per_batch is not None:
            if items_per_batch <= 0:
                raise ValidationError("Items per batch must be greater than zero")
            finished_unit.items_per_batch = items_per_batch
        
        finished_unit.updated_at = utc_now()
        session.flush()
        
        return finished_unit
    
    def delete_finished_unit(
        self,
        finished_unit_id: int,
        session: Session
    ) -> None:
        """
        Delete a finished unit.
        
        Raises:
            ValidationError: If finished unit is used in events/bundles
        """
        finished_unit = session.query(FinishedUnit).get(finished_unit_id)
        if not finished_unit:
            raise ValidationError("Finished unit not found")
        
        # TODO: Check if used in events/bundles (F045+)
        # For F044, just delete (no dependencies yet)
        
        session.delete(finished_unit)
        session.flush()
    
    def _generate_slug(
        self,
        display_name: str,
        recipe_name: str,
        session: Session
    ) -> str:
        """Generate unique slug for finished unit."""
        import re
        
        # Slugify: "Large Cookie" + "Cookie Dough" → "large-cookie-cookie-dough"
        base = f"{display_name} {recipe_name}".lower()
        base = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
        
        # Ensure uniqueness
        slug = base
        counter = 1
        while session.query(FinishedUnit).filter(
            FinishedUnit.slug == slug
        ).first():
            slug = f"{base}-{counter}"
            counter += 1
        
        return slug
```

---

## 5. UI Implementation

### 5.1 Recipe Edit Form Changes

**File**: `src/ui/dialogs/recipe_edit_dialog.py` (or similar)

**Add "Yield Types" section:**

```python
class RecipeEditDialog(ctk.CTkToplevel):
    """Dialog for editing recipes."""
    
    def __init__(self, parent, recipe_id=None, on_save_callback=None):
        super().__init__(parent)
        
        self.recipe_id = recipe_id
        self.on_save_callback = on_save_callback
        self.finished_units = []  # List of yield types
        
        self._create_ui()
        if recipe_id:
            self._load_recipe()
    
    def _create_ui(self):
        """Create dialog UI."""
        # ... existing recipe fields (name, ingredients, instructions)
        
        # Add yield types section
        self._create_yield_types_section()
        
        # Save/Cancel buttons
        self._create_buttons()
    
    def _create_yield_types_section(self):
        """Create yield types management section."""
        # Section header
        separator = ctk.CTkFrame(self, height=2, fg_color="gray")
        separator.pack(fill="x", padx=10, pady=10)
        
        header = ctk.CTkLabel(
            self,
            text="Yield Types (What can this recipe produce?)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(padx=10, pady=(10, 5), anchor="w")
        
        # Yield types list
        self.yield_types_frame = ctk.CTkFrame(self)
        self.yield_types_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Header row
        header_frame = ctk.CTkFrame(self.yield_types_frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header_frame, text="Name", width=200).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Per Batch", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Actions", width=120).pack(side="left", padx=5)
        
        # Scrollable list of yield types
        self.yield_types_list = ctk.CTkScrollableFrame(self.yield_types_frame, height=150)
        self.yield_types_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add yield type button
        add_button = ctk.CTkButton(
            self.yield_types_frame,
            text="+ Add Yield Type",
            command=self._on_add_yield_type
        )
        add_button.pack(pady=5)
    
    def _load_recipe(self):
        """Load existing recipe and its yield types."""
        from src.services.finished_unit_service import FinishedUnitService
        from src.services.database import session_scope
        
        with session_scope() as session:
            # Load recipe
            recipe = session.query(Recipe).get(self.recipe_id)
            # ... populate recipe fields
            
            # Load yield types
            fu_service = FinishedUnitService()
            self.finished_units = fu_service.get_finished_units_by_recipe(
                self.recipe_id, session
            )
            
            # Display yield types
            self._refresh_yield_types_list()
    
    def _refresh_yield_types_list(self):
        """Refresh the yield types list display."""
        # Clear existing
        for widget in self.yield_types_list.winfo_children():
            widget.destroy()
        
        # Add rows
        for fu in self.finished_units:
            row = ctk.CTkFrame(self.yield_types_list)
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=fu.display_name, width=200).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(fu.items_per_batch), width=80).pack(side="left", padx=5)
            
            edit_btn = ctk.CTkButton(
                row, text="Edit", width=60,
                command=lambda f=fu: self._on_edit_yield_type(f)
            )
            edit_btn.pack(side="left", padx=2)
            
            delete_btn = ctk.CTkButton(
                row, text="Delete", width=60,
                command=lambda f=fu: self._on_delete_yield_type(f)
            )
            delete_btn.pack(side="left", padx=2)
    
    def _on_add_yield_type(self):
        """Open dialog to add new yield type."""
        dialog = AddYieldTypeDialog(
            self,
            on_save_callback=self._on_yield_type_added
        )
        dialog.focus()
    
    def _on_yield_type_added(self, display_name, items_per_batch):
        """Handle new yield type added."""
        # Create temporary FinishedUnit object (not saved to DB yet)
        fu = type('FinishedUnit', (), {
            'id': None,  # Temp, will get ID on save
            'display_name': display_name,
            'items_per_batch': items_per_batch,
            'recipe_id': self.recipe_id
        })()
        
        self.finished_units.append(fu)
        self._refresh_yield_types_list()
    
    def _on_edit_yield_type(self, finished_unit):
        """Edit existing yield type."""
        dialog = EditYieldTypeDialog(
            self,
            finished_unit=finished_unit,
            on_save_callback=self._on_yield_type_updated
        )
        dialog.focus()
    
    def _on_yield_type_updated(self, finished_unit, display_name, items_per_batch):
        """Handle yield type updated."""
        finished_unit.display_name = display_name
        finished_unit.items_per_batch = items_per_batch
        self._refresh_yield_types_list()
    
    def _on_delete_yield_type(self, finished_unit):
        """Delete yield type."""
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "Delete Yield Type",
            f"Delete '{finished_unit.display_name}'?\n\nThis action cannot be undone."
        )
        
        if result:
            self.finished_units.remove(finished_unit)
            self._refresh_yield_types_list()
    
    def _save(self):
        """Save recipe and yield types."""
        from src.services.database import session_scope
        from src.services.finished_unit_service import FinishedUnitService
        
        with session_scope() as session:
            # Save recipe
            # ... save recipe fields
            
            # Save yield types
            fu_service = FinishedUnitService()
            
            for fu in self.finished_units:
                if fu.id is None:
                    # New yield type
                    fu_service.create_finished_unit(
                        recipe_id=self.recipe_id,
                        display_name=fu.display_name,
                        items_per_batch=fu.items_per_batch,
                        session=session
                    )
                else:
                    # Update existing
                    fu_service.update_finished_unit(
                        finished_unit_id=fu.id,
                        display_name=fu.display_name,
                        items_per_batch=fu.items_per_batch,
                        session=session
                    )
            
            session.commit()
        
        if self.on_save_callback:
            self.on_save_callback()
        
        self.destroy()
```

### 5.2 Add/Edit Yield Type Dialogs

**File**: `src/ui/dialogs/yield_type_dialog.py`

```python
class AddYieldTypeDialog(ctk.CTkToplevel):
    """Dialog for adding new yield type."""
    
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        
        self.on_save_callback = on_save_callback
        
        self.title("Add Yield Type")
        self.geometry("400x250")
        
        self._create_ui()
    
    def _create_ui(self):
        """Create dialog UI."""
        # Name
        ctk.CTkLabel(self, text="Yield Name:").pack(padx=20, pady=(20, 5), anchor="w")
        ctk.CTkLabel(
            self, 
            text="(e.g., \"Large Cookie\", \"9-inch Cake\")",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(padx=20, pady=(0, 5), anchor="w")
        
        self.name_entry = ctk.CTkEntry(self, width=360)
        self.name_entry.pack(padx=20, pady=5)
        
        # Items per batch
        ctk.CTkLabel(self, text="Items Per Batch:").pack(padx=20, pady=(10, 5), anchor="w")
        ctk.CTkLabel(
            self,
            text="(How many does 1x recipe make?)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(padx=20, pady=(0, 5), anchor="w")
        
        self.items_entry = ctk.CTkEntry(self, width=100)
        self.items_entry.pack(padx=20, pady=5, anchor="w")
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Add",
            command=self._save
        ).pack(side="left", padx=5)
    
    def _save(self):
        """Validate and save."""
        from tkinter import messagebox
        
        display_name = self.name_entry.get().strip()
        items_str = self.items_entry.get().strip()
        
        # Validate
        if not display_name:
            messagebox.showerror("Validation Error", "Yield name cannot be empty")
            return
        
        try:
            items_per_batch = int(items_str)
            if items_per_batch <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Items per batch must be a positive number")
            return
        
        # Callback
        if self.on_save_callback:
            self.on_save_callback(display_name, items_per_batch)
        
        self.destroy()


class EditYieldTypeDialog(AddYieldTypeDialog):
    """Dialog for editing existing yield type."""
    
    def __init__(self, parent, finished_unit, on_save_callback):
        self.finished_unit = finished_unit
        super().__init__(parent, on_save_callback)
        
        self.title("Edit Yield Type")
        
        # Pre-fill fields
        self.name_entry.insert(0, finished_unit.display_name)
        self.items_entry.insert(0, str(finished_unit.items_per_batch))
    
    def _save(self):
        """Validate and save."""
        from tkinter import messagebox
        
        display_name = self.name_entry.get().strip()
        items_str = self.items_entry.get().strip()
        
        # Validate
        if not display_name:
            messagebox.showerror("Validation Error", "Yield name cannot be empty")
            return
        
        try:
            items_per_batch = int(items_str)
            if items_per_batch <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Items per batch must be a positive number")
            return
        
        # Callback with finished_unit reference
        if self.on_save_callback:
            self.on_save_callback(self.finished_unit, display_name, items_per_batch)
        
        self.destroy()
```

### 5.3 Finished Units Tab

**File**: `src/ui/tabs/finished_units_tab.py` (NEW)

```python
class FinishedUnitsTab(ctk.CTkFrame):
    """Read-only catalog view of all finished units."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.finished_units = []
        self._data_loaded = False
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # List expands
        
        self._create_header()
        self._create_controls()
        self._create_list()
        
        # Grid to parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _create_header(self):
        """Create header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        
        title = ctk.CTkLabel(
            header_frame,
            text="Finished Units",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=10, pady=10)
    
    def _create_controls(self):
        """Create search and filter controls."""
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Search
        self.search_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Search by name...",
            width=250
        )
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filters())
        
        # Recipe filter
        ctk.CTkLabel(controls_frame, text="Recipe:").pack(side="left", padx=5)
        self.recipe_filter = ctk.CTkComboBox(
            controls_frame,
            values=["All"],
            command=lambda e: self._apply_filters()
        )
        self.recipe_filter.pack(side="left", padx=5)
        
        # Info label
        self.info_label = ctk.CTkLabel(
            controls_frame,
            text="ℹ️ To edit yield types, open the Recipe Edit form.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.info_label.pack(side="right", padx=10)
    
    def _create_list(self):
        """Create finished units list."""
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # Treeview with columns
        columns = ("name", "recipe", "items_per_batch")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        self.tree.heading("name", text="Name")
        self.tree.heading("recipe", text="Recipe")
        self.tree.heading("items_per_batch", text="Items/Batch")
        
        self.tree.column("name", width=200)
        self.tree.column("recipe", width=200)
        self.tree.column("items_per_batch", width=100)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Double-click to open recipe
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        
        # Count label
        self.count_label = ctk.CTkLabel(self, text="")
        self.count_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
    
    def load_data(self):
        """Load finished units from database."""
        from src.services.finished_unit_service import FinishedUnitService
        from src.services.database import session_scope
        
        with session_scope() as session:
            fu_service = FinishedUnitService()
            self.finished_units = fu_service.get_all_finished_units(session)
            
            # Get unique recipe names for filter
            recipes = set(fu.recipe.name for fu in self.finished_units)
            self.recipe_filter.configure(values=["All"] + sorted(recipes))
        
        self._data_loaded = True
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply search and filter."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get filters
        search_query = self.search_entry.get().lower()
        recipe_filter = self.recipe_filter.get()
        
        # Filter
        filtered = self.finished_units
        
        if search_query:
            filtered = [fu for fu in filtered if search_query in fu.display_name.lower()]
        
        if recipe_filter != "All":
            filtered = [fu for fu in filtered if fu.recipe.name == recipe_filter]
        
        # Populate tree
        for fu in filtered:
            self.tree.insert("", "end", values=(
                fu.display_name,
                fu.recipe.name,
                fu.items_per_batch
            ), tags=(fu.id,))
        
        # Update count
        self.count_label.configure(text=f"{len(filtered)} yield types")
    
    def _on_double_click(self, event):
        """Open recipe edit form for selected finished unit."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get finished_unit_id from tags
        item = selection[0]
        finished_unit_id = int(self.tree.item(item, "tags")[0])
        
        # Find finished unit
        finished_unit = next(
            (fu for fu in self.finished_units if fu.id == finished_unit_id),
            None
        )
        
        if finished_unit:
            # TODO: Open recipe edit dialog
            # For now, show message
            from tkinter import messagebox
            messagebox.showinfo(
                "Edit Recipe",
                f"Opening recipe '{finished_unit.recipe.name}' for editing..."
            )
```

---

## 6. Functional Requirements

### 6.1 Recipe Edit Form Requirements

**REQ-F044-001:** Recipe Edit form SHALL include "Yield Types" section
**REQ-F044-002:** Yield Types section SHALL display list of yield types for the recipe
**REQ-F044-003:** Each yield type row SHALL show: Name, Items Per Batch, [Edit], [Delete]
**REQ-F044-004:** [+ Add Yield Type] button SHALL open dialog to create new yield type
**REQ-F044-005:** [Edit] button SHALL open dialog to modify yield type
**REQ-F044-006:** [Delete] button SHALL remove yield type with confirmation
**REQ-F044-007:** Saving recipe SHALL persist all yield type changes

### 6.2 Yield Type Dialog Requirements

**REQ-F044-008:** Add Yield Type dialog SHALL require two fields: Name, Items Per Batch
**REQ-F044-009:** Name field SHALL accept freeform text (max 200 characters)
**REQ-F044-010:** Items Per Batch SHALL accept positive integers only
**REQ-F044-011:** Dialog SHALL validate inputs before saving
**REQ-F044-012:** Edit dialog SHALL pre-fill with existing values

### 6.3 Finished Units Tab Requirements

**REQ-F044-013:** Finished Units tab SHALL exist in CATALOG mode
**REQ-F044-014:** Tab SHALL display all yield types across all recipes
**REQ-F044-015:** List SHALL show columns: Name, Recipe, Items/Batch
**REQ-F044-016:** Search bar SHALL filter by yield type name
**REQ-F044-017:** Recipe dropdown SHALL filter by parent recipe
**REQ-F044-018:** Double-clicking row SHALL open parent Recipe Edit form
**REQ-F044-019:** Tab SHALL be read-only (no Add/Edit/Delete buttons)
**REQ-F044-020:** Tab SHALL display info message: "To edit yield types, open Recipe Edit form"

### 6.4 Service Layer Requirements

**REQ-F044-021:** FinishedUnitService SHALL support CRUD operations
**REQ-F044-022:** create_finished_unit SHALL validate name not empty
**REQ-F044-023:** create_finished_unit SHALL validate items_per_batch > 0
**REQ-F044-024:** create_finished_unit SHALL enforce uniqueness (recipe_id, display_name)
**REQ-F044-025:** update_finished_unit SHALL allow changing name and items_per_batch
**REQ-F044-026:** delete_finished_unit SHALL remove yield type (no dependency checks in F044)
**REQ-F044-027:** get_finished_units_by_recipe SHALL return ordered list
**REQ-F044-028:** get_all_finished_units SHALL support recipe and search filters

---

## 7. Non-Functional Requirements

### 7.1 Usability

**REQ-F044-NFR-001:** Adding yield type SHALL require max 3 clicks
**REQ-F044-NFR-002:** Recipe Edit form SHALL remain responsive with 10+ yield types
**REQ-F044-NFR-003:** Finished Units tab SHALL load <500ms for 100 yield types
**REQ-F044-NFR-004:** Validation errors SHALL be specific and actionable

### 7.2 Data Integrity

**REQ-F044-NFR-005:** Yield types SHALL NOT be orphaned (recipe deletion cascades or blocks)
**REQ-F044-NFR-006:** Duplicate names within recipe SHALL be prevented
**REQ-F044-NFR-007:** Items per batch SHALL be positive integer

### 7.3 Consistency

**REQ-F044-NFR-008:** UI patterns SHALL match existing tabs (Ingredients, Products, Recipes)
**REQ-F044-NFR-009:** Dialogs SHALL use standard CustomTkinter components
**REQ-F044-NFR-010:** Error messages SHALL follow application style

---

## 8. Testing Strategy

### 8.1 Unit Tests

**FinishedUnitService:**
```python
def test_create_finished_unit_success():
    """Test creating valid finished unit."""
    
def test_create_finished_unit_empty_name():
    """Test validation: name cannot be empty."""
    
def test_create_finished_unit_zero_items():
    """Test validation: items per batch must be positive."""
    
def test_create_finished_unit_duplicate_name():
    """Test uniqueness: (recipe_id, name) must be unique."""
    
def test_update_finished_unit():
    """Test updating name and items per batch."""
    
def test_delete_finished_unit():
    """Test deletion."""
    
def test_get_finished_units_by_recipe():
    """Test querying by recipe."""
    
def test_get_all_finished_units_with_filters():
    """Test search and recipe filtering."""
```

### 8.2 Integration Tests

**Recipe Edit Form:**
```python
def test_recipe_edit_shows_yield_types():
    """Test yield types section displays in recipe edit."""
    
def test_add_yield_type_flow():
    """Test adding yield type through UI."""
    
def test_edit_yield_type_flow():
    """Test editing yield type through UI."""
    
def test_delete_yield_type_flow():
    """Test deleting yield type with confirmation."""
    
def test_save_recipe_persists_yield_types():
    """Test yield types saved when recipe saved."""
```

**Finished Units Tab:**
```python
def test_finished_units_tab_loads_data():
    """Test tab loads all yield types."""
    
def test_search_filters_by_name():
    """Test search bar filters results."""
    
def test_recipe_filter_works():
    """Test recipe dropdown filters results."""
    
def test_double_click_opens_recipe():
    """Test double-clicking opens recipe edit."""
```

### 8.3 User Acceptance Tests

**UAT-001: Add Yield Types to Recipe**
```
Given: User has recipe "Cookie Dough"
When: User opens Recipe Edit
And: Adds yield type "Large Cookie" with 30 per batch
And: Adds yield type "Small Cookie" with 72 per batch
And: Saves recipe
Then: Yield types appear in Finished Units tab
And: Can be selected in event planning
```

**UAT-002: Browse Finished Units**
```
Given: System has 47 yield types across 15 recipes
When: User opens Finished Units tab
Then: All 47 yield types displayed
And: Can search by name
And: Can filter by recipe
And: Double-click opens Recipe Edit form
```

**UAT-003: Edit Existing Yield Type**
```
Given: Recipe has yield type "Large Cookie" (30 per batch)
When: User opens Recipe Edit
And: Clicks [Edit] on "Large Cookie"
And: Changes to "Extra Large Cookie" (24 per batch)
And: Saves
Then: Yield type updated
And: Appears as "Extra Large Cookie" in Finished Units tab
```

**UAT-004: Delete Yield Type**
```
Given: Recipe has yield type "Small Cookie"
When: User opens Recipe Edit
And: Clicks [Delete] on "Small Cookie"
And: Confirms deletion
And: Saves recipe
Then: Yield type removed
And: No longer appears in Finished Units tab
```

---

## 9. Implementation Phases

### Phase 1: Service Layer (High Priority)
**Effort:** 4-5 hours

**Scope:**
- Create `FinishedUnitService` class
- Implement CRUD methods
- Validation logic
- Unit tests (8-10 tests)

**Deliverables:**
- ✓ Service methods functional
- ✓ Tests passing
- ✓ Can create/read/update/delete via Python

### Phase 2: Recipe Edit Form (High Priority)
**Effort:** 6-8 hours

**Scope:**
- Add "Yield Types" section to Recipe Edit form
- Yield types list display
- Add/Edit/Delete dialogs
- Integration with service layer

**Deliverables:**
- ✓ Can manage yield types in Recipe Edit
- ✓ Changes persist to database
- ✓ Validation working

### Phase 3: Finished Units Tab (Medium Priority)
**Effort:** 4-5 hours

**Scope:**
- Create FinishedUnitsTab component
- List view with search/filter
- Double-click navigation to recipe
- Read-only enforcement

**Deliverables:**
- ✓ Tab visible in CATALOG mode
- ✓ Can browse all yield types
- ✓ Filters working

### Phase 4: Integration Testing (Medium Priority)
**Effort:** 2-3 hours

**Scope:**
- End-to-end workflow tests
- Recipe Edit ↔ Finished Units tab integration
- Edge cases (empty recipes, many yield types)

**Deliverables:**
- ✓ Full workflow tested
- ✓ Edge cases handled

**Total Effort Estimate:** 16-21 hours (2-3 working days)

---

## 10. Success Criteria

**Must Have:**
- [ ] Recipe Edit form has "Yield Types" section
- [ ] Can add yield types: name + items per batch
- [ ] Can edit existing yield types
- [ ] Can delete yield types with confirmation
- [ ] Finished Units tab shows all yield types
- [ ] Search/filter working in Finished Units tab
- [ ] Double-click navigates to Recipe Edit
- [ ] Validation prevents empty names, zero/negative quantities, duplicates
- [ ] Data persists correctly

**Should Have:**
- [ ] Yield types display ordered by name
- [ ] Edit dialog pre-fills with existing values
- [ ] Delete shows confirmation dialog
- [ ] Info message explains read-only nature of tab

**Nice to Have:**
- [ ] Keyboard shortcuts (Enter to save, Esc to cancel)
- [ ] Tab order logical in dialogs
- [ ] Preview of yield calculation in dialog

---

## 11. Relationship to Other Features

**F037 (Recipe Redesign ✅)**: Provides Recipe model with relationship support
**F042 (UI Polish ✅)**: Establishes tab layout patterns
**F045 (Finished Goods/Bundles)**: Depends on FinishedUnits existing
**F046 (Shopping Lists)**: Depends on yield calculations
**F047 (Assembly)**: Depends on tracking FinishedUnit production

---

## 12. Constitutional Compliance

**Principle I (User-Centric Design):**
- ✓ Embedded in recipe workflow (not separate interface)
- ✓ Minimal fields (just name + count)
- ✓ Read-only catalog for browsing

**Principle V (Layered Architecture):**
- ✓ Service layer handles business logic
- ✓ UI calls service methods
- ✓ Data model separate from UI

**Principle VII (Pragmatic Aspiration):**
- ✓ Desktop-first patterns (CustomTkinter)
- ✓ Web-ready service layer
- ✓ Minimal viable implementation (can extend later)

---

## 13. Related Documents

- **Requirements:** `docs/requirements/req_finished_goods.md` Section 5.1
- **User Testing:** `docs/user_testing/usr_testing_2026_01_07.md` (identified need)
- **Dependencies:** `docs/func-spec/F037_recipe_redesign.md` (Recipe model)
- **Feature Roadmap:** `docs/feature_roadmap.md` (F043-F047 sequence)
- **Constitution:** `.kittify/memory/constitution.md` (Architecture principles)

---

**END OF SPECIFICATION**
