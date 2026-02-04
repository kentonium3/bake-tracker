# Paper Prototype Instructions: Finished Goods UX

## Materials Needed

- **8.5x11" paper or cardstock** (white) - 10 sheets
- **Colored paper** (optional but helpful):
  - Blue for filters/controls
  - Green for selected items
  - Yellow for active/in-progress areas
- **Scissors**
- **Tape or glue stick**
- **Markers** (black, red, blue)
- **Index cards** (3x5") - 20-30 cards
- **Sticky notes** - 1 pad
- **Paper clips** - 10-15 clips
- **Clear page protectors** (optional) - 2-3 for reusable components

---

## Pattern B: Accordion Builder Prototype

### Step 1: Create the Base Template

**Main Screen (8.5x11" paper, landscape orientation)**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Catalog Mode > Finished Goods > Create New (Guided Builder)            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Name: [_________________________________]  [Auto-generate from choices]│
│                                                                         │
│                                                                         │
│  [ACCORDION STEP 1 GOES HERE]                                           │
│                                                                         │
│                                                                         │
│                                                                         │
│  [ACCORDION STEP 2 GOES HERE]                                           │
│                                                                         │
│                                                                         │
│                                                                         │
│  [ACCORDION STEP 3 GOES HERE]                                           │
│                                                                         │
│                                                                         │
│                                                                         │
│  [ACCORDION STEP 4 GOES HERE]                                           │
│                                                                         │
│                                                                         │
│                                                      [Cancel]           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Instructions:**
1. Draw this frame on landscape paper
2. Leave space for 4 accordion sections (about 2.5" vertical each)
3. Write header at top
4. Draw Cancel button in bottom right

---

### Step 2: Create Accordion Section Templates

Cut out 4 accordion sections from separate pieces of paper. 
Each should be ~8" wide × 2.5" tall.

**Cut-out Template for Collapsed State (make 4 of these)**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▶ STEP [N]: [Step Title]                                               │
│   [Status message or greyed out text]                      [Action]    │
└─────────────────────────────────────────────────────────────────────────┘
```

Dimensions: 8" wide × 0.75" tall
Mark with: "COLLAPSED"

**Cut-out Template for Expanded State (make 4 of these)**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▼ STEP [N]: [Step Title]                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [Content area - 2" tall]                                               │
│  [This is where radio buttons, lists, and controls go]                  │
│                                                                         │
│                                                                         │
│                                            [Skip]  [Continue →]        │
└─────────────────────────────────────────────────────────────────────────┘
```

Dimensions: 8" wide × 2.5" tall
Mark with: "EXPANDED"

**Instructions:**
1. Cut out 4 collapsed sections
2. Cut out 4 expanded sections
3. Write step numbers and titles on each:
   - Step 1: Select Base Food Item (required)
   - Step 2: Add Packaging (optional)
   - Step 3: Add Decorations/Extras (optional)
   - Step 4: Review & Save
4. Use paper clips to attach collapsed/expanded pairs together
5. You'll swap them during testing to show state changes

---

### Step 3: Create Step 1 Content (Base Food Selection)

**Cut-out: Category Radio Buttons (on blue paper)**

```
┌────────────────────────────────────────────────────────────────┐
│ Category:  ( ) Cakes      ( ) Cookies      ( ) Brownies       │
│            ( ) Cupcakes   ( ) Other Baked  ( ) Candies        │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.5" tall

**Instructions:**
1. Cut out rectangle
2. Draw 6 radio buttons (circles)
3. This goes at top of Step 1 expanded content

---

**Cut-out: Filter Checkboxes (on blue paper)**

```
┌────────────────────────────────────────────────────────────────┐
│ Show:  [ ] Bare items only  [ ] Include pre-packaged          │
│        [ ] Include assemblies                                 │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.4" tall

**Instructions:**
1. Cut out rectangle
2. Draw 3 checkboxes (squares)
3. This goes below category radio buttons

---

**Cut-out: Search Box**

```
┌────────────────────────────────────────────────────────────────┐
│ Search: [_________________________] 🔍                         │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.3" tall

---

**Cut-outs: Food Item Cards (on index cards - make 12-15)**

Create individual cards for selectable items:

```
┌────────────────────────────────────────────────┐
│ ( ) Chocolate Cake (bare)                      │
│     From: Chocolate Cake recipe                │
│     Yield: 1 cake | Cost: $3.50                │
└────────────────────────────────────────────────┘
```

Dimensions: 3x5" index card (horizontal orientation)

**Make cards for:**
- Chocolate Cake (bare) - $3.50
- Vanilla Cake (bare) - $3.20
- Chocolate Layer Cake (bare) - $6.20
- Chocolate Chip Cookie (bare) - $0.18
- Sugar Cookie (bare) - $0.15
- Peanut Butter Cookie (bare) - $0.20
- Brownie (bare) - $0.45
- Chocolate Cupcake (bare) - $0.42
- Vanilla Cupcake (bare) - $0.38
- Lemon Bar (bare) - $0.55
- Chocolate Truffle (bare) - $0.35
- Peppermint Bark (bare) - $0.28

**Instructions:**
1. Write item name, source, yield, and cost on each card
2. Draw radio button (circle) at the start of each card
3. Organize into stacks:
   - Cakes stack (4 cards)
   - Cookies stack (3 cards)
   - Brownies stack (1 card)
   - Cupcakes stack (2 cards)
   - Other Baked stack (1 card)
   - Candies stack (2 cards)
4. Rubber band each stack
5. During testing, only show the stack that matches selected category

**Pro tip:** Use colored dots on card edges to mark categories:
- Red dot = Cakes
- Blue dot = Cookies
- Green dot = Brownies
- Yellow dot = Cupcakes
- Orange dot = Other Baked
- Purple dot = Candies

---

### Step 4: Create Step 2 Content (Packaging)

**Cut-out: Packaging Type Radio Buttons (on blue paper)**

```
┌────────────────────────────────────────────────────────────────┐
│ Type:  ( ) None/Skip  ( ) Box     ( ) Wrap/Film               │
│        ( ) Tin        ( ) Bag     ( ) Tray                     │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.4" tall

---

**Cut-out: Size Filter Radio Buttons (on blue paper)**

```
┌────────────────────────────────────────────────────────────────┐
│ Size/Fit:  ( ) Single item   ( ) Multiple items               │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.3" tall

---

**Cut-outs: Packaging Material Cards (on index cards - make 12-15)**

```
┌────────────────────────────────────────────────┐
│ ( ) Cake Box (8x8x5, kraft)                    │
│     Cost: $0.42 | Qty per FG: [1]              │
└────────────────────────────────────────────────┘
```

**Make cards for:**

**Boxes:**
- Cake Box (8x8x5, kraft) - $0.42
- Cake Box (8x8x5, white) - $0.38
- Window Box (clear top, 8x8x5) - $0.55
- Bakery Box (9x9x4, white) - $0.32
- Cookie Box (6x6x3, kraft) - $0.28
- Brownie Box (8x8x2, white) - $0.35

**Wrap/Film:**
- Cellophane Wrap (12x12) - $0.08
- Plastic Wrap (clear, 12x16) - $0.05
- Tinfoil (12x12) - $0.12

**Bags:**
- Cellophane Bag (4x6) - $0.06
- Cellophane Bag (6x9) - $0.09
- Bakery Bag (white, 6x9) - $0.07

**Tins:**
- Round Tin (6" diameter) - $1.20
- Square Tin (8x8) - $1.45

**Instructions:**
1. Use colored dots to mark types:
   - Red = Box
   - Blue = Wrap
   - Green = Bag
   - Yellow = Tin
2. Write "SINGLE" or "MULTI" on back to indicate size fit
3. Stack by type

---

### Step 5: Create Step 3 Content (Decorations/Extras)

**Cut-out: Decoration Type Radio Buttons (on blue paper)**

```
┌────────────────────────────────────────────────────────────────┐
│ Type:  ( ) None/Skip  ( ) Ribbon    ( ) Stickers              │
│        ( ) Tags       ( ) Tissue    ( ) Other                 │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 0.4" tall

---

**Cut-out: Current Extras Display Area**

```
┌────────────────────────────────────────────────────────────────┐
│ Current extras (0):                                            │
│                                                                │
│ [Empty - selected items will appear here]                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 1" tall

This is a "staging area" where you'll place selected decoration cards during testing.

---

**Cut-outs: Decoration Cards (on index cards - make 8-10)**

```
┌────────────────────────────────────────────────┐
│ ( ) Ribbon (red satin, 24")                    │
│     Cost: $0.15 | Qty: [1]                     │
└────────────────────────────────────────────────┘
```

**Make cards for:**
- Ribbon (red satin, 24") - $0.15
- Ribbon (gold metallic, 24") - $0.18
- Ribbon (white satin, 36") - $0.22
- Gift Tag (kraft, 2x3) - $0.05
- Sticker Sheet (holiday, 12ct) - $0.12
- Tissue Paper (red, 2 sheets) - $0.08
- Tissue Paper (white, 2 sheets) - $0.08
- Twine (natural, 36") - $0.10

**Instructions:**
1. Use colored dots to mark types:
   - Red = Ribbon
   - Blue = Tags
   - Green = Stickers
   - Yellow = Tissue
   - Orange = Other

---

### Step 6: Create Step 4 Content (Review & Save)

**Cut-out: Summary Display Area**

```
┌─────────────────────────────────────────────────────────────────┐
│ FINISHED GOOD SUMMARY                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Components per unit:                                            │
│   [Selected items will be listed here]                          │
│                                                                 │
│                                                   ----------    │
│ Total Cost per Unit:                              $XX.XX       │
│                                                                 │
│ This finished good will:                                        │
│   • Yield: [X] finished good(s) per assembly                    │
│   • Can be used in: Events, Other Finished Goods                │
│   • Nesting level: [X] (contains bare food items)               │
│                                                                 │
│ Auto-suggested tags:                                            │
│   [Tags will appear based on selections]                        │
│                                                                 │
│ Notes (optional):                                               │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │                                                           │   │
│ │                                                           │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│                     [Save Finished Good]  [Start Over]         │
└─────────────────────────────────────────────────────────────────┘
```

Dimensions: 7" wide × 4" tall

**Instructions:**
1. Leave space to write in selected items during testing
2. Have a calculator handy to add up costs
3. This is a static display - no cards to move around

---

### Step 7: Create State Indicators

**Cut-out: Checkmark Indicators (on green paper - make 4)**

```
✓
```

Dimensions: 0.5" × 0.5"

**Instructions:**
1. Cut out 4 green checkmarks
2. Place next to completed step numbers during testing
3. Example: "▶ STEP 1: Select Base Food Item ✓"

---

**Cut-out: "Selected:" Labels (on green paper - make 4)**

```
┌──────────────────────────────────────────────────────────┐
│ Selected: [Item Name] - $X.XX              [Change]     │
└──────────────────────────────────────────────────────────┘
```

Dimensions: 6" wide × 0.4" tall

**Instructions:**
1. These replace expanded sections when step is complete
2. Write selected item name in pencil (so you can erase/change)
3. Place over collapsed accordion section

---

## Pattern A: Hierarchical Drawer Prototype

### Step 1: Create Split-Screen Layout

**Main Canvas (left side - 5" wide × 8.5" tall, portrait)**

```
┌────────────────────────────┐
│ BUILDING: [Name____]       │
│                            │
│  Components (0)            │
│                [+ Add Item]│
│  ┌──────────────────────┐  │
│  │                      │  │
│  │                      │  │
│  │ [Empty or selected   │  │
│  │  components appear   │  │
│  │  here]               │  │
│  │                      │  │
│  │                      │  │
│  │                      │  │
│  └──────────────────────┘  │
│                            │
│  Estimated Cost: $0.00     │
│  Total Yield: 0 items      │
│                            │
└────────────────────────────┘
```

**Instructions:**
1. Draw this on left side of landscape paper
2. Draw vertical line 5" from left edge to separate canvas from drawer
3. Leave large empty box in middle for component staging area

---

### Step 2: Create Drawer Panel (right side - 5.5" wide × 8.5" tall)

**Drawer Template - Collapsed State**

```
│  │
│  │ [Drawer is hidden]
│  │
```

Just a vertical line - no drawer visible.

---

**Drawer Template - Expanded State**

```
│ ADD COMPONENT                      │
│ ┌────────────────────────────────┐ │
│ │ Quick Filters                  │ │
│ ├────────────────────────────────┤ │
│ │ [All] [Food] [Material] [FG]   │ │
│ │                                │ │
│ │ Nesting Level:                 │ │
│ │ [All] [Bare] [Level 1] [2+]    │ │
│ │                                │ │
│ │ Category:                      │ │
│ │ [Filter options here]          │ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ Search: [______]           🔍  │ │
│ └────────────────────────────────┘ │
│                                    │
│ Showing: X of XXX items            │
│ ┌────────────────────────────────┐ │
│ │ [Results appear here]          │ │
│ │                                │ │
│ │                                │ │
│ └────────────────────────────────┘ │
│                                    │
│    [Add Selected] [Cancel]         │
```

**Instructions:**
1. Cut out entire drawer panel (5.5" × 8.5")
2. Make TWO versions: collapsed (hidden) and expanded (shown above)
3. Use tape hinge on left edge so drawer can "slide" in and out
4. Or use paper clip to swap collapsed/expanded states

---

### Step 3: Create Filter Control Strips (for Drawer)

**Cut-out: Item Type Filter (on blue paper)**

```
┌────────────────────────────────────────────────┐
│ [All] [Food] [Material] [Finished Good]        │
└────────────────────────────────────────────────┘
```

Dimensions: 5" wide × 0.3" tall

**Instructions:**
1. Draw as pill-shaped buttons
2. Use sticky note to mark which one is "active" (or circle it)

---

**Cut-out: Nesting Level Filter (on blue paper)**

```
┌────────────────────────────────────────────────┐
│ [All] [Bare] [Level 1] [Level 2+]              │
└────────────────────────────────────────────────┘
```

Dimensions: 5" wide × 0.3" tall

---

**Cut-out: Category Filter - Dynamic (on blue paper, make 3 versions)**

**Version 1: Food Categories**
```
┌────────────────────────────────────────────────┐
│ [All] [Cakes] [Cookies] [Brownies] [...]       │
└────────────────────────────────────────────────┘
```

**Version 2: Material Categories**
```
┌────────────────────────────────────────────────┐
│ [All] [Boxes] [Wrap] [Ribbon] [Tags] [...]     │
└────────────────────────────────────────────────┘
```

**Version 3: Finished Good Categories**
```
┌────────────────────────────────────────────────┐
│ [All] [Individual] [Bundles] [Trays] [...]     │
└────────────────────────────────────────────────┘
```

**Instructions:**
1. Make all 3 versions
2. Swap them based on "Item Type" selection
3. Stack them with paper clips - only show relevant one

---

### Step 4: Create Drawer Result Cards (Reuse from Pattern B)

Use the same index cards you created for Pattern B:
- Food item cards (cakes, cookies, etc.)
- Packaging cards (boxes, wrap, etc.)
- Decoration cards (ribbon, tags, etc.)

**Instructions:**
1. Sort cards by type in separate stacks
2. During testing, only show cards matching active filters
3. Place visible cards in "Results" area of drawer

**Example filter logic:**
- Type: Food + Nesting: Bare + Category: Cakes → Show only bare cake cards
- Type: Material + Category: Boxes → Show only box cards

---

### Step 5: Create Selected Components Display (for Main Canvas)

**Cut-out: Component Row Template (make 5-6 reusable ones)**

```
┌──────────────────────────────────────────────┐
│ X. [Item Name_________________]        [×]   │
│    Qty: [__] per unit | $X.XX each           │
└──────────────────────────────────────────────┘
```

Dimensions: 4.5" wide × 0.6" tall

**Instructions:**
1. Cut out 5-6 blank templates
2. Use pencil to write selected items (can erase)
3. Stack these vertically in the "Components" area on main canvas
4. [×] button is for "remove" action

---

## Assembly Instructions for Each Pattern

### Pattern B Assembly

1. **Tape down the base template** (landscape paper with header/footer)
2. **Position Step 1 (collapsed)** on the template where marked
3. **Prepare Step 1 expanded version** with:
   - Category radio buttons taped inside
   - Filter checkboxes below that
   - Search box below that
   - Space for result cards at bottom
   - Continue button at bottom
4. **Prepare Step 2, 3, 4** similarly (collapsed and expanded versions)
5. **Organize card stacks** by category in small boxes or with rubber bands
6. **Keep sticky notes handy** for marking selections (or use pencil circles)

**Usage during testing:**
- Start with all steps collapsed
- When user would click to expand, swap collapsed for expanded
- When user selects category, show only that stack of cards
- When user completes step, swap expanded for collapsed+checkmark
- Write selected items on "Selected:" labels

---

### Pattern A Assembly

1. **Draw split-screen layout** on landscape paper
2. **Tape down left canvas** area
3. **Create drawer as separate piece** that can slide in from right
   - Option 1: Tape hinge on left edge of drawer
   - Option 2: Use paper clip to swap collapsed/expanded drawer
4. **Prepare filter strips** - stack with paper clips, swap as needed
5. **Organize card stacks** by type/category
6. **Prepare component row templates** for main canvas

**Usage during testing:**
- Start with drawer collapsed (hidden)
- When user clicks "+ Add Item", slide drawer in (or swap to expanded)
- When user changes filters, swap filter strips and card stacks
- When user selects item, move that card to main canvas component area
- When user clicks "Add Selected", slide drawer out (or swap to collapsed)

---

## Pro Tips for Testing

### Make It Interactive
- Use **sticky notes** to mark radio button selections (easy to move)
- Use **paper clips** to attach selected cards to staging areas
- Use **pencil** for any text you'll change during testing
- Use **colored dots** on card edges for quick sorting

### Prepare Multiple Scenarios
Create preset card arrangements for common scenarios:

**Scenario 1: Simple Cookie**
- Start with: Sugar Cookie (bare) selected
- Drawer shows: Cellophane bags

**Scenario 2: Boxed Cake**
- Start with: Chocolate Cake (bare) selected
- Drawer shows: Cake boxes
- Then: Ribbon options

**Scenario 3: Gift Basket**
- Start with: Tray selected
- Drawer shows: Multiple item types (brownies, cookies)
- Then: Tissue, cellophane

### Reusability Trick
- Put cards in **clear page protectors**
- Use **dry-erase markers** to mark selections
- Wipe clean between tests

### Speed Tips
- **Pre-filter card stacks** with rubber bands and labels
- **Number the backs** of cards so you can quickly find them
- **Color code edges** with markers for instant categorization

---

## What You'll Learn from Paper Prototyping

### Pattern B Questions
- Does the step order feel natural?
- Can user find items within category filters?
- Do they try to jump back to earlier steps?
- Is "Skip Step" used often?
- Do they get frustrated expanding/collapsing?

### Pattern A Questions
- Do filters make sense?
- Can user find items with filter combinations?
- Does drawer feel cluttered or overwhelming?
- Do they understand filter interactions?
- Do they want to add multiple items at once?

### General Questions
- Where do they get stuck?
- What do they try to click that doesn't exist?
- What questions do they ask?
- Do they understand nesting levels?
- Can they build target scenarios successfully?

---

## Time Estimates

**Pattern B Prep:**
- Base template: 15 min
- Accordion sections: 30 min
- All cut-out cards: 45 min
- Assembly: 15 min
- **Total: ~2 hours**

**Pattern A Prep:**
- Split screen template: 15 min
- Drawer panel: 20 min
- Filter strips: 20 min
- Reuse cards from Pattern B
- Assembly: 10 min
- **Total: ~1 hour** (if Pattern B already done)

**Both patterns: ~2.5 hours total prep**

---

## Next Step After Paper Prototyping

Once you identify the winning pattern:

1. **Photograph the final assembled prototype** for reference
2. **Document pain points** Marianne encountered
3. **Sketch refinements** based on feedback
4. **Then move to HTML mockup** with fake data
5. **Only after HTML validation** → CustomTkinter implementation

This workflow ensures you don't write code for a UI that doesn't work.
