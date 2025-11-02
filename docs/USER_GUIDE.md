# User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Managing Inventory](#managing-inventory)
3. [Creating Recipes](#creating-recipes)
4. [Planning Events](#planning-events)
5. [Tracking Production](#tracking-production)
6. [Generating Reports](#generating-reports)
7. [Tips & Best Practices](#tips--best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Launch

When you first launch the Seasonal Baking Tracker:

1. The application will create a new database in the `data/` folder
2. You'll see an empty dashboard
3. Start by adding ingredients to your inventory

### Main Interface

The application uses a tabbed interface with these sections:

- **Dashboard** - Overview of current activities
- **Inventory** - Manage ingredients and quantities
- **Recipes** - Create and manage recipes
- **Bundles** - Group finished goods together
- **Packages** - Create gift packages
- **Recipients** - Manage gift recipients
- **Events** - Plan holiday seasons
- **Reports** - View analytics and export data

---

## Managing Inventory

### Adding a New Ingredient

1. Click the **Inventory** tab
2. Click **Add Ingredient**
3. Fill in the form:
   - **Name**: e.g., "All-Purpose Flour"
   - **Brand**: e.g., "King Arthur"
   - **Category**: Select from dropdown (Flour/Grains, Sugar, etc.)
   - **Purchase Unit**: How you buy it (e.g., "bag")
   - **Purchase Unit Size**: Size description (e.g., "50 lb")
   - **Recipe Unit**: How recipes measure it (e.g., "cup")
   - **Conversion Factor**: How many recipe units per purchase unit (e.g., 200 = 1 bag = 200 cups)
   - **Quantity**: Current inventory in purchase units (e.g., 2.5 bags)
   - **Unit Cost**: Cost per purchase unit (e.g., $15.99)
4. Click **Save**

### Understanding Unit Conversions

**Example: Flour**
- You buy flour in 50 lb bags
- Recipes call for flour in cups
- 1 bag (50 lb) ≈ 200 cups
- Set: Purchase Unit = "bag", Recipe Unit = "cup", Conversion Factor = 200

The app will automatically convert recipe requirements back to purchase units for shopping.

### Creating an Inventory Snapshot

Before planning a new event:

1. Update all ingredient quantities to reflect current stock
2. Click **Create Snapshot**
3. Give it a meaningful name (e.g., "Pre-Christmas 2025")
4. This snapshot will be used for planning without affecting live inventory

---

## Creating Recipes

### Adding a Recipe

1. Click the **Recipes** tab
2. Click **Add Recipe**
3. Fill in basic information:
   - **Name**: e.g., "Chocolate Chip Cookies"
   - **Category**: e.g., "Cookies"
   - **Source**: Where recipe came from (optional)
   - **Estimated Time**: Prep + bake time
   - **Yield**: e.g., "48 cookies"
4. Click **Add Ingredient** for each ingredient:
   - Select ingredient from dropdown
   - Enter quantity
   - Select unit (must match ingredient's recipe unit)
5. Add any notes
6. Click **Save**

The app will automatically calculate the recipe cost based on ingredient prices.

### Viewing Recipe Cost

Each recipe displays:
- Cost per batch
- Cost per unit (batch cost ÷ yield)
- List of ingredients with quantities and individual costs

---

## Planning Events

### Creating a New Event

1. Click the **Events** tab
2. Click **New Event**
3. Fill in:
   - **Name**: e.g., "Christmas 2025"
   - **Year**: 2025
   - **Date Range**: Start and end dates
   - **Inventory Snapshot**: Select the snapshot to use for planning
4. Click **Save**

### Assigning Packages to Recipients

1. Open the event
2. Click **Assign Packages**
3. For each recipient:
   - Select recipient from dropdown
   - Select package(s) to give them
   - Specify quantity
4. Click **Save Assignments**

### Generating Shopping List

1. Open the event
2. Click **Generate Shopping List**
3. The app will show:
   - Total ingredients needed (in purchase units)
   - Current inventory (from snapshot)
   - Shortfall (what to buy)
   - Color coding:
     - 🟢 Green: Sufficient inventory
     - 🟡 Yellow: Low inventory (< 20% buffer)
     - 🔴 Red: Insufficient inventory
4. Click **Export to CSV** to save for shopping

### Understanding the Planning Summary

The event summary shows:
- Total packages to deliver
- Total bundles needed
- Total finished goods to produce
- Recipe batches required
- Estimated total cost

---

## Tracking Production

### Recording Production

1. Navigate to the event
2. Click **Production** tab
3. For each recipe:
   - Click **Record Production**
   - Enter actual quantity produced
   - Enter date produced
   - Add notes (optional)
4. The system can automatically deduct ingredients from live inventory

### Marking Packages as Delivered

1. In the event, go to **Deliveries**
2. Find the recipient
3. Click **Mark Delivered**
4. Enter delivery date
5. Optionally record actual cost if different from planned

### Tracking Progress

The event dashboard shows:
- Planned vs. actual production
- Packages assembled vs. total needed
- Packages delivered vs. total needed
- Cost overruns or savings

---

## Generating Reports

### Available Reports

**Inventory Report**
- Current stock levels
- Total inventory value
- Low stock items

**Event Summary**
- Planned vs. actual for the event
- Cost breakdown by category
- Production efficiency

**Recipient History**
- What each person has received over time
- Total value by recipient

**Cost Analysis**
- Most expensive ingredients
- Cost per package type
- Year-over-year trends

**Shopping List**
- Exportable by category
- Quantities in purchase units

### Exporting Data

1. Open any report
2. Click **Export to CSV**
3. Choose save location
4. Open in Excel or other spreadsheet software

---

## Tips & Best Practices

### Inventory Management
- Update inventory quantities regularly
- Create a new snapshot before each major event
- Keep purchase receipts to update unit costs
- Review and clean up unused ingredients annually

### Recipe Management
- Be precise with ingredient quantities for accurate costing
- Include notes about substitutions or variations
- Keep source information for reference
- Test recipes before adding to event plans

### Event Planning
- Plan events at least 2-4 weeks in advance
- Add 10-15% buffer to ingredient quantities
- Review previous years' events for insights
- Export shopping list to mobile device for store

### Production Tracking
- Record production immediately after baking
- Note any recipe adjustments in notes field
- Track actual costs for better future estimates
- Take photos of finished packages (store separately)

### Data Backup
- Database is in `data/baking_tracker.db`
- Back up before major changes
- Use Carbonite or similar for automatic backup
- Export reports periodically as CSV

---

## Troubleshooting

### Application Won't Start
- Ensure Python 3.10+ is installed
- Verify virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check for error messages in console

### Database Errors
- Database may be locked (close other instances)
- Check file permissions on `data/` folder
- If corrupted, restore from backup

### Unit Conversion Issues
- Verify conversion factors are correct
- Check that recipe units match ingredient's recipe unit type
- For custom conversions, calculate carefully

### Performance Issues
- Large data sets may slow down reports
- Archive old events if database grows too large
- Close unused browser windows/apps for memory
- Restart application periodically

### Missing Features
- This is a phased implementation
- Check CHANGELOG.md for current status
- Submit feature requests on GitHub

---

## Keyboard Shortcuts

*(To be implemented in future version)*

- `Ctrl+N` - New item in current tab
- `Ctrl+S` - Save current form
- `Ctrl+F` - Search/filter
- `Ctrl+Z` - Undo last edit
- `Escape` - Cancel/close dialog

---

## Getting Help

- Review this guide and the FAQ section
- Check [REQUIREMENTS.md](../REQUIREMENTS.md) for feature specifications
- Report issues on GitHub: [github.com/kentonium3/bake-tracker/issues](https://github.com/kentonium3/bake-tracker/issues)

---

**Document Status:** Living document, updated as features are implemented
**Last Updated:** 2025-11-02
