# Planning Tab Layout: Before vs After

## Before: Broken Layout (All Stacked, No Scrolling)

```
┌─────────────────────────────────────────────────────┐
│ [Create Event] [Edit] [Delete]       [Refresh]     │ Row 0 (height: auto)
├─────────────────────────────────────────────────────┤
│                                                     │
│              EVENT DATA TABLE                       │
│         (Expands to fill space)                     │
│                                                     │ Row 1 (weight: 1) ← TAKES ALL SPACE
│  • Christmas 2026                                   │
│  • Easter 2026                                      │
│  • ...                                              │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│     Recipe Selection for Christmas 2026             │ Row 2 (300px height)
│     ☑ Almond Biscotti                              │
│     ☐ Almond Flour Brownies                        │
│     ... (20+ recipes)                               │
│                                                     │
│     [Save] [Cancel]                                 │
│─────────────────────────────────────────────────────│
│ Finished Goods for Christmas 2026                   │ Row 3 (200px height)
│ 0 of 0 selected                                     │ ← PARTIALLY VISIBLE
└─────────────────────────────────────────────────────┘
  ⬇ EVERYTHING BELOW IS UNREACHABLE (no scrolling)

  [Batch Options]                                      Row 4 ❌ NOT VISIBLE
  [Plan State Controls]                                Row 5 ❌ NOT VISIBLE
  [Amendment Controls]                                 Row 6 ❌ NOT VISIBLE
  [Shopping Summary]                                   Row 7 ❌ NOT VISIBLE
  [Assembly Status]                                    Row 8 ❌ NOT VISIBLE
  [Production Progress]                                Row 9 ❌ NOT VISIBLE

│ Ready                                               │ Row 10 ❌ NOT VISIBLE
```

**Problem**: Event table grows to fill available space, pushing planning sections out of view with no way to scroll to them.

---

## After: Split-Pane Layout (Fixed Table + Scrollable Planning)

```
┌─────────────────────────────────────────────────────┐
│ [Create Event] [Edit] [Delete]       [Refresh]     │ Row 0 (height: auto)
├─────────────────────────────────────────────────────┤
│  EVENT TABLE  • Christmas 2026   ← selected         │ Row 1 (height: 100px, FIXED)
│  (100px)      • Easter 2026                         │      Shows 2-3 events
├─────────────────────────────────────────────────────┤
│ ╔═══════════════════════════════════════════════╗   │
│ ║  SCROLLABLE PLANNING SECTIONS CONTAINER       ║   │ Row 2 (weight: 1, EXPANDS)
│ ║  ↕ (scroll to see all sections)               ║   │    MUCH MORE SPACE NOW!
│ ║                                                ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Recipe Selection for Christmas 2026           ║   │ ✅ VISIBLE
│ ║ ☑ Almond Biscotti                            ║   │
│ ║ ☑ Butterscotch Pumpkin Cake                  ║   │
│ ║ ... (20+ recipes)                             ║   │
│ ║ [Save] [Cancel]                               ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Finished Goods for Christmas 2026             ║   │ ✅ VISIBLE
│ ║ 0 of 0 selected                               ║   │
│ ║ (filtered by selected recipes)                ║   │
│ ║ [Save] [Cancel]                               ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Batch Options                                 ║   │ ✅ SCROLLABLE
│ ║ (batch sizes, inventory gaps)                 ║   │
│ ║ [Save Batch Decisions]                        ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Plan State: Draft                             ║   │ ✅ SCROLLABLE
│ ║ [Lock Plan]                                   ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Shopping Summary                              ║   │ ✅ SCROLLABLE
│ ║ • 2 cups flour needed                         ║   │
│ ║ • 1 lb butter needed                          ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Assembly Status                               ║   │ ✅ SCROLLABLE
│ ║ ✓ All recipes feasible                        ║   │
│ ╠═══════════════════════════════════════════════╣   │
│ ║ Production Progress                           ║   │ ✅ SCROLLABLE
│ ║ (shown when in production)                    ║   │
│ ╚═══════════════════════════════════════════════╝   │
│ ↕ Scroll here to see all sections                   │
├─────────────────────────────────────────────────────┤
│ Ready                                               │ Row 3 (height: auto)
└─────────────────────────────────────────────────────┘
```

**Solution**: Event table has fixed height; all planning sections live in a scrollable container that expands to fill remaining space.

---

## Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| **Event Table** | Expandable (weight=1) | Fixed 100px height (2-3 rows) |
| **Planning Sections** | Stacked with grid, no scrolling | Packed in scrollable container |
| **Accessibility** | Only first 1-2 sections visible | All sections accessible via scroll |
| **Layout Manager** | Grid throughout | Grid for panes, Pack within container |
| **User Experience** | Broken - can't access features | Functional - single-screen workflow |

