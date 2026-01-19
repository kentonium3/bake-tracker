# F038 Terminology Correction

**Date:** 2026-01-05
**Purpose:** Update F038 alignment document to reflect correct architectural understanding

---

## Key Change: "Bundles" → "Finished Goods" (assemblies)

### Previous Understanding (INCORRECT):
- Requirements use "Bundle" as a distinct entity
- Code uses "FinishedGood" as something different
- Need to add "Bundles" tab to CATALOG

### Correct Understanding:
- **FinishedUnit** = Individual items from recipes (single cookie, single cake)
- **FinishedGood** = Assembled items (gift bag with 6 cookies + 3 brownies)
- "Bundle" in requirements IS "FinishedGood" in code
- These are already SEPARATE TABLES (two-tier hierarchy)

---

## Updated F038 Terminology

### CATALOG Mode Tabs (CORRECTED):

**Original F038:**
```
CATALOG tabs:
- Ingredients
- Products
- Recipes
- Finished Units
- Bundles (NEW)      ← INCORRECT - creates confusion
- Packages (Phase 3)
```

**Corrected F038:**
```
CATALOG tabs:
- Ingredients
- Products
- Recipes
- Finished Units     ← Individual items from recipes
- Finished Goods     ← Assembled items (what req calls "bundles")
- Packages (Phase 3) ← Aesthetic containers
```

**UI Label Strategy:**
- Tab name: "Finished Goods"
- Tab subtitle: "(Assemblies & Gift Bundles)"
- This clarifies purpose without creating new terminology

---

## Model Mapping (CORRECTED)

| User Concept | Requirements Term | Code Model | Table |
|--------------|------------------|------------|-------|
| Individual baked item | FinishedUnit | FinishedUnit | finished_units |
| Functional assembly | **Bundle** | **FinishedGood** | finished_goods |
| Aesthetic container | Package | Package | packages |

**Key Insight:** "Bundle" in requirements = FinishedGood in code, NOT a separate entity.

---

## Planning Flow (CORRECTED)

### Event Output Modes:

**BULK_COUNT:**
```
User specifies: 300 FinishedUnits (cookies)
System uses: EventProductionTarget(finished_unit_id, quantity)
```

**BUNDLED:**
```
User specifies: 50 FinishedGoods (gift bags)
                Each FinishedGood defined as: 6 cookies + 3 brownies
System uses: EventAssemblyTarget(finished_good_id, quantity)
Explodes to: 300 cookies + 150 brownies (FinishedUnits)
```

**PACKAGED:**
```
User specifies: 50 Packages (aesthetic presentation)
System uses: EventRecipientPackage(package_id, quantity)
```

---

## PRODUCE Mode Flow (CORRECTED)

### Workflow:

1. **Production Runs Tab:**
   - Make recipe batches
   - Produces FinishedUnits (individual items)
   - Example: 7 batches Sugar Cookies → 336 cookies (FinishedUnits)

2. **Assembly Tab:**
   - Assemble FinishedGoods from FinishedUnits
   - Example: Combine 6 cookies + 3 brownies → 1 "Holiday Gift Bag" (FinishedGood)
   - Uses: FinishedGood.can_assemble() to check feasibility

3. **Packaging Tab:**
   - Add aesthetic materials to assembled FinishedGoods
   - Example: Put "Holiday Gift Bag" into tissue + ribbon + box
   - Creates: Package

**Terminology:**
- Production produces **FinishedUnits**
- Assembly creates **FinishedGoods** (what requirements call "bundles")
- Packaging creates **Packages** (aesthetic presentation)

---

## Why NOT "Bundles" Tab?

### Problem with Adding "Bundles" Tab:
1. Creates terminology drift (UI says "Bundle", code says "FinishedGood")
2. Suggests Bundles are separate from other FinishedGoods
3. Doesn't account for FinishedGood.assembly_type variations:
   - GIFT_BOX (bundle for gifts)
   - VARIETY_PACK (bundle for variety)
   - SAMPLER (bundle for sampling)
   - CUSTOM_ORDER (custom assembly)
   - TRAY (serving assembly)

### Solution: Use "Finished Goods" Tab:
1. ✅ Matches code model exactly
2. ✅ Encompasses all assembly types
3. ✅ Clarify with subtitle: "(Assemblies & Gift Bundles)"
4. ✅ No terminology drift

