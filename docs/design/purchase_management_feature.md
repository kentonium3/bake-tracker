# Purchase Management Feature - Design Document

**Status**: DRAFT - Initial Design Phase  
**Priority**: HIGH - Needed for production data entry  
**Target**: Feature 031 or similar

## Problem Statement

Currently, purchase data is difficult to view and manage:
- No UI to view purchase history
- No way to edit purchase prices except through database
- No way to add purchases without creating inventory
- Cannot track price trends over time
- Manual price research workflow is cumbersome

## User Needs

### Primary Use Cases

1. **View Purchase History**
   - See all purchases for a product
   - See all purchases from a supplier
   - Filter by date range
   - Sort by price, date, supplier

2. **Edit Purchase Data**
   - Update unit prices (after research)
   - Correct quantities
   - Fix dates
   - Change supplier
   - Add notes

3. **Add New Purchases**
   - Record purchases that were used immediately (no inventory)
   - Backfill historical purchase data
   - Bulk entry from receipts

4. **Price Analysis**
   - See price trends for a product
   - Compare prices across suppliers
   - Identify best value suppliers
   - Track price inflation

5. **Data Quality**
   - Identify purchases missing prices
   - Flag unusual prices
   - Bulk update capabilities
   - Import/export for external processing

## Proposed Solution

### Purchase Management Tab

New tab in main application: **"My Purchases"**

**Layout**:
```
┌─ My Purchases ──────────────────────────────────────────────┐
│ [+ Add Purchase] [Import CSV] [Export] [Refresh]           │
│                                                              │
│ Filters:                                                     │
│ Product: [All Products ▼]  Supplier: [All Suppliers ▼]     │
│ Date Range: [From: ____] [To: ____]  Show: [All ▼]         │
│                                                              │
│ ┌─ Purchases ───────────────────────────────────────────┐  │
│ │ Date       │Product        │Supplier│Qty│Price│Total │  │
│ │ 2024-12-15 │Dark Choc Chips│Costco  │ 2 │18.99│37.98 │  │
│ │ 2024-12-01 │Dark Choc Chips│Wegmans │ 1 │22.49│22.49 │  │
│ │ 2024-11-20 │All-Purp Flour │Costco  │10 │ 5.99│59.90 │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                              │
│ [Edit] [Delete] [View Details]                             │
└──────────────────────────────────────────────────────────────┘
```

### Key Features

#### 1. Purchase List View
- Sortable columns (date, product, supplier, price)
- Multi-column filtering
- Search across all fields
- Pagination for large datasets
- Color coding for missing/estimated prices

#### 2. Purchase Detail/Edit Form
```
┌─ Edit Purchase ────────────────────────────┐
│ Product: [Dark Chocolate Chips ▼]         │
│ Supplier: [Costco ▼]                      │
│                                            │
│ Purchase Date: [2024-12-15]               │
│ Quantity: [2] packages                    │
│                                            │
│ Unit Price: [$18.99]                      │
│ Total Cost: [$37.98] (calculated)         │
│                                            │
│ Store/Location: [Costco Waltham MA]       │
│ Receipt/Order #: [________________]       │
│                                            │
│ Notes:                                     │
│ [________________________________]         │
│ [________________________________]         │
│                                            │
│ Price Source: ○ Actual  ○ Estimated       │
│ Research URL: [________________]           │
│                                            │
│ [Save] [Delete] [Cancel]                  │
└────────────────────────────────────────────┘
```

#### 3. Bulk Operations
- Import from CSV (researched prices)
- Export to CSV (for research)
- Bulk price update
- Bulk supplier assignment
- Copy purchase to create new

#### 4. Price Analysis Views
- Price history chart for selected product
- Supplier comparison table
- Best price finder
- Price trend indicators

## Data Model Considerations

### Current Schema
```python
class Purchase(Base):
    id: int
    product_id: int
    supplier_id: int (nullable)
    purchase_date: date
    quantity_purchased: Decimal
    unit_price: Decimal (per package)
    total_cost: Decimal
    store_or_supplier: str (nullable)
    notes: text (nullable)
```

### Proposed Additions
```python
class Purchase(Base):
    # ... existing fields ...
    
    # New fields:
    receipt_number: str (nullable)
    price_source: str (nullable)  # 'actual', 'estimated', 'researched'
    research_url: str (nullable)  # Where price was found
    is_hidden: bool (default=False)  # For soft delete
```

## Integration Points

### With Inventory
- When adding inventory, optionally create purchase
- When creating purchase, optionally create inventory
- Link existing inventory to purchases
- Show related inventory items from purchase

### With Products
- Quick add purchase from product detail view
- Show purchase history in product view
- Price trends in product analysis

### With Suppliers
- Show all purchases from supplier
- Calculate average price per supplier
- Supplier performance metrics

## Implementation Phases

### Phase 1: Basic CRUD (MVP)
- Purchase list view with filtering
- Add/Edit/Delete purchase forms
- Link to existing products/suppliers
- Basic CSV import/export

### Phase 2: Price Research Workflow
- Enhanced CSV export for research
- Import researched prices
- Flag estimated vs actual prices
- Research URL tracking

### Phase 3: Analytics
- Price history charts
- Supplier comparison
- Best price finder
- Trend analysis

### Phase 4: Advanced Features
- Receipt photo upload
- OCR for receipt scanning
- Auto-create inventory from purchase
- Bulk operations UI

## Open Questions

1. **Purchase without inventory?**
   - Should we support recording purchases that don't create inventory?
   - Use case: Used immediately, tracking spending only

2. **Historical data?**
   - How far back should users track purchases?
   - Import old receipts/records?

3. **Multiple items per receipt?**
   - Should one purchase = one product?
   - Or one purchase = multiple line items?

4. **Price source tracking?**
   - How important is tracking actual vs estimated vs researched?
   - Should this affect reports/analytics?

5. **Soft delete vs hard delete?**
   - Keep purchase history even if product deleted?
   - Archive old purchases?

## Success Criteria

1. **Easy Price Entry**: Can update 100+ prices in under 2 hours
2. **Price Visibility**: Can see purchase history for any product
3. **Supplier Comparison**: Can compare prices across suppliers
4. **Data Quality**: Can identify and fix missing/incorrect prices
5. **Integration**: Seamlessly works with inventory and products

## Related Documents

- `_WORKFLOW_price_research_export_import.md` - Interim CSV workflow
- Feature 030 - Enhanced Export/Import (existing)
- Constitution - Data integrity principles

## Notes

- This feature enables transition from "test data" to "production data"
- Critical for accurate inventory valuation
- Supports future features (budgeting, trend analysis, supplier optimization)
- Should support both manual entry and bulk import workflows
