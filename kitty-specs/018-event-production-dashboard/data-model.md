# Data Model: Event Production Dashboard

**Feature**: 018-event-production-dashboard
**Date**: 2025-12-12

## Summary

This feature requires **no new database entities**. All data access uses existing models from Feature 016 (Event-Centric Production Model).

## Existing Entities Used

### Event
- `id`, `name`, `event_date`, `notes`
- Used for: Filtering events, displaying event name/date on cards

### EventProductionTarget
- `event_id`, `recipe_id`, `target_batches`, `notes`
- Used for: Production progress calculation (via EventService)

### EventAssemblyTarget
- `event_id`, `finished_good_id`, `target_quantity`, `notes`
- Used for: Assembly progress calculation (via EventService)

### EventRecipientPackage
- `event_id`, `recipient_id`, `package_id`, `quantity`, `fulfillment_status`
- Used for: Fulfillment status counts (pending/ready/delivered)

### ProductionRun
- `event_id`, `recipe_id`, `num_batches`, `actual_yield`
- Used for: Calculating produced batches per target

### AssemblyRun
- `event_id`, `finished_good_id`, `quantity_assembled`
- Used for: Calculating assembled quantity per target

## New Service Method Data Contract

### get_events_with_progress()

**Input Parameters**:
```python
filter_type: str = "active_future"  # "active_future" | "past" | "all"
date_from: date = None              # Optional start date
date_to: date = None                # Optional end date
```

**Output Structure** (per event):
```python
{
    "event": Event,                 # SQLAlchemy model instance
    "event_id": int,
    "event_name": str,
    "event_date": date,
    "production_progress": [        # From get_production_progress()
        {
            "recipe_name": str,
            "target_batches": int,
            "produced_batches": int,
            "progress_pct": float,
            "is_complete": bool
        }
    ],
    "assembly_progress": [          # From get_assembly_progress()
        {
            "finished_good_name": str,
            "target_quantity": int,
            "assembled_quantity": int,
            "progress_pct": float,
            "is_complete": bool
        }
    ],
    "overall_progress": {           # From get_event_overall_progress()
        "production_targets_count": int,
        "production_complete_count": int,
        "production_complete": bool,
        "assembly_targets_count": int,
        "assembly_complete_count": int,
        "assembly_complete": bool,
        "packages_pending": int,
        "packages_ready": int,
        "packages_delivered": int,
        "packages_total": int
    }
}
```

## UI Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProductionDashboardTab                        │
├─────────────────────────────────────────────────────────────────┤
│  Filter Controls                                                 │
│  [Active & Future ▼] [From: ____] [To: ____] [Apply]            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              get_events_with_progress(filter_type, date_from, date_to)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  EventCard (per event in results)                                │
├─────────────────────────────────────────────────────────────────┤
│  [▶] Christmas 2025 | Dec 25, 2025 | ████████░░ 80%             │
│      3 pending | 2 ready | 5 delivered                           │
│  ─────────────────────────────────────────────────────────────── │
│  [Expanded Detail - hidden by default]                           │
│    Production: Sugar Cookies 2/4 (50%) ████░░░░                  │
│    Assembly: Gift Box 5/5 (100%) ████████ ✓                      │
│    [Record Production] [Record Assembly] [Shopping] [Details]    │
└─────────────────────────────────────────────────────────────────┘
```

## No Schema Changes Required

Feature 018 is a UI-only enhancement that consumes existing services. The data model is stable from Feature 016.