---

## Updated CATALOG Mode Dashboard Mockup

```
┌─ CATALOG ──────────────────────────────────────────────┐
│                                                         │
│  Quick Stats:                                          │
│  • 487 Ingredients | 892 Products | 45 Recipes         │
│  • 12 Finished Units | 8 Finished Goods               │
│                       ↑ Individual    ↑ Assemblies     │
│                                                         │
│  Quick Actions:                                        │
│  [+ New Ingredient] [+ New Recipe] [Import Catalog]    │
│                                                         │
│  Recent Activity:                                      │
│  • Chocolate Chip Cookie recipe updated (2 days ago)   │
│  • Added 5 new products (1 week ago)                   │
│                                                         │
│  [Ingredients] [Products] [Recipes]                    │
│  [Finished Units] [Finished Goods]                     │
│                    ↑ From recipes  ↑ Assemblies        │
└─────────────────────────────────────────────────────────┘
```

---

## Updated PLAN Mode Dashboard Mockup

```
┌─ PLAN ─────────────────────────────────────────────────┐
│                                                         │
│  Upcoming Events:                                      │
│  ┌────────────────────────────────────────────────┐   │
│  │ Christmas 2025          Dec 20-25              │   │
│  │ Output Mode: BUNDLED                           │   │
│  │ Status: ⚠️ Planning needed                     │   │
│  │ Requirements:                                   │   │
│  │   • 50 × Holiday Gift Bags (FinishedGood)      │   │
│  │       (6 cookies + 3 brownies each)            │   │
│  │ [View Details →]                               │   │
│  ├────────────────────────────────────────────────┤   │
│  │ New Year Party          Dec 31                 │   │
│  │ Output Mode: BULK_COUNT                        │   │
│  │ Status: ✅ Ready to produce                    │   │
│  │ Requirements:                                   │   │
│  │   • 100 × Chocolate Chip Cookies (Units)       │   │
│  │ [View Details →]                               │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  [Events] [Planning Workspace]                        │
└─────────────────────────────────────────────────────────┘
```

---

## Updated Mode Definitions Table

| Mode | Purpose | User Mental Model | Tabs |
|------|---------|-------------------|------|
| **CATALOG** | Define reusable things | "Set up my kitchen" | Ingredients, Products, Recipes, **Finished Units, Finished Goods** |
| **PLAN** | Create event plans | "What am I making?" | Events, Planning Workspace |
| **SHOP** | Acquire ingredients | "What do I need to buy?" | Shopping Lists, Purchases, Inventory |
| **PRODUCE** | Execute production & assembly | "Time to bake & assemble" | Production Runs, **Assembly, Packaging** |
| **OBSERVE** | Monitor status | "How am I doing?" | Dashboard, Event Status, Reports |

---

## Assembly Type Examples in Finished Goods Tab

**When user opens: CATALOG → Finished Goods**

```
┌─ Finished Goods (Assemblies & Gift Bundles) ───────┐
│                                                      │
│  [+ Add] [Edit] [Delete]                 [Refresh] │
│                                                      │
│  Search: [___] Type: [All ▼]  [Clear]              │
│                                                      │
│  ┌─ List ──────────────────────────────────────┐   │
│  │ Name                Type        Components   │   │
│  │ ──────────────────  ──────────  ──────────   │   │
│  │ Holiday Gift Bag    Gift Box    2 items      │   │
│  │ Deluxe Sampler      Variety     5 items      │   │
│  │ Cookie Tray         Tray        3 items      │   │
│  │ ...                                          │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Type Filter Options:                                │
│  • All                                              │
│  • Gift Box (bundles for gifts)                    │
│  • Variety Pack                                     │
│  • Sampler                                          │
│  • Custom Order                                     │
│  • Tray                                             │
└──────────────────────────────────────────────────────┘
```

---

## Corrected Workflow Example

### User Creates Event (BUNDLED Mode):

**Step 1: Define Assembly (CATALOG → Finished Goods)**
```
Create FinishedGood:
  display_name: "Holiday Gift Bag"
  assembly_type: GIFT_BOX  ← System knows this is a "bundle"
  
  Components (via Composition):
    - FinishedUnit: "Chocolate Chip Cookie" × 6
    - FinishedUnit: "Fudge Brownie" × 3
```

