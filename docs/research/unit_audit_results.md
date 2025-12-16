Unit Audit Report
=================

Generated: 2025-12-16 11:04:45

Non-standard units found: 9

Table: finished_units
  ID 1: item_unit = "cookie" (not in valid units)
  ID 2: item_unit = "brownie" (not in valid units)
  ID 3: item_unit = "cookie" (not in valid units)
  ID 5: item_unit = "cookie" (not in valid units)

Table: recipes
  ID 1: yield_unit = "cookies" (not in valid units)
  ID 2: yield_unit = "brownies" (not in valid units)
  ID 3: yield_unit = "cookies" (not in valid units)
  ID 4: yield_unit = "pieces" (not in valid units)
  ID 5: yield_unit = "cookies" (not in valid units)

Standard Units Reference
------------------------
Weight:  oz, lb, g, kg
Volume:  tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
Count:   each, count, piece, dozen
Package: bag, box, bar, bottle, can, jar, packet, container, package, case

Total valid units: 27

Analysis Notes
--------------
The non-standard values found are in `yield_unit` and `item_unit` fields.
These fields are intentionally flexible to allow descriptive yield terms
like "cookies", "brownies", etc. They describe WHAT a recipe produces,
not standard measurement units.

**Recommended Action:** No migration needed. These values are intentional
and appropriate for their use case. The `yield_unit` and `item_unit` fields
should continue to accept custom descriptive values.

The following fields SHOULD use standard units (and all currently do):
- products.package_unit (or purchase_unit) - validated
- ingredients.density_volume_unit - validated
- ingredients.density_weight_unit - validated
- recipe_ingredients.unit - validated
- production_consumptions.unit - validated
- assembly_packaging_consumptions.unit - validated