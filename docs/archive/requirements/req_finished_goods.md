# Finished Goods - Requirements Document

**Component:** Finished Goods (Units, Bundles, Packages)  
**Version:** 0.2 (Current) 
**Last Updated:** 2025-01-04  
**Status:** Draft - Awaiting Extension  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Finished Goods represent the **outputs of the baking process** in bake-tracker. They exist in a three-tier hierarchy: FinishedUnits (individual baked items), Bundles (consumer-packaged collections), and Packages (logistics containers). This taxonomy supports diverse output modes from bulk delivery to individual gift packaging.

### 1.2 Business Purpose

The Finished Goods system serves multiple business functions:

1. **Production Planning:** Defines what to bake for events
2. **Assembly Management:** Tracks bundling of items for delivery
3. **Output Flexibility:** Supports multiple delivery modes (bulk, bundled, packaged, per-serving)
4. **Inventory Tracking:** Manages stock of produced items (Phase 3)
5. **Event Fulfillment:** Links production to event requirements

### 1.3 Design Rationale

**Three-Tier Hierarchy:** Real-world baking operations involve multiple levels of "finished" state:
- **FinishedUnit:** Individual items fresh from the oven (1 cookie, 1 cake)
- **Bundle:** Consumer-facing packages (bag of 6 cookies, box of brownies)
- **Package:** Logistics containers for delivery (gift basket with multiple bundles)

This hierarchy supports both simple workflows (bulk cookie trays) and complex workflows (multi-bundle gift packages with deferred material decisions).

**Material vs Ingredient Separation:** Materials (bags, boxes, ribbon) have fundamentally different metadata and tracking needs than ingredients (flour, sugar). Materials are deferred to separate requirements (req_materials.md).

---

## 2. Finished Goods Hierarchy

### 2.1 Three-Tier Model

| Level | Name | Purpose | Example |
|-------|------|---------|---------|
| **Tier 1** | FinishedUnit | Individual baked items | 1 Chocolate Chip Cookie, 1 Vanilla Cake, 1 Truffle |
| **Tier 2** | Bundle | Consumer-packaged collections | Bag of 6 Cookies, Box of 12 Brownies, Tin of 24 Truffles |
| **Tier 3** | Package | Logistics containers | Gift Basket (3 bundles), Shipping Box (multiple recipients) |

### 2.2 Hierarchy Rules

**FinishedUnit (Tier 1):**
- Atomic baked item produced from a recipe variant
- Linked to exactly one RecipeIngredientVariant
- Can be delivered as-is (bulk mode) OR assembled into Bundles
- Inventory tracked at unit level (Phase 3)

**Bundle (Tier 2):**
- Collection of FinishedUnits in consumer packaging
- Contents: One or more FinishedUnits (can include other Bundles in Phase 3+)
- Packaging material: Cellophane bag, decorative box, tin, basket
- Material selection can be deferred until assembly (see F026)
- Inventory tracked at bundle level (Phase 3)

**Package (Tier 3):**
- Logistics container for delivery/shipping
- Contents: One or more Bundles and/or FinishedUnits
- Packaging material: Shipping box, gift basket, delivery tray
- May be pre-assigned to recipient or bulk delivery
- Not tracked in inventory (consumed at delivery)

### 2.3 Key Principle

**Hierarchy is compositional, not categorical:**
- A FinishedUnit (cake) may BE a finished good for delivery (no bundling)
- A Bundle may BE the final package (no additional packaging)
- System supports all permutations based on output mode

---

## 3. Scope & Boundaries

### 3.1 In Scope

**FinishedUnit Management:**
- ✅ Define FinishedUnits and link to recipe variants
- ✅ Track which recipe produces which FinishedUnit
- ✅ Calculate production quantities from event requirements
- ✅ Phase 3: Inventory tracking for cross-event use

**Bundle Management:**
- ✅ Define Bundle contents (FinishedUnit quantities)
- ✅ Calculate assembly requirements from event needs
- ✅ Deferred packaging material selection (Phase 2+)
- ✅ Phase 3: Inventory tracking and assembly runs

