### 5.1 FinishedUnit Management

**Core Concept:** FinishedUnits represent **yield types** of recipes. A single recipe (at 1x scale) can produce different finished units depending on how the baker divides/portions the batch. This is a **one-to-many relationship**: Recipe → multiple FinishedUnits.

**Design Philosophy:** Keep it simple. A FinishedUnit is just a **name** and a **count** linked to a recipe. The baker describes the yield however makes sense to them.

**UI Location:** FinishedUnits are **managed within the Recipe Edit form**, not via separate interface. Users add/edit/delete yield types while editing recipes.

---

**Examples:**

| Recipe | Yield Type 1 | Yield Type 2 | Yield Type 3 | Yield Type 4 |
|--------|--------------|--------------|--------------|--------------|
| **Cookie Dough (1x)** | Large Cookie → 30 per batch | Medium Cookie → 48 per batch | Small Cookie → 72 per batch | - |
| **Chocolate Cake (1x)** | 11-inch Cake → 1 per batch | 8-inch Cake → 2 per batch | 6-inch Cake → 4 per batch | 4-inch Cake → 6 per batch |
| **Brownie Batter (1x)** | Large Brownie (2x3") → 24 per batch | Medium Brownie (2x2") → 36 per batch | Small Brownie (1x2") → 48 per batch | - |

**Key Principle:** Each FinishedUnit is a **yield configuration** describing how one recipe batch (1x) can be portioned. Users select which yield type when planning events.

---

## Requirements

**REQ-FG-001:** System SHALL support creation of FinishedUnits **within the Recipe Edit form** with minimal fields:
- **display_name**: How the baker describes this yield (e.g., "Large Cookie", "9-inch Cake", "Medium Brownie")
- **items_per_batch**: How many items one recipe batch (1x scale) produces
- **recipe_id**: Automatically set from parent recipe (not user-entered)

**REQ-FG-001a:** FinishedUnit management SHALL be **embedded in Recipe Edit form**, not separate interface
- Add yield type: [+ Add Yield Type] button in Recipe Edit form
- Edit yield type: Inline editing within Recipe Edit form
- Delete yield type: Delete button/action within Recipe Edit form
- No standalone "FinishedUnits Edit" dialog or form

**REQ-FG-001b:** Recipe Edit form SHALL display all yield types for the recipe
- List of yield types shown in Recipe Edit form
- Format: "Large Cookie → 30 per batch"
- Actions available: Edit, Delete per yield type

**REQ-FG-002:** Each FinishedUnit SHALL link to exactly ONE Recipe (the recipe that produces it)

**REQ-FG-003:** A Recipe MAY have multiple FinishedUnits (different yield types)
- **Example 1:** "Cookie Dough" recipe can produce:
  - FinishedUnit A: "Large Cookie" → 30 per batch
  - FinishedUnit B: "Medium Cookie" → 48 per batch
  - FinishedUnit C: "Small Cookie" → 72 per batch
- **Example 2:** "Chocolate Cake" recipe can produce:
  - FinishedUnit A: "11-inch Cake" → 1 per batch
  - FinishedUnit B: "8-inch Cake" → 2 per batch
  - FinishedUnit C: "6-inch Cake" → 4 per batch
  - FinishedUnit D: "4-inch Cake" → 6 per batch

**REQ-FG-004:** System SHALL enforce one-to-one relationship: FinishedUnit → Recipe
- Each FinishedUnit belongs to exactly one Recipe
- A Recipe can have zero or many FinishedUnits
- Deleting a Recipe SHALL require handling dependent FinishedUnits (block deletion or cascade)

**REQ-FG-005:** System SHALL NOT parse or validate display_name format
- User is responsible for providing descriptive names
- "Large Cookie" is valid
- "3-inch Cookie" is valid
- "Cookie (large scoop)" is valid
- System stores and displays name as-is, no interpretation

**REQ-FG-006:** System SHALL validate items_per_batch is positive integer
- Must be greater than zero
- Used for batch calculations (e.g., 100 cookies ÷ 30 per batch = 3.33 batches)

**REQ-FG-007:** FinishedUnits SHALL be selectable for event requirements (BULK_COUNT mode)
- User specifies: "I need 120 Medium Cookies" (selects FinishedUnit, enters quantity)
- System calculates: 120 cookies ÷ 48 per batch = 2.5 batches of Cookie Dough recipe

**REQ-FG-008:** FinishedUnits SHALL be usable as Bundle components
- Bundles contain specific yield types, not abstract recipes
- Example: "Cookie Sampler Bundle" contains:
  - 4 × Large Cookie
  - 6 × Small Cookie

**REQ-FG-009:** System SHALL validate FinishedUnit has valid recipe linkage before use in planning
- Cannot add FinishedUnit to event if recipe doesn't exist
- Cannot delete recipe if FinishedUnits depend on it (without handling cascade)

**REQ-FG-010:** System SHALL calculate cost per FinishedUnit item from recipe FIFO cost
- Formula: `unit_cost = recipe_cost ÷ items_per_batch`
- Example: Recipe costs $12, produces 30 cookies → $0.40 per cookie
- Cost calculated dynamically, not stored (changes as ingredient prices change)

**REQ-FG-011:** System SHALL support querying "What can I make from this recipe?"
- Given recipe, return all FinishedUnits (yield types) available
- Example: "Cookie Dough" → [Large Cookie (30), Medium Cookie (48), Small Cookie (72)]

**REQ-FG-012:** System SHALL prevent exact duplicate FinishedUnit definitions
- Cannot create two FinishedUnits with identical display_name for same recipe
- Enforce uniqueness: (recipe_id, display_name) combination
- Different names allowed: "Large Cookie" and "Big Cookie" are distinct (user's choice)

---

## Naming Conventions (Recommended, Not Enforced)

**Suggested Patterns:**

For consistency, users may adopt naming conventions (system does not enforce):

**Cookies:**
- "Large Cookie" (30/batch)
- "Medium Cookie" (48/batch)
- "Small Cookie" (72/batch)

**Cakes:**
- "11-inch Cake" (1/batch)
- "9-inch Cake" (1/batch)
- "8-inch Cake" (2/batch)
- "6-inch Cake" (4/batch)

**Brownies:**
- "Large Brownie" (24/batch)
- "Medium Brownie" (36/batch)
- "Brownie Bar 2x3" (24/batch)

**Multi-Component Items:**
- "Cookie Sandwich" (15/batch)
- "Decorated Cookie" (24/batch)
- "Filled Cupcake" (12/batch)

**Category Prefixes (Optional):**
- "Cookie - Large" (30/batch)
- "Cookie - Medium" (48/batch)
- "Cake - 9 inch" (1/batch)

This helps with sorting/filtering but is user's choice.

---

## Data Model

```python
class FinishedUnit(BaseModel):
    __tablename__ = "finished_units"
    
    # Primary key
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Core fields (minimal design)
    display_name = Column(String(200), nullable=False, index=True)
    items_per_batch = Column(Integer, nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="finished_units")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("recipe_id", "display_name", name="uq_finished_unit_recipe_name"),
        CheckConstraint("items_per_batch > 0", name="ck_finished_unit_items_positive"),
        Index("idx_finished_unit_recipe", "recipe_id"),
        Index("idx_finished_unit_name", "display_name"),
    )
```

**That's it. Three core fields.**

---

## Rationale for Minimal Design

1. **Reflects Real Baker Workflow:**
   - Bakers say: "I make 30 large cookies per batch"
   - That's exactly two pieces of information: name + count
   - Don't over-structure what's fundamentally just a label

2. **Accurate Batch Calculations:**
   - Only `items_per_batch` matters for math
   - 100 large cookies (30/batch) = 3.33 batches
   - The word "large" is just human context

3. **Maximum Flexibility:**
   - Baker decides descriptiveness: "Large" vs "3-inch" vs "Large (3-inch, #40 scoop)"
   - System doesn't impose measurement formats
   - No dropdowns, no categories, no parsing

4. **Easy to Extend Later:**
   - Can add `item_type` field if filtering becomes important
   - Can add `yield_description` if separation needed
   - Not losing anything by starting minimal

5. **Fast Data Entry:**
   - Two fields: name and count
   - Can't get simpler

6. **YAGNI Principle:**
   - Don't add fields until proven necessary
   - User testing will reveal if categorization needed

---

## UI Design

### Recipe Edit Form (with embedded FinishedUnit management)

```
┌─ Edit Recipe: Cookie Dough ─────────────────────────────┐
│                                                          │
│  Recipe Name: [Cookie Dough________________]             │
│                                                          │
│  Ingredients:                                            │
│    [ingredient list...]                                  │
│                                                          │
│  Instructions:                                           │
│    [instruction text...]                                 │
│                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  Yield Types (What can this recipe produce?)            │
│                                                          │
│    • Large Cookie       → 30 per batch   [Edit] [Delete]│
│    • Medium Cookie      → 48 per batch   [Edit] [Delete]│
│    • Small Cookie       → 72 per batch   [Edit] [Delete]│
│                                                          │
│    [+ Add Yield Type]                                    │
│                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  [Cancel]  [Save Recipe]                                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Add Yield Type (inline in Recipe Edit form)

**Option A: Inline Row Entry (Simplest)**
```
Yield Types:

  • Large Cookie       → 30 per batch   [Edit] [Delete]
  • Medium Cookie      → 48 per batch   [Edit] [Delete]
  
  [New] Name: [____________]  Items/Batch: [__]  [Add]
  
  [+ Add Another Yield Type]
```

**Option B: Modal Dialog (if inline too cramped)**
```
[+ Add Yield Type] → Opens modal:

┌─ Add Yield Type ────────────────────────────┐
│                                             │
│  Yield Name: [Large Cookie_____________]    │
│    (e.g., "Large Cookie", "9-inch Cake")    │
│                                             │
│  Items Per Batch: [30]                      │
│                                             │
│  [Cancel]  [Add]                            │
│                                             │
└─────────────────────────────────────────────┘
```

**Recommendation: Start with Option A (inline), switch to Option B (modal) if user testing shows it's too cramped.**

### FinishedUnits Tab (Read-Only Catalog View)

**Note:** This tab is for **viewing/browsing** all yield types across recipes. **Editing happens in Recipe Edit form only.**

```
┌─ CATALOG Mode → Finished Units Tab ─────────────────────┐
│                                                          │
│  Search: [________]  Recipe: [All ▼]                     │
│                                                          │
│  ╔════════════════════════════════════════════════════╗  │
│  ║ Name              Recipe          Items/Batch     ║  │
│  ║ ─────────────     ─────────────   ──────────      ║  │
│  ║ Large Cookie      Cookie Dough    30              ║  │
│  ║ Medium Cookie     Cookie Dough    48              ║  │
│  ║ Small Cookie      Cookie Dough    72              ║  │
│  ║ 9-inch Cake       Chocolate Cake  1               ║  │
│  ║ 8-inch Cake       Chocolate Cake  2               ║  │
│  ║ Large Brownie     Brownie Batter  24              ║  │
│  ║ ...                                                ║  │
│  ║ (20+ rows visible)                                 ║  │
│  ╚════════════════════════════════════════════════════╝  │
│                                                          │
│  47 yield types defined                                  │
│                                                          │
│  To edit yield types, open the Recipe Edit form.        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Actions in FinishedUnits Tab:**
- **View Only**: Browse all yield types
- **Search/Filter**: Find specific yield types
- **Navigate to Recipe**: Click yield type → opens parent Recipe Edit form

**NO "Add/Edit/Delete" buttons in FinishedUnits tab** - those actions happen in Recipe Edit form.

### Event Planning (Using FinishedUnits)

```
┌─ Event: Birthday Party ──────────────────────────────────┐
│                                                          │
│  FinishedUnits Needed:                                   │
│                                                          │
│    Recipe: Cookie Dough                                  │
│      • Large Cookie          100 units    3.33 batches   │
│                                                          │
│    Recipe: Brownie Batter                                │
│      • Large Brownie          50 units    2.08 batches   │
│                                                          │
│  Production Plan:                                        │
│    - Make 4 batches Cookie Dough                         │
│      (yields 120 Large Cookies, 20 extra)                │
│    - Make 3 batches Brownie Batter                       │
│      (yields 72 Large Brownies, 22 extra)                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Validation Rules

| Rule | Validation | Error Message |
|------|-----------|---------------|
| VAL-FG-001 | display_name required | "Yield name cannot be empty" |
| VAL-FG-002 | display_name max 200 chars | "Yield name too long (max 200 characters)" |
| VAL-FG-003 | items_per_batch required | "Items per batch cannot be empty" |
| VAL-FG-004 | items_per_batch > 0 | "Items per batch must be greater than zero" |
| VAL-FG-005 | recipe_id auto-set | System error if not set (should never happen) |
| VAL-FG-006 | recipe exists | "Recipe not found" |
| VAL-FG-007 | Unique (recipe_id, display_name) | "This yield type already exists for this recipe" |

---

## Workflow Summary

### User wants to define yield types:
1. Navigate to CATALOG mode → Recipes tab
2. Find recipe (e.g., "Cookie Dough")
3. Click [Edit] to open Recipe Edit form
4. Scroll to "Yield Types" section
5. Click [+ Add Yield Type]
6. Enter name ("Large Cookie") and count (30)
7. Click [Add]
8. Repeat for other yield types (Medium, Small)
9. Click [Save Recipe]

### User wants to view all yield types:
1. Navigate to CATALOG mode → Finished Units tab
2. Browse/search yield types
3. See which recipes produce which yields
4. Click yield type → opens parent Recipe Edit form

### User wants to edit yield type:
1. Navigate to Recipe Edit form
2. Find yield type in "Yield Types" section
3. Click [Edit] next to yield type
4. Modify name or count
5. Click [Save Recipe]

**Key principle: All FinishedUnit CRUD operations happen within Recipe Edit form.**

---

## Future Extensions (When Needed)

If user testing reveals limitations, can add:

**Optional Category Field:**
```python
item_category = Column(String(50), nullable=True, index=True)
# Examples: "cookie", "cake", "brownie", "bar", "pie"
# Enables filtering: "Show me all cookies"
```

**Optional Description Field:**
```python
yield_description = Column(Text, nullable=True)
# Examples: "3-inch diameter", "Made with large scoop", "9x13 pan"
# Provides additional context without cluttering display_name
```

**Optional Unit Field:**
```python
item_unit = Column(String(50), nullable=True)
# Examples: "cookie", "cake", "bar", "piece"
# Enables proper pluralization: "30 cookies" vs "1 cookie"
```

But **don't add these until user testing proves they're needed**.

---

## Summary

**Minimal FinishedUnit Design:**
- ✅ display_name (freeform text)
- ✅ items_per_batch (positive integer)
- ✅ recipe_id (foreign key, auto-set)
- ✅ Simple, fast, flexible
- ✅ Easy to extend later if needed

**UI Location:**
- ✅ **Managed in Recipe Edit form** (not separate interface)
- ✅ FinishedUnits tab is **read-only catalog view**
- ✅ Edit/Add/Delete happens in Recipe Edit form only

**User enters two things:**
1. What do you call it? → "Large Cookie"
2. How many per batch? → 30

**System does the rest.**

---

**END OF SECTION 5.1 REWRITE**