---

## Layout Hierarchy (After)

```
PlanningTab (CTkFrame)
├─ Row 0: button_frame (CTkFrame)
│  ├─ create_button
│  ├─ edit_button
│  ├─ delete_button
│  └─ refresh_button
│
├─ Row 1: data_table (PlanningEventDataTable) [height: 250px]
│
├─ Row 2: _planning_container (CTkScrollableFrame) [weight: 1]
│  ├─ _recipe_selection_frame (RecipeSelectionFrame) [packed]
│  ├─ _fg_selection_frame (FGSelectionFrame) [packed]
│  ├─ _batch_options_container (CTkFrame) [packed]
│  ├─ _plan_state_frame (CTkFrame) [packed]
│  ├─ _amendment_controls_frame (CTkFrame) [packed]
│  ├─ _shopping_summary_frame (ShoppingSummaryFrame) [packed]
│  ├─ _assembly_status_frame (AssemblyStatusFrame) [packed]
│  └─ _production_progress_frame (ProductionProgressFrame) [packed]
│
└─ Row 3: status_frame (CTkFrame)
   └─ status_label
```

---

## Space Allocation Comparison

### Before Adjustment (250px table)
```
┌─────────────────────┐
│ Buttons (50px)      │ 5%
├─────────────────────┤
│                     │
│ Event Table         │ 25% ← Too much space
│ (250px)             │
│                     │
├─────────────────────┤
│ Planning Container  │ 65%
│ (scrollable)        │
└─────────────────────┘
```

### After Adjustment (100px table)
```
┌─────────────────────┐
│ Buttons (50px)      │ 5%
├─────────────────────┤
│ Event Table (100px) │ 10% ← Compact!
├─────────────────────┤
│                     │
│                     │
│ Planning Container  │ 85% ← Much more space!
│ (scrollable)        │
│                     │
│                     │
│                     │
└─────────────────────┘
```

**Result**: Planning sections get ~33% more screen space (from 65% to 85%)

---

## Visual Flow

### Before (Broken)
```
User Action:              Result:
─────────────────────────────────────────────
1. Select event      →   Recipe selection appears
2. Try to scroll     →   ❌ No scrolling available
3. Look for FG       →   ❌ Partially visible at bottom
4. Look for Batch    →   ❌ Completely hidden
5. Look for Status   →   ❌ Completely hidden
6. Give up           →   😞 Cannot use planning workflow
```

### After (Fixed)
```
User Action:              Result:
─────────────────────────────────────────────
1. Select event      →   All sections appear in container
2. Scroll down       →   ✅ See Recipe Selection
3. Scroll further    →   ✅ See Finished Goods
4. Scroll further    →   ✅ See Batch Options
5. Scroll further    →   ✅ See Plan State, Shopping, Assembly
6. Complete plan     →   ✅ Full workflow accessible! 🎉
```

---

## Responsive Behavior

### Window Resize

**Narrow Window:**
```
┌──────────────────┐
│ [Buttons]        │
├──────────────────┤
│ Event Table      │
│ (250px fixed)    │
├──────────────────┤
│ ╔══════════════╗ │
│ ║ Planning     ║ │ ← Small but scrollable
│ ║ Sections     ║ │
│ ╚══════════════╝ │
└──────────────────┘
```

**Tall Window:**
```
┌─────────────────────────────┐
│ [Buttons]                   │
├─────────────────────────────┤
│ Event Table                 │
│ (250px fixed)               │
├─────────────────────────────┤
│ ╔═════════════════════════╗ │
│ ║ Planning Sections       ║ │
│ ║                         ║ │
│ ║                         ║ │ ← More sections visible
│ ║                         ║ │    without scrolling
│ ║                         ║ │
│ ║                         ║ │
│ ╚═════════════════════════╝ │
└─────────────────────────────┘
```

---

## Scrolling Behavior

The `CTkScrollableFrame` provides:
- **Mousewheel scrolling** - Scroll anywhere in the planning section
- **Scrollbar** - Visual indicator on the right side
- **Smooth scrolling** - Native CustomTkinter behavior
- **Keyboard navigation** - Arrow keys, Page Up/Down work

### Scroll Indicators
```
┌─────────────────────────────┐
│ ╔═════════════════════════╗ │
│ ║ Recipe Selection        ║ │
│ ║ (visible section)       ║█│ ← Scrollbar position
│ ╠═════════════════════════╣█│    indicates content below
│ ║ FG Selection            ║█│
│ ║ (visible section)       ║█│
│ ╠═════════════════════════╣ │
│ ║ Batch Options           ║ │
│ ║ (partially visible)     ║ │
│ ╚═════════════════════════╝ │
└─────────────────────────────┘
        ⬇ More content below
```