**Package Management:**
- ✅ Define Package contents (Bundle/FinishedUnit quantities)
- ✅ Support recipient assignment (pre-assigned vs bulk)
- ⏳ Phase 3+: Full packaging workflow

**Output Modes:**
- ✅ BULK_COUNT: Deliver FinishedUnits on trays/baskets
- ✅ BUNDLED: Deliver Bundles (bags, boxes, tins)
- ⏳ Phase 3: PACKAGED (multi-bundle containers)
- ⏳ Phase 3: PER_SERVING (guest-count based)
- ⏳ Phase 3: RECIPIENT_ASSIGNED (per-recipient packages)

### 3.2 Out of Scope (Phase 2)

**Explicitly NOT Yet Supported:**
- ❌ Cross-event inventory tracking (Phase 3)
- ❌ Inventory transactions (consume/add) (Phase 3 - see F040)
- ❌ Material management system (separate req_materials.md)
- ❌ Historical production tracking
- ❌ Cost calculation per finished good
- ❌ Nutrition calculation per finished good

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Define what a recipe can produce (FinishedUnit) so FinishedGoods can be defined.
2. Define what I can produce (FinishedGoods) from available recipes so I can plan production and assembly.
3. See how many batches to make of which recipe based on finished goods needed
4. Create bundles (gift bags, boxes) so I can package items attractively
5. Track what's been produced, what's pending, and what needs assembly
6. Defer packaging material choices until assembly time

**As an event planner, I want to:**
1. Specify event requirements in terms of finished goods (bundles or units)
2. See total production needed to fulfill event
3. See the status of FinishedGoods needed/produced.
4. Confirm when assembly is complete
5. See the estimated cost of FinishedGoods as a definition and in aggregate for an event.
6. Support different output modes (trays vs bags vs gift boxes)

**As a gift coordinator, I want to:**
1. Create multi-bundle packages for VIP recipients
2. Make bundling and packaging materials decisions as late as assembly time
3. Pre-assign packages to specific recipients

### 4.2 Use Case: Bulk Delivery (Trays)

**Actor:** Baker  
**Precondition:** Event requires FinishedUnits delivered loose  
**Output Mode:** BULK_COUNT

**Main Flow:**
1. User creates event: "House Party"
2. Sets output mode: BULK_COUNT
3. Specifies requirements:
   - 100 Chocolate Chip Cookies (FinishedUnit)
   - 50 Brownies (FinishedUnit)
   - 3 Cakes (FinishedUnit)
1. System calculates production plan (recipe batches)
2. User produces items
3. User delivers on trays (no assembly required)

**Postconditions:**
- Production plan shows 100 cookies, 50 brownies, 3 cakes
- No bundle/package assembly needed
- Event fulfilled with bulk delivery

### 4.3 Use Case: Bundled Gifts

**Actor:** Baker  
**Precondition:** Event requires packaged bundles  
**Output Mode:** BUNDLED

**Main Flow:**
1. User creates event: "Christmas Client Gifts"
2. Sets output mode: BUNDLED
3. Specifies requirements:
   - 50 Cookie Assortment Bags (Bundle)
     - Each contains: 6 cookies, 3 brownies
4. System explodes to FinishedUnit quantities:
   - 150 plain sugar cookies (50 x 3) (base recipe)
   - 150 decorated sugar cookies (50 × 3) (variant recipe)
   - 150 brownies (50 × 3)
1. System calculates production plan (recipe batches)
2. System checks inventory
3. System generates shopping list if needed
4. User purchases items and enters them into the app
5. User produces items
6. System checks assembly feasibility: ✅ Can assemble 50 bundles
7. User confirms assembly complete (checklist)
8. User delivers 50 bundles to clients

**Postconditions:**
- Production plan met requirements
- Assembly feasibility confirmed
- 50 bundles assembled and delivered

### 4.4 Use Case: Deferred Packaging Material Selection

**Actor:** Baker  
**Precondition:** Bundle defined, material choice not yet made  
**Trigger:** F026 deferred packaging decisions

**Main Flow:**
1. User defines Bundle: "Cookie Assortment Bag"
   - Contents: 6 cookies, 3 brownies
   - Packaging material: (not selected yet)
