# Bug Fix: Add Online Vendor Support to Supplier Management

**Branch**: `bugfix/supplier-online-vendor-support`  
**Priority**: MEDIUM (user-reported workflow issue)  
**Estimated Effort**: 1 hour

## Context

**User Testing Finding**: Some suppliers are online vendors (Amazon, Penzeys online, King Arthur Baking) and don't have a physical store location. Current supplier form requires geographic fields (state, zip) for all suppliers, which doesn't make sense for online vendors.

**Problem**:
- Users forced to enter fake/meaningless location data for online vendors
- No way to store supplier website URL
- Form validation prevents saving without state/zip

## Current State vs Expected

### Current (Broken Workflow)
```
Add Supplier Form:
Name: [Amazon___________________]
State: [Required - must fake it] ❌
Zip: [Required - must fake it] ❌
(No URL field available)
```

### Expected (Fixed Workflow)
```
Add Supplier Form:
Name: [Amazon___________________]
Type: ○ Physical Store  ● Online Vendor

[If Online Vendor selected:]
  Website URL: [https://amazon.com___]
  State: [Optional - grayed out]
  Zip: [Optional - grayed out]

[If Physical Store selected:]
  Address: [_____________________]
  City: [_____________________]
  State: [Required ▼]
  Zip: [Required_____]
  Website URL: [Optional_____] (for stores with websites)
```

## Requirements

### 1. Database Schema Changes

**Add to Supplier model**:
```python
class Supplier(Base):
    # ... existing fields ...
    
    # NEW FIELDS:
    supplier_type = Column(String(20), default='physical')  # 'physical' or 'online'
    website_url = Column(String(500), nullable=True)
    
    # MODIFY: Make these nullable for online vendors
    # state = Column(String(2), nullable=False)  # CHANGE TO:
    state = Column(String(2), nullable=True)
    
    # zip_code = Column(String(10), nullable=False)  # CHANGE TO:
    zip_code = Column(String(10), nullable=True)
```

**Migration needed**: Yes

### 2. Form Validation Updates

**New validation rules**:
```python
def validate_supplier(data):
    """Validate supplier based on type."""
    
    # Name always required
    if not data.get('name'):
        raise ValidationError("Supplier name is required")
    
    supplier_type = data.get('supplier_type', 'physical')
    
    if supplier_type == 'online':
        # Online vendors: URL recommended, location optional
        if not data.get('website_url'):
            # Warning, not error
            logger.warning("Online vendor without website URL")
    
    elif supplier_type == 'physical':
        # Physical stores: location required
        if not data.get('state'):
            raise ValidationError("State is required for physical stores")
        if not data.get('zip_code'):
            raise ValidationError("Zip code is required for physical stores")
    
    # Validate URL format if provided
    if data.get('website_url'):
        url = data['website_url']
        if not url.startswith(('http://', 'https://')):
            raise ValidationError("Website URL must start with http:// or https://")
```

### 3. Supplier Form UI Updates

**Add supplier type selector** (at top of form):
```python
# Radio buttons for type selection
type_frame = ctk.CTkFrame(form)
type_frame.grid(row=0, column=0, columnspan=2, pady=10)

type_label = ctk.CTkLabel(type_frame, text="Supplier Type:")
type_label.pack(side="left", padx=5)

self.supplier_type_var = ctk.StringVar(value="physical")

physical_radio = ctk.CTkRadioButton(
    type_frame,
    text="Physical Store",
    variable=self.supplier_type_var,
    value="physical",
    command=self._on_supplier_type_change
)
physical_radio.pack(side="left", padx=10)

online_radio = ctk.CTkRadioButton(
    type_frame,
    text="Online Vendor",
    variable=self.supplier_type_var,
    value="online",
    command=self._on_supplier_type_change
)
online_radio.pack(side="left", padx=10)
```

