# General UI reorganization

- The header area in each mode --  Catalog, Plan, Shop, Produce -- needs to be much more compact. 3-4 lines at most. 
- Rename mode Shop -> Purchase
- Rename mode Produce -> Make
- 
# Catalog Mode

![Catalog Mode](<./images/Screenshot_2026-01-07_a_7.29.27_PM.png>)

- header area way too large. Needs to be compact.

## Ingredient Catalog UI
- Stats shown in header summary area are all "0", even after clicking the refresh button.
- "413 ingredients loaded" notification could be in the title area next to "My Ingredients".
- Ingredient listing: The window showing the ingredient listing is only two rows high when the layout should dedicate most of the screen real estate to it. It's unmanageable as is.
- Subcategory filters: Very odd implementation. Whichever filter is selected blanks out the column of the level selected and the expected values show in the name column. The way filtering is expected to operate is that the ingredient list can be filtered using cascading category filters as is done on the Product Catalog dashboard. The point is to be able to see all columns of data but to filter all columns with cascading category filters. 

## Product Catalog UI
- Product listing: The window showing the product listing is only two rows high when the layout should dedicate most of the screen real estate to it.
- Sub-title "Manage Products, suppliers, and purchase history" is not necessary nor accurate. Remove it.
- Search bar and "Show Hidden" checkbox could be in the bar where the "Add Product" button is. The order should be Search bar, Show Hidden button, Add Product button.
- The product count "153 Products" could be next to the title "Product Catalog"

## Recipes Catalog UI
- Is Refresh button still needed?


# Plan Mode

![Plan Mode](<./images/Screenshot_2026-01-07_at_9.34.09_PM.png>)
- header area way too large. Needs to be compact. 3-4 lines at most. 


# Shop Mode

![Shop Mode](<./images/Screenshot_2026-01-07_at_9.46.50_PM.png>)
- Invert Shopping Lists, Purchases, Inventory sub-tab order
- header area way too large. Needs to be compact. 3-4 lines at most. 

## Inventory tab
- Ingredient hierarchy still showing as concatenated field value. Bad design decision. Need to make columns for each hierarchy level.
- My Pantry subtitle not needed. Delete.

## Purchases tab
- not implemented

## Shopping Lists tab
- not implemented

# Produce Mode
- header area way too large. Needs to be compact. 3-4 lines at most. 

## Production Runs
- Finished Units button goes nowhere
- Finished Goods button goes nowhere
- Is Refresh button needed?

## Assembly
- Not implemented

## Packaging
- Not implemented