2. User plans event requiring 50 of these bundles
3. System calculates production (300 cookies, 150 brownies)
4. User produces items
5. System checks assembly feasibility: ✅
6. **At assembly time:** User selects material:
   - Choice: Snowflake cellophane bags (not Christmas tree)
7. User assembles 50 bundles with selected material
8. User delivers bundles

**Postconditions:**
- Material choice deferred until assembly
- Flexibility maintained for creative decisions
- Assembly completed with selected materials

---

## 5. Functional Requirements

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



**REQ-FG-006:** System shall support creation of Bundles with name and description  
**REQ-FG-007:** Each Bundle shall define contents as list of {FinishedUnit, quantity} pairs  
**REQ-FG-008:** Bundle contents shall support multiple FinishedUnit types (mixed bundles)  
**REQ-FG-009:** Bundle packaging material selection shall be optional (can be deferred)  
**REQ-FG-010:** System shall validate Bundle has at least one component  
**REQ-FG-011:** Bundles shall be selectable for event requirements (BUNDLED mode)

### 5.3 Package Management (Phase 3)

**REQ-FG-012:** System shall support creation of Packages with name and description  
**REQ-FG-013:** Each Package shall define contents as list of {Bundle/FinishedUnit, quantity} pairs  
**REQ-FG-014:** Package shall support recipient assignment (optional)  
**REQ-FG-015:** Packages shall be selectable for event requirements (PACKAGED mode)

### 5.4 Output Mode Support

**REQ-FG-016:** Events shall have an output_mode attribute (enum)  
**REQ-FG-017:** System shall support BULK_COUNT mode (FinishedUnits only)  
**REQ-FG-018:** System shall support BUNDLED mode (Bundles as requirements)  
**REQ-FG-019:** Phase 3: System shall support PACKAGED mode  
**REQ-FG-020:** Phase 3: System shall support PER_SERVING mode (guest count × template)  
**REQ-FG-021:** Phase 3: System shall support RECIPIENT_ASSIGNED mode

### 5.5 Assembly Planning

**REQ-FG-022:** System shall calculate assembly requirements from event Bundle needs  
**REQ-FG-023:** System shall explode Bundle requirements to FinishedUnit quantities  
**REQ-FG-024:** System shall validate assembly feasibility (enough components after production)  
**REQ-FG-025:** System shall provide assembly checklist for event (Phase 2 minimal)  
**REQ-FG-026:** Phase 3: System shall track assembly completion with inventory transactions

### 5.6 Recipe Linkage

**REQ-FG-027:** Each FinishedUnit shall be produced by exactly one RecipeIngredientVariant  
**REQ-FG-028:** System shall use this linkage for production planning (batches needed)  
**REQ-FG-029:** System shall validate recipe linkage exists before allowing FinishedUnit in planning

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-FG-NFR-001:** Hierarchy (Unit → Bundle → Package) shall be intuitive to non-technical bakers  
**REQ-FG-NFR-002:** Bundle content definition shall require max 3 clicks per component  
**REQ-FG-NFR-003:** Assembly feasibility status shall be clearly visible (icons, colors)  
**REQ-FG-NFR-004:** Deferred packaging decisions shall not block planning or production

### 6.2 Data Integrity

**REQ-FG-NFR-005:** No orphaned Bundles (all must have valid FinishedUnit components)  
**REQ-FG-NFR-006:** No orphaned FinishedUnits (all must link to valid recipe variant)  
**REQ-FG-NFR-007:** Bundle component quantities must be positive integers  
**REQ-FG-NFR-008:** Circular references not allowed (Bundle cannot contain itself)

### 6.3 Flexibility

**REQ-FG-NFR-009:** System shall support creative variations (new bundles without schema changes)  
**REQ-FG-NFR-010:** Material selection deferral shall not create technical debt  
**REQ-FG-NFR-011:** Output mode additions (Phase 3) shall not break existing event data

---

## 7. Data Model Summary

### 7.1 FinishedUnit Table Structure