**Add website URL field**:
```python
# Website URL field (always visible, required for online)
url_label = ctk.CTkLabel(form, text="Website URL:")
url_label.grid(row=N, column=0, sticky="w", padx=20, pady=5)

self.url_entry = ctk.CTkEntry(form, width=400)
self.url_entry.grid(row=N, column=1, sticky="w", pady=5)
```

**Add dynamic field enabling**:
```python
def _on_supplier_type_change(self):
    """Handle supplier type change - enable/disable location fields."""
    
    supplier_type = self.supplier_type_var.get()
    
    if supplier_type == 'online':
        # Disable/gray out location fields
        self.state_dropdown.configure(state="disabled")
        self.zip_entry.configure(state="disabled")
        self.address_entry.configure(state="disabled")
        self.city_entry.configure(state="disabled")
        
        # Optional: Clear location fields
        # self.state_dropdown.set("")
        # self.zip_entry.delete(0, 'end')
        
        # Highlight URL as important
        self.url_label.configure(text="Website URL: *", text_color="red")
        
    elif supplier_type == 'physical':
        # Enable location fields
        self.state_dropdown.configure(state="normal")
        self.zip_entry.configure(state="normal")
        self.address_entry.configure(state="normal")
        self.city_entry.configure(state="normal")
        
        # URL is optional for physical stores
        self.url_label.configure(text="Website URL:", text_color=("black", "white"))
```

### 4. Supplier List Display

**Add type indicator** to supplier list:
```python
# In supplier list/table
columns = ('name', 'type', 'location', 'url')

# Format type column
type_display = "🌐 Online" if supplier.supplier_type == 'online' else "📍 Store"

# Format location column
if supplier.supplier_type == 'online':
    location_display = supplier.website_url or "Online"
else:
    location_display = f"{supplier.city}, {supplier.state}" if supplier.city else supplier.state
```

## Implementation Tasks

### Task 1: Create Database Migration
**File**: New migration script

```python
"""Add online vendor support to suppliers.

Migration: Add supplier_type and website_url fields,
make state and zip_code nullable.
"""

def upgrade():
    # Add new fields
    op.add_column('suppliers', sa.Column('supplier_type', sa.String(20), server_default='physical'))
    op.add_column('suppliers', sa.Column('website_url', sa.String(500), nullable=True))
    
    # Make location fields nullable
    op.alter_column('suppliers', 'state', nullable=True)
    op.alter_column('suppliers', 'zip_code', nullable=True)

def downgrade():
    # Remove new fields
    op.drop_column('suppliers', 'website_url')
    op.drop_column('suppliers', 'supplier_type')
    
    # Revert location fields (may fail if NULL values exist)
    op.alter_column('suppliers', 'state', nullable=False)
    op.alter_column('suppliers', 'zip_code', nullable=False)
```

### Task 2: Update Supplier Model
**File**: `src/models/supplier.py`

1. Add `supplier_type` field (default='physical')
2. Add `website_url` field (nullable=True)
3. Make `state` nullable=True
4. Make `zip_code` nullable=True
5. Update `__repr__` to show type

### Task 3: Update Supplier Form
**File**: Supplier form (likely `src/ui/forms/supplier_form.py` or similar)

1. Add supplier type radio buttons at top
2. Add website URL entry field
3. Implement `_on_supplier_type_change()` handler
4. Update field enable/disable logic
5. Update save logic to include new fields
6. Update load logic to set supplier type

### Task 4: Update Validation
**File**: `src/utils/validators.py` or service layer

1. Update `validate_supplier()` function
2. Make state/zip conditional based on type
3. Add URL format validation
4. Add warning for online vendors without URL

### Task 5: Update Supplier List View
**File**: Supplier management tab

1. Add type indicator column (or icon)
2. Update location display logic
3. Show URL for online vendors
4. Add filter by type (optional)

### Task 6: Handle Existing Data
**File**: Migration or data fix script

```python
# After migration, review existing suppliers
# Manually classify if needed:
# - Amazon, Penzeys, King Arthur Baking → online
# - Costco, Wegmans, Stop & Shop → physical
```

