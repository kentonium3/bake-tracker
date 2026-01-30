# Planning Tab UI Redesign - Dropdown-Based Event Selector

**Date**: 2026-01-29
**Issue**: Redundant event table wasting screen space
**Solution**: Replaced table with compact dropdown selector

---

## Problem Analysis

The original Planning tab design had significant UX issues:

1. **Redundant Event Management**
   - Events tab already provides full event CRUD
   - Planning tab duplicated the event list unnecessarily
   - Users had to navigate the same event list twice

2. **Wasted Screen Space**
   - Event table took 10-25% of screen height
   - Planning workflow (the actual purpose) was cramped
   - Even with 100px height, table was unnecessary

3. **Wrong Mental Model**
   - Planning tab should be about *planning an event*
   - Not about *browsing and managing events*
   - Event management belongs in Events tab

---

## Solution: Dropdown-Based Selector

### New Design Philosophy

**Planning Tab = Single Event Focus**
- User selects ONE event to plan
- 95%+ of screen dedicated to planning that event
- No table, no pagination, no browsing

###new Layout

```
┌────────────────────────────────────────────────────────────┐
│ [Create Event]  Event: [Christmas 2026 ▼]  [Edit] [Delete]│ ← Compact header
│                 2026-12-15 • Draft                         │    (~50px)
├────────────────────────────────────────────────────────────┤
│ ╔════════════════════════════════════════════════════════╗ │
│ ║                                                        ║ │
│ ║  Recipe Selection for Christmas 2026                  ║ │
│ ║  ☑ Almond Biscotti                                    ║ │
│ ║  ☑ Butterscotch Pumpkin Cake                          ║ │
│ ║  ...                                                   ║ │
│ ║  [Save] [Cancel]                                       ║ │
│ ╠════════════════════════════════════════════════════════╣ │
│ ║  Finished Goods for Christmas 2026                     ║ │
│ ║  ...                                                   ║ │ ← 95% of screen!
│ ╠════════════════════════════════════════════════════════╣ │
│ ║  Batch Options                                         ║ │
│ ║  ...                                                   ║ │
│ ╠════════════════════════════════════════════════════════╣ │
│ ║  Plan State: Draft  [Lock Plan]                        ║ │
│ ╠════════════════════════════════════════════════════════╣ │
│ ║  Shopping Summary                                      ║ │
│ ║  ...                                                   ║ │
│ ╠════════════════════════════════════════════════════════╣ │
│ ║  Assembly Status                                       ║ │
│ ║  ...                                                   ║ │
│ ╚════════════════════════════════════════════════════════╝ │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ Ready                                                      │ ← Status bar
└────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Components Removed

1. **`PlanningEventDataTable` class** - Entire class deleted (70 lines)
2. **`_create_action_buttons()` method** - Replaced with `_create_event_selector()`
3. **`_create_data_table()` method** - Removed entirely
4. **`_on_row_select()` method** - Replaced with `_on_event_dropdown_change()`
5. **`_on_row_double_click()` method** - No longer needed
6. **DataTable import** - Removed from imports

### Components Added

1. **`_create_event_selector()` method** - Creates compact header with:
   - Create Event button (left)
   - Event dropdown (center)
   - Event details display (date, attendees, state)
   - Edit/Delete buttons (right)

2. **`_on_event_dropdown_change()` method** - Handles event selection
   - Loads event details
   - Shows all planning sections
   - Updates UI state

3. **`_update_event_details_display()` method** - Shows event metadata
   - Formats date, attendees, plan state
   - Displays in compact inline format

4. **`_clear_selection()` method** - Resets UI when no event selected

### Grid Layout Changes

**Before:**
```python
Row 0: Action buttons
Row 1: Data table (100-250px)
Row 2: Planning container (expandable)
Row 3: Status bar
```

**After:**
```python
Row 0: Event selector header (~50px)
Row 1: Planning container (expandable, 95%+ of screen!)
Row 2: Status bar
```

### Event Dropdown Logic

The dropdown intelligently selects which events to show:

1. **Primary: Incomplete Events**
   - Shows events where `plan_state != COMPLETED`
   - Focuses on events that need planning

2. **Fallback: Last 5 Events**
   - If all events are completed, shows most recent 5
   - Allows reviewing completed plans

3. **Smart Selection**
   - Auto-selects first event on load
   - Remembers selection across refreshes
   - Gracefully handles empty event list

---

## User Workflow

### Creating a New Event

1. Click **[Create Event]** button in Planning tab
2. Fill in event details dialog
3. Event is automatically selected in dropdown
4. Planning sections appear immediately
5. User can start planning right away

### Planning an Existing Event

1. Open Planning tab
2. Dropdown auto-shows incomplete events
3. Select event from dropdown (or use first event shown)
4. All planning sections appear
5. Scroll through sections to complete planning

### Switching Between Events

1. Click dropdown
2. Select different event
3. Planning sections update instantly
4. Previous work is saved

---

## Space Allocation Comparison

### Old Design (with table)
```
Header/Buttons:  5%
Event Table:    10%  ← Wasted space
Planning:       80%
Status Bar:      5%
```

### New Design (dropdown)
```
Header/Dropdown:  5%  ← Minimal!
Planning:        90%  ← Maximum space!
Status Bar:       5%
```

**Result**: Planning workflow gets +10% more screen space (80% → 90%)

---

## Benefits

### 1. **Eliminates Redundancy**
- No duplicate event list
- Clear separation: Events tab = manage, Planning tab = plan
- Simpler mental model

### 2. **Maximizes Planning Space**
- 95%+ of screen for actual planning work
- All sections easily accessible via scrolling
- No visual clutter

### 3. **Faster Workflow**
- No need to scroll through event table
- Quick dropdown selection
- Focus on planning, not navigation

### 4. **Better UX**
- Create Event button right where you need it
- Event context always visible (name, date, state)
- Edit/Delete easily accessible when needed

---

## Files Modified

1. **`src/ui/planning_tab.py`** - Complete redesign
   - Removed: PlanningEventDataTable class, table methods, row selection methods
   - Added: Event selector with dropdown, event detail display
   - Changed: Grid layout, refresh logic, event selection flow
   - Net change: ~100 lines removed, ~150 lines added (simpler overall)

---

## Testing Checklist

### Basic Functionality
- [ ] Planning tab loads without errors
- [ ] Dropdown shows incomplete events (or last 5 if all complete)
- [ ] Selecting event from dropdown loads planning sections
- [ ] Event details display (date, attendees, state) correctly
- [ ] Create Event button opens dialog
- [ ] Edit button opens dialog for selected event
- [ ] Delete button removes selected event

### Event Selection
- [ ] First event auto-selected on load
- [ ] Dropdown updates after creating new event
- [ ] Selection persists across refreshes (if event still exists)
- [ ] Empty state handled gracefully ("No events available")

### Planning Sections
- [ ] Recipe Selection appears and works
- [ ] Finished Goods Selection appears and works
- [ ] Batch Options appear and work
- [ ] Plan State controls appear correctly
- [ ] Shopping Summary displays
- [ ] Assembly Status displays
- [ ] Production Progress displays (when applicable)
- [ ] All sections scrollable

### Edge Cases
- [ ] No events in database → shows "No events available"
- [ ] All events completed → shows last 5 events
- [ ] Selected event deleted → dropdown resets
- [ ] Window resize → layout adapts correctly

---

## Migration Notes

### For Users

**No data migration needed** - This is purely a UI change. All existing:
- Events
- Recipe selections
- Finished goods selections
- Batch decisions
- Plan states
- etc.

...remain unchanged and fully accessible.

### For Developers

**No API changes** - All service methods remain the same:
- `event_service.get_events_for_planning()`
- `event_service.get_event_recipe_ids()`
- `event_service.get_event_fg_quantities()`
- etc.

The only change is how events are displayed and selected in the UI.

---

## Future Enhancements

1. **Dropdown Improvements**
   - Search/filter in dropdown (for users with many events)
   - Group by month or year
   - Show event icons/status indicators

2. **Quick Event Switching**
   - Keyboard shortcuts (Ctrl+[ / Ctrl+] to cycle)
   - Recent events list
   - Pin favorite events to top

3. **Planning Workflow Streamlining**
   - "Start Planning" wizard for new events
   - Progress indicator showing completed steps
   - Auto-save as you go

4. **Context Preservation**
   - Remember scroll position per event
   - Remember expanded/collapsed sections
   - Undo/redo for planning changes

---

## Rollback Instructions

If issues arise, revert the commit:

```bash
git log --oneline --grep="dropdown" -5  # Find the commit
git revert <commit-hash>
```

Note: This will restore the table-based layout.

---

## Related Issues

- User feedback: "Too much redundancy between Events and Planning tabs"
- User feedback: "Can't see planning sections, table takes too much space"
- Original issue: Planning workflow sections were inaccessible

---

## Conclusion

This redesign transforms the Planning tab from a hybrid event browser/planner into a focused, single-event planning workspace. By eliminating the redundant event table and replacing it with a compact dropdown, we free up 10% more screen space and provide a much clearer, more efficient user experience.

The Planning tab now does exactly one thing: **help you plan an event**. Event management stays in the Events tab where it belongs.