```
FinishedUnit
├─ id (PK)
├─ uuid (unique)
├─ slug (unique)
├─ display_name
├─ description (optional)
├─ recipe_variant_id (FK → RecipeIngredientVariant, required)
├─ inventory_count (int, default 0) [Phase 3]
└─ timestamps
```

### 7.2 Bundle Table Structure

```
Bundle (formerly "FinishedGood")
├─ id (PK)
├─ uuid (unique)
├─ slug (unique)
├─ display_name
├─ description (optional)
├─ packaging_material_id (FK → Material, nullable, can defer)
├─ bundle_contents (relation)
│    └─ BundleContent: {finished_unit_id, quantity}
├─ inventory_count (int, default 0) [Phase 3]
└─ timestamps
```

### 7.3 Package Table Structure (Phase 3)

```
Package
├─ id (PK)
├─ uuid (unique)
├─ slug (unique)
├─ display_name
├─ description (optional)
├─ packaging_material_id (FK → Material, nullable)
├─ package_contents (relation)
│    └─ PackageContent: {bundle_id OR finished_unit_id, quantity}
├─ recipient_id (FK → Recipient, nullable)
└─ timestamps
```

### 7.4 Key Relationships

```
RecipeIngredientVariant
  └─ produces → FinishedUnit (1:1)

FinishedUnit
  └─ used_in → BundleContent (many)

Bundle
  ├─ contains → BundleContent (many)
  └─ used_in → PackageContent (many) [Phase 3]

Package [Phase 3]
  └─ contains → PackageContent (many)

Event
  ├─ output_mode (enum)
  └─ requirements:
       ├─ If BULK_COUNT → List[{finished_unit_id, quantity}]
       ├─ If BUNDLED → List[{bundle_id, quantity}]
       └─ If PACKAGED → List[{package_id, quantity}] [Phase 3]
```

---

## 8. Output Modes

### 8.1 BULK_COUNT (Phase 2)

**Description:** Deliver FinishedUnits loose on trays, in baskets, or bulk containers

**Use Cases:**
- House party with cookie trays
- Fundraiser with bulk brownies
- Casual gatherings

**Event Requirements Input:**
```
Event: House Party
Output Mode: BULK_COUNT

Requirements:
  - 100 Chocolate Chip Cookies (FinishedUnit)
  - 50 Brownies (FinishedUnit)
```

**Planning Calculation:**
- No explosion needed (already FinishedUnits)
- Calculate recipe batches directly
- No assembly required

### 8.2 BUNDLED (Phase 2)

**Description:** Deliver Bundles (consumer-packaged collections)

**Use Cases:**
- Client gifts in cellophane bags
- Holiday cookie tins
- Sampler boxes

**Event Requirements Input:**
```
Event: Christmas Client Gifts
Output Mode: BUNDLED

Requirements:
  - 50 Cookie Assortment Bags (Bundle)
    - Each contains: 6 cookies, 3 brownies
```

**Planning Calculation:**
- Explode Bundles to FinishedUnit quantities
- Calculate recipe batches
- Validate assembly feasibility
- Provide assembly checklist

### 8.3 PACKAGED (Phase 3)

**Description:** Deliver Packages containing multiple Bundles

**Use Cases:**
- VIP gift baskets with multiple items
- Corporate gift boxes
- Multi-recipient shipments

**Event Requirements Input:**
```
Event: VIP Client Gifts
Output Mode: PACKAGED

Requirements:
  - 10 Premium Gift Baskets (Package)
    - Each contains:
      - 1 Cookie Assortment (Bundle)
      - 1 Brownie Box (Bundle)
      - 1 Truffle Tin (Bundle)
```

**Planning Calculation:**
- Explode Packages to Bundles
- Explode Bundles to FinishedUnits
- Calculate recipe batches
- Validate assembly feasibility (two levels)

### 8.4 PER_SERVING (Phase 3)

**Description:** Distribute based on guest count with serving template

**Use Cases:**
- Weddings (100 guests, each gets 2 cookies + 1 brownie)
- Corporate events (per-person servings)

**Event Requirements Input:**
```
Event: Wedding Reception
Output Mode: PER_SERVING

Guest Count: 100
Serving Template:
  - 2 Cookies (any variety)
  - 1 Brownie
```