### Task 7: Update Tests
**File**: Test files

1. Test online vendor creation
2. Test physical store creation
3. Test validation (online without location is OK)
4. Test validation (physical without location is error)
5. Test form field enabling/disabling

## Testing Checklist

### Add New Suppliers
- [ ] Can add online vendor with just name + URL
- [ ] Cannot add online vendor without name
- [ ] URL validation works (requires http:// or https://)
- [ ] Location fields disabled for online vendors
- [ ] Can add physical store with full location data
- [ ] Cannot add physical store without state/zip
- [ ] Can add physical store with optional URL

### Edit Existing Suppliers
- [ ] Can change physical → online
- [ ] Can change online → physical
- [ ] Fields enable/disable correctly on type change
- [ ] Validation updates based on type
- [ ] Save preserves supplier type

### Form Behavior
- [ ] Type selection defaults to "Physical Store"
- [ ] Switching type enables/disables correct fields
- [ ] URL field always visible
- [ ] Location fields gray out when disabled
- [ ] Visual indicators show required fields

### Data Integrity
- [ ] Migration runs successfully
- [ ] Existing suppliers default to 'physical'
- [ ] Existing data (state/zip) preserved
- [ ] Can save NULL state/zip for online vendors
- [ ] Cannot save NULL state/zip for physical stores

### Display
- [ ] Supplier list shows type indicator
- [ ] Online vendors show URL or "Online"
- [ ] Physical stores show city, state
- [ ] Filtering works (if implemented)

## Success Criteria

1. **Online Vendors Supported**: Can create suppliers without location data
2. **Website URLs Tracked**: Can store and display supplier websites
3. **Validation Correct**: Physical stores require location, online don't
4. **UI Clear**: Type selection is obvious and intuitive
5. **Data Migration Clean**: Existing suppliers work correctly
6. **User Validation**: Primary user confirms workflow is fixed

## Example Suppliers

### Online Vendors
```
Name: Amazon
Type: Online Vendor
URL: https://www.amazon.com
State: (blank)
Zip: (blank)

Name: Penzeys Spices
Type: Online Vendor
URL: https://www.penzeys.com
State: (blank)
Zip: (blank)

Name: King Arthur Baking
Type: Online Vendor
URL: https://www.kingarthurbaking.com
State: (blank)
Zip: (blank)
```

### Physical Stores (with websites)
```
Name: Costco Waltham
Type: Physical Store
URL: https://www.costco.com
Address: 385 Winter St
City: Waltham
State: MA
Zip: 02451
```

## Edge Cases

**Hybrid suppliers** (both physical and online):
- Classify based on primary shopping method
- Or create two supplier records (Amazon Online, Amazon Physical)
- Document recommendation in form help text

**International vendors**:
- State/Zip might not apply
- Consider "Other/International" type in future
- For now, use "Online Vendor" type

**Local suppliers** (farmer's market, friend):
- Can use Physical Store with minimal location
- Or add "Other" type in future
- For now, use Physical Store

## Related Files

**Primary Files**:
- Migration script (new file)
- `src/models/supplier.py` - Model updates
- Supplier form file (find location)
- `src/utils/validators.py` - Validation updates

**Service Layer**:
- `src/services/supplier_service.py` - May need updates

**UI**:
- Supplier management tab - Display updates

## Git Workflow

```bash
git checkout -b bugfix/supplier-online-vendor-support
git commit -m "feat: add supplier_type and website_url fields to model"
git commit -m "feat: add online vendor support to supplier form"
git commit -m "feat: update validation for online vs physical suppliers"
git commit -m "feat: update supplier list display with type indicator"
git commit -m "migrate: add supplier online vendor fields"
git push
```

---

**USER-DRIVEN FIX**: Directly addresses user testing feedback. Enables proper tracking of online vendors like Amazon, Penzeys, King Arthur Baking.