**Step 2: Plan Event (PLAN → Events)**
```
Create Event:
  name: "Christmas 2025"
  output_mode: BUNDLED
  
Create EventAssemblyTarget:
  event_id: Christmas 2025
  finished_good_id: "Holiday Gift Bag"  ← This is the "bundle"
  target_quantity: 50
```

**Step 3: Planning Workspace Calculates**
```
System recognizes:
  - output_mode = BUNDLED
  - Event requires FinishedGoods (assemblies)
  
System explodes:
  50 FinishedGoods × (6 cookies + 3 brownies)
  = 300 cookies + 150 brownies (FinishedUnits)

System groups by recipe:
  Cookies → Sugar Cookie Recipe
  Brownies → Brownie Recipe

System calculates batches...
```

**Step 4: Execute (PRODUCE → Production Runs)**
```
User makes batches:
  7 batches Sugar Cookies → 336 FinishedUnits (cookies)
  7 batches Brownies → 168 FinishedUnits (brownies)
```

**Step 5: Assemble (PRODUCE → Assembly)**
```
System checks FinishedGood.can_assemble(50):
  ✅ Have 336 cookies (need 300)
  ✅ Have 168 brownies (need 150)
  ✅ Can assemble 50 FinishedGoods

User assembles:
  Combine 6 cookies + 3 brownies → 1 Holiday Gift Bag
  Repeat 50 times
  
Result: 50 FinishedGoods (Holiday Gift Bags) assembled
```

---

## Summary of Changes to F038

### Remove These References:
- ❌ "Bundles" as separate tab
- ❌ "Bundle" as distinct entity from FinishedGood
- ❌ Any suggestion to create new Bundle table/model

### Update to These References:
- ✅ CATALOG tabs: "Finished Units" and "Finished Goods"
- ✅ "Finished Goods (Assemblies & Gift Bundles)" as tab title
- ✅ assembly_type distinguishes different FinishedGood types
- ✅ "Bundle" in requirements = FinishedGood with assembly_type = GIFT_BOX (or similar)
- ✅ Planning explodes FinishedGoods to FinishedUnits (not "bundles to items")

### Clarify Architecture:
- ✅ Two-tier hierarchy: FinishedUnit (from recipes) → FinishedGood (assemblies)
- ✅ EventAssemblyTarget links Events to FinishedGoods
- ✅ Composition links FinishedGoods to their FinishedUnit components
- ✅ No separate "Bundle" entity needed

---

## Impact on F038 Implementation

### Phase 1: F038 Foundation (NO CHANGE in effort: 20-30 hours)

**CATALOG Mode Migration:**
- Migrate "Finished Units" tab (existing)
- Migrate "Finished Goods" tab (existing, may be misnamed currently)
- Remove any "Bundles" tab references from spec
- Add subtitle clarification: "(Assemblies & Gift Bundles)"

**No schema changes needed - infrastructure already exists**

---

## Terminology Glossary for Development

| User-Facing Term | Code Model | Table | Description |
|------------------|------------|-------|-------------|
| Individual Item | FinishedUnit | finished_units | Single cookie, truffle, cake - produced from recipe |
| Assembly / Bundle | FinishedGood | finished_goods | Assembled item containing FinishedUnits or other FinishedGoods |
| Gift Bag / Gift Box | FinishedGood (assembly_type=GIFT_BOX) | finished_goods | Specific type of assembly for gifting |
| Variety Pack | FinishedGood (assembly_type=VARIETY_PACK) | finished_goods | Specific type of assembly for variety |
| Package | Package | packages | Aesthetic container with materials (tissue, ribbon, box) |

---

**RECOMMENDATION FOR F038:**

1. Update all "Bundle" references to "Finished Goods (assemblies)"
2. Clarify in spec: "Requirements documents may use 'Bundle' terminology, which maps to FinishedGood model"
3. Remove any suggestion to create new Bundle tab or entity
4. Use "Finished Goods" tab with subtitle "(Assemblies & Gift Bundles)"
5. Proceed with implementation using existing models

**No architectural changes needed - terminology alignment only.**

---

**END OF TERMINOLOGY CORRECTION**