**Planning Calculation:**
- Multiply serving template by guest count
- Distribute varieties (if multiple)
- Calculate recipe batches

### 8.5 RECIPIENT_ASSIGNED (Phase 3)

**Description:** Pre-assign Packages to specific recipients

**Use Cases:**
- Personalized client gifts
- Mail-order shipments
- Tracked deliveries

**Event Requirements Input:**
```
Event: Holiday Shipping
Output Mode: RECIPIENT_ASSIGNED

Requirements:
  - 10 Premium Boxes → VIP Client List
  - 25 Standard Boxes → Regular Client List
```

**Planning Calculation:**
- Calculate by recipient tier
- Track shipping assignments
- Generate shipping labels

---

## 9. Assembly Workflow

### 9.1 Assembly Decision Tiers (per F026)

**Tier 1: Content Decisions (Planning Phase)**
- **When:** During event planning
- **What:** Which FinishedUnits in each Bundle? Quantities?
- **Must Decide:** Yes - required for production planning

**Tier 2: Material Decisions (Can Defer)**
- **When:** Anytime before physical assembly
- **What:** Which bag design? Box style? Ribbon color?
- **Can Defer:** Yes - supports creative flexibility

**Tier 3: Recipient Assignment (Varies)**
- **When:** Depends on output mode
- **What:** Which package goes to which recipient?
- **Required:** Only for RECIPIENT_ASSIGNED mode

### 9.2 Phase 2 Assembly Checklist (Minimal)

**Purpose:** Confirm assembly completion without inventory transactions

**UI Display:**
```
Assembly Checklist for "Christmas 2025":
  
  Production Status:
  ✅ 300 Chocolate Chip Cookies produced
  ✅ 150 Brownies produced
  
  Ready to Assemble:
  [ ] 50 Holiday Gift Bags
      Components available: ✅
      (6 cookies + 3 brownies per bag)
  
  [ ] 25 Truffle Boxes
      Components available: ✅
      (12 truffles per box)
```

**Behavior:**
- Checkboxes disabled until production complete
- Checking box records assembly confirmation
- No inventory transactions in Phase 2
- Event status updated to "assembly complete"

### 9.3 Phase 3 Assembly Workflow (Full)

**Additions in Phase 3:**
- Assembly runs create actual inventory transactions
- Material selection at assembly time
- Batch assembly tracking
- Assembly history and audit trail
- Cross-event inventory consumption

---

## 10. Validation Rules

### 10.1 FinishedUnit Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-FG-001 | FinishedUnit name required | "Finished unit name cannot be empty" |
| VAL-FG-002 | FinishedUnit must link to recipe variant | "Finished unit must be produced by a recipe variant" |
| VAL-FG-003 | Recipe variant must exist | "Recipe variant not found" |

### 10.2 Bundle Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-FG-004 | Bundle name required | "Bundle name cannot be empty" |
| VAL-FG-005 | Bundle must have at least one component | "Bundle must contain at least one item" |
| VAL-FG-006 | Component quantities must be positive | "Component quantity must be greater than zero" |
| VAL-FG-007 | Bundle cannot contain itself (circular) | "Bundle cannot contain itself" |
| VAL-FG-008 | All components must exist | "Component finished unit not found" |

### 10.3 Package Validation (Phase 3)

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-FG-009 | Package name required | "Package name cannot be empty" |
| VAL-FG-010 | Package must have at least one component | "Package must contain at least one item" |
| VAL-FG-011 | Package cannot contain itself | "Package cannot contain itself" |

---

## 11. Acceptance Criteria

### 11.1 Phase 2 (Current) Acceptance

**Must Have:**
- [ ] FinishedUnit creation with recipe variant linkage
- [ ] Bundle creation with FinishedUnit components
- [ ] BULK_COUNT output mode supported
- [ ] BUNDLED output mode supported
- [ ] Event requirements explosion (Bundle → FinishedUnit)
- [ ] Assembly feasibility check (event-scoped)
- [ ] Assembly completion checklist (minimal UI)
- [ ] Deferred packaging material selection (can be null)

