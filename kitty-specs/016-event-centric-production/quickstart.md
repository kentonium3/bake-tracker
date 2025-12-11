# Quickstart: Event-Centric Production Model

**Feature**: 016-event-centric-production
**Date**: 2025-12-10

---

## Overview

This feature adds event-production linkage to enable progress tracking and fulfillment workflows. After implementation, users can:

1. Link production runs to specific events (e.g., "Christmas 2025")
2. Set explicit targets for how many batches/units to produce
3. Track progress toward targets with visual progress bars
4. Track package fulfillment status (pending → ready → delivered)

---

## Implementation Order

### Phase 1: Model Layer
1. Add `FulfillmentStatus` enum to `src/models/event.py`
2. Add `EventProductionTarget` model to `src/models/event.py`
3. Add `EventAssemblyTarget` model to `src/models/event.py`
4. Add `event_id` FK to `ProductionRun` model
5. Add `event_id` FK to `AssemblyRun` model
6. Add `fulfillment_status` column to `EventRecipientPackage`
7. Add relationships to `Event` model
8. Update `src/models/__init__.py` exports

### Phase 2: Service Layer
1. Update `BatchProductionService.record_batch_production()` with `event_id` param
2. Update `AssemblyService.record_assembly()` with `event_id` param
3. Add target CRUD methods to `EventService`
4. Add progress calculation methods to `EventService`
5. Add fulfillment status methods to `EventService`
6. Write comprehensive service tests

### Phase 3: Import/Export
1. Add `EventProductionTarget` to export/import
2. Add `EventAssemblyTarget` to export/import
3. Add `event_name` to ProductionRun export/import
4. Add `event_name` to AssemblyRun export/import
5. Add `fulfillment_status` to EventRecipientPackage export/import
6. Write import/export tests

### Phase 4: UI Layer
1. Add event selector to `RecordProductionDialog`
2. Add event selector to `RecordAssemblyDialog`
3. Add Targets tab to `EventDetailWindow`
4. Add progress display (CTkProgressBar + text) to Targets tab
5. Add fulfillment status column to package assignments view
6. Manual UI testing

---

## Key Files to Modify

| Layer | File | Changes |
|-------|------|---------|
| Models | `src/models/event.py` | Add 3 new classes, modify 2 existing |
| Models | `src/models/production_run.py` | Add event_id FK |
| Models | `src/models/assembly_run.py` | Add event_id FK |
| Models | `src/models/__init__.py` | Export new classes |
| Services | `src/services/batch_production_service.py` | Add event_id param |
| Services | `src/services/assembly_service.py` | Add event_id param |
| Services | `src/services/event_service.py` | Add 12 new methods |
| Services | `src/services/import_export_service.py` | Add new entities |
| UI | `src/ui/forms/record_production_dialog.py` | Add event selector |
| UI | `src/ui/forms/record_assembly_dialog.py` | Add event selector |
| UI | `src/ui/event_detail_window.py` | Add Targets tab |

---

## Testing Checklist

### Model Tests
- [ ] EventProductionTarget CRUD operations
- [ ] EventAssemblyTarget CRUD operations
- [ ] Unique constraint (one target per recipe/FG per event)
- [ ] Cascade delete (event → targets)
- [ ] Restrict delete (recipe/FG with targets)
- [ ] FulfillmentStatus enum validation

### Service Tests
- [ ] `set_production_target()` - create and update
- [ ] `set_assembly_target()` - create and update
- [ ] `get_production_progress()` - calculation accuracy
- [ ] `get_assembly_progress()` - calculation accuracy
- [ ] `record_batch_production(event_id=X)` - links correctly
- [ ] `record_assembly(event_id=X)` - links correctly
- [ ] `update_fulfillment_status()` - valid transitions
- [ ] `update_fulfillment_status()` - reject invalid transitions
- [ ] Progress with over-production (>100%)

### Import/Export Tests
- [ ] Export includes new entities and fields
- [ ] Import resolves event_name references
- [ ] Import handles null event_id
- [ ] Import handles fulfillment_status
- [ ] Round-trip preserves all data

### Manual UI Tests
- [ ] Event selector appears in Record Production dialog
- [ ] Event selector appears in Record Assembly dialog
- [ ] Events ordered by date (nearest upcoming first)
- [ ] Targets tab displays in Event Detail
- [ ] Progress bars update correctly
- [ ] Over-production shows >100%
- [ ] Fulfillment status dropdown works
- [ ] Status transitions enforced in UI

---

## Migration Notes

### Before Migration
1. Export all data: Menu → Data → Export All
2. Save export file safely

### Apply Migration
1. Pull updated code with new models
2. Delete `bake_tracker.db` file
3. Start application (creates new schema)
4. Import data: Menu → Data → Import

### Data Defaults
- ProductionRun.event_id → NULL
- AssemblyRun.event_id → NULL
- EventRecipientPackage.fulfillment_status → 'pending'

---

## Common Patterns

### Adding Event Selector to Dialog

```python
# In dialog __init__
self.events = event_service.get_all_events()
self.events.sort(key=lambda e: e.event_date or datetime.max)

# Create dropdown
event_options = ["(None - standalone)"] + [e.name for e in self.events]
self.event_var = ctk.StringVar(value=event_options[0])
self.event_dropdown = ctk.CTkOptionMenu(
    parent,
    variable=self.event_var,
    values=event_options
)

# Get selected event_id in confirm handler
def _get_selected_event_id(self):
    selected = self.event_var.get()
    if selected == "(None - standalone)":
        return None
    for event in self.events:
        if event.name == selected:
            return event.id
    return None
```

### Progress Bar with Text

```python
# Create progress row
row_frame = ctk.CTkFrame(parent)

name_label = ctk.CTkLabel(row_frame, text=recipe_name, width=150)
name_label.pack(side="left", padx=5)

progress_bar = ctk.CTkProgressBar(row_frame, width=100)
progress_bar.set(progress_pct / 100)  # 0.0 to 1.0
progress_bar.pack(side="left", padx=5)

text_label = ctk.CTkLabel(row_frame, text=f"{produced}/{target} ({progress_pct:.0f}%)")
text_label.pack(side="left", padx=5)

if is_complete:
    check_label = ctk.CTkLabel(row_frame, text="✓", text_color="green")
    check_label.pack(side="left", padx=2)
```

### Enforcing Sequential Status Transitions

```python
def update_fulfillment_status(self, erp_id: int, new_status: FulfillmentStatus):
    erp = self._get_package(erp_id)
    current = FulfillmentStatus(erp.fulfillment_status)

    valid_transitions = {
        FulfillmentStatus.PENDING: [FulfillmentStatus.READY],
        FulfillmentStatus.READY: [FulfillmentStatus.DELIVERED],
        FulfillmentStatus.DELIVERED: []
    }

    if new_status not in valid_transitions[current]:
        raise ValueError(
            f"Invalid transition: {current.value} → {new_status.value}. "
            f"Allowed: {[s.value for s in valid_transitions[current]]}"
        )

    erp.fulfillment_status = new_status.value
    return erp
```