**Should Have:**
- [ ] Bundle content validation (positive quantities, no circular refs)
- [ ] Assembly feasibility displayed with visual indicators
- [ ] Clear error messages for validation failures

**Nice to Have:**
- [ ] Bundle cloning (duplicate with new name)
- [ ] Bundle templates for common patterns
- [ ] Visual hierarchy display (Unit → Bundle → Package)

### 11.2 Phase 3 (Future) Acceptance

**Inventory Integration:**
- [ ] Cross-event finished goods inventory tracking
- [ ] Assembly runs with inventory transactions
- [ ] FinishedUnit consumption during assembly
- [ ] Bundle inventory addition after assembly

**Advanced Output Modes:**
- [ ] PACKAGED mode (multi-bundle containers)
- [ ] PER_SERVING mode (guest count based)
- [ ] RECIPIENT_ASSIGNED mode (per-recipient tracking)

**Material Management:**
- [ ] Material entity with metadata
- [ ] Material inventory tracking
- [ ] Material selection at assembly time
- [ ] Material cost tracking

---

## 12. Dependencies

### 12.1 Upstream Dependencies (Blocks This)

- ✅ Recipe system with ingredient variants (req_recipes.md)
- ✅ RecipeIngredientVariant → FinishedUnit linkage
- ⏳ Material entity definition (req_materials.md - future)

### 12.2 Downstream Dependencies (This Blocks)

- Event planning (requires finished goods definitions)
- Production planning (requires FinishedUnit → recipe linkage)
- Assembly planning (requires Bundle definitions)
- Inventory management (Phase 3 - requires finished goods tracking)

---

## 13. Testing Requirements

### 13.1 Test Coverage

**Unit Tests:**
- FinishedUnit validation rules
- Bundle content validation
- Bundle explosion to FinishedUnit quantities
- Circular reference detection

**Integration Tests:**
- Create FinishedUnit linked to recipe variant
- Create Bundle with multiple FinishedUnits
- Event requirements explosion (Bundle → FinishedUnit)
- Assembly feasibility calculation

**User Acceptance Tests:**
- Create event with BULK_COUNT mode
- Create event with BUNDLED mode
- Confirm assembly checklist workflow
- Defer packaging material selection

---

## 14. Open Questions & Future Considerations

### 14.1 Open Questions

**Q1:** Should Bundles support nested Bundles (Bundle contains Bundle)?  
**A1:** Deferred to Phase 3. Phase 2 supports Bundle contains FinishedUnits only.

**Q2:** How to handle partial assembly (some bundles done, some pending)?  
**A2:** Phase 2 uses simple checklist (all or nothing). Phase 3 adds granular tracking.

**Q3:** Should system suggest Bundle templates based on common patterns?  
**A3:** Good Phase 3+ feature. Track usage patterns, suggest popular bundles.

### 14.2 Future Enhancements

**Phase 3 Candidates:**
- Bundle nesting (Bundle contains Bundle)
- Assembly workflow automation
- Material cost tracking per Bundle
- Bundle popularity analytics
- Cross-event Bundle reuse

**Phase 4 Candidates:**
- AI-suggested Bundle compositions
- Nutrition facts per Bundle
- Allergen tracking per Bundle
- Custom Bundle builder UI
- Photo upload per Bundle/FinishedUnit

---

## 15. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-04 | Kent Gale | Initial seeded draft from planning discussions |

---

## 16. Approval & Sign-off

**Document Owner:** Kent Gale  
**Last Review Date:** 2025-01-04  
**Next Review Date:** TBD (after extension and refinement)  
**Status:** 📝 DRAFT - SEEDED

---

## 17. Related Documents

- **Design Specs:** `_F040_finished_goods_inventory.md` (inventory architecture - Phase 3)
- **Design Specs:** `F026-deferred-packaging-decisions.md` (material selection workflow)
- **Requirements:** `req_recipes.md` (recipe → FinishedUnit linkage)
- **Requirements:** `req_planning.md` (event planning with finished goods)
- **Requirements:** `req_materials.md` (future - material management)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT - SEEDED)**
