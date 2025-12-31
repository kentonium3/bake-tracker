# Ingredient Hierarchy Categorization Prompt

Use this prompt with an AI assistant (Claude, GPT, Gemini, etc.) to categorize your exported ingredients into a three-tier hierarchy.

---

## Context

I am migrating a baking ingredient database from a flat category structure to a three-tier hierarchy:

- **Level 0 (Root)**: Top-level categories (e.g., "Chocolate", "Flour", "Sugar")
- **Level 1 (Mid-tier)**: Sub-categories (e.g., "Dark Chocolate", "Whole Grain Flour")
- **Level 2 (Leaf)**: Specific ingredients that can be used in recipes (e.g., "Semi-Sweet Chocolate Chips", "All-Purpose Flour")

Only leaf ingredients (level 2) can have products or be used in recipes. Root and mid-tier categories are organizational only.

---

## Input Format

I will provide a JSON export of my current ingredients with this structure:

```json
{
  "metadata": {
    "export_date": "2025-12-31T12:00:00Z",
    "record_count": 487
  },
  "ingredients": [
    {
      "id": 1,
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category": "Flour",
      "is_packaging": false,
      "description": "Standard wheat flour for general baking"
    }
  ]
}
```

---

## Output Format

Please provide a JSON response with this exact structure:

```json
{
  "categories": [
    {
      "name": "Chocolate",
      "slug": "chocolate",
      "level": 0,
      "children": ["Dark Chocolate", "Milk Chocolate", "White Chocolate", "Cocoa"]
    },
    {
      "name": "Dark Chocolate",
      "slug": "dark_chocolate",
      "level": 1,
      "parent": "Chocolate",
      "children": []
    },
    {
      "name": "Milk Chocolate",
      "slug": "milk_chocolate",
      "level": 1,
      "parent": "Chocolate",
      "children": []
    }
  ],
  "assignments": [
    {
      "ingredient_slug": "semi_sweet_chips",
      "parent_name": "Dark Chocolate"
    },
    {
      "ingredient_slug": "milk_chocolate_chips",
      "parent_name": "Milk Chocolate"
    }
  ]
}
```

---

## Guidelines for Categorization

### Root Categories (Level 0)

Create **10-20 root categories** based on the types of ingredients in the export. Common baking categories include:

- Chocolate & Cocoa
- Flour & Starches
- Sugar & Sweeteners
- Dairy & Eggs
- Fats & Oils
- Nuts & Seeds
- Fruits (Fresh, Dried, Preserves)
- Spices & Flavorings
- Leaveners & Stabilizers
- Colorings & Decorations
- Grains & Cereals
- Packaging (if `is_packaging: true`)

### Mid-tier Categories (Level 1)

Create **2-5 sub-categories per root** where meaningful distinctions exist. Examples:

- Under "Flour & Starches": All-Purpose Flour, Bread Flour, Pastry Flour, Whole Grain Flour, Specialty Flour, Starches
- Under "Sugar & Sweeteners": Granulated Sugars, Brown Sugars, Liquid Sweeteners, Specialty Sweeteners
- Under "Nuts & Seeds": Tree Nuts, Peanuts, Seeds, Nut Butters

### Leaf Assignments

Assign **every existing ingredient** to a level 1 (mid-tier) category. The existing ingredients become level 2 (leaf) items automatically.

---

## Special Handling

### Packaging Items

Items where `is_packaging: true` should be categorized under a "Packaging" root category with appropriate sub-categories (Boxes, Bags, Ribbons, etc.).

### Ambiguous Items

If an ingredient could fit multiple categories, choose the most specific or common usage:
- "Chocolate Syrup" -> Chocolate & Cocoa / Chocolate Sauces
- "Almond Flour" -> Flour & Starches / Specialty Flour (not Nuts)

### Single-Member Categories

Avoid creating mid-tier categories with only one item. If a root category has few items, they can all share one mid-tier category (e.g., "General" or "Other").

---

## Example Categorization

### Input Ingredients (sample):

```json
[
  {"slug": "all_purpose_flour", "display_name": "All-Purpose Flour", "category": "Flour"},
  {"slug": "bread_flour", "display_name": "Bread Flour", "category": "Flour"},
  {"slug": "whole_wheat_flour", "display_name": "Whole Wheat Flour", "category": "Flour"},
  {"slug": "semi_sweet_chips", "display_name": "Semi-Sweet Chocolate Chips", "category": "Chocolate"},
  {"slug": "unsweetened_cocoa", "display_name": "Unsweetened Cocoa Powder", "category": "Chocolate"},
  {"slug": "granulated_sugar", "display_name": "Granulated Sugar", "category": "Sugar"},
  {"slug": "brown_sugar", "display_name": "Brown Sugar", "category": "Sugar"}
]
```

### Output (sample):

```json
{
  "categories": [
    {
      "name": "Flour & Starches",
      "slug": "flour_starches",
      "level": 0,
      "children": ["White Flour", "Whole Grain Flour"]
    },
    {
      "name": "White Flour",
      "slug": "white_flour",
      "level": 1,
      "parent": "Flour & Starches",
      "children": []
    },
    {
      "name": "Whole Grain Flour",
      "slug": "whole_grain_flour",
      "level": 1,
      "parent": "Flour & Starches",
      "children": []
    },
    {
      "name": "Chocolate & Cocoa",
      "slug": "chocolate_cocoa",
      "level": 0,
      "children": ["Chocolate Chips", "Cocoa Powders"]
    },
    {
      "name": "Chocolate Chips",
      "slug": "chocolate_chips",
      "level": 1,
      "parent": "Chocolate & Cocoa",
      "children": []
    },
    {
      "name": "Cocoa Powders",
      "slug": "cocoa_powders",
      "level": 1,
      "parent": "Chocolate & Cocoa",
      "children": []
    },
    {
      "name": "Sugar & Sweeteners",
      "slug": "sugar_sweeteners",
      "level": 0,
      "children": ["Granulated Sugars", "Brown Sugars"]
    },
    {
      "name": "Granulated Sugars",
      "slug": "granulated_sugars",
      "level": 1,
      "parent": "Sugar & Sweeteners",
      "children": []
    },
    {
      "name": "Brown Sugars",
      "slug": "brown_sugars",
      "level": 1,
      "parent": "Sugar & Sweeteners",
      "children": []
    }
  ],
  "assignments": [
    {"ingredient_slug": "all_purpose_flour", "parent_name": "White Flour"},
    {"ingredient_slug": "bread_flour", "parent_name": "White Flour"},
    {"ingredient_slug": "whole_wheat_flour", "parent_name": "Whole Grain Flour"},
    {"ingredient_slug": "semi_sweet_chips", "parent_name": "Chocolate Chips"},
    {"ingredient_slug": "unsweetened_cocoa", "parent_name": "Cocoa Powders"},
    {"ingredient_slug": "granulated_sugar", "parent_name": "Granulated Sugars"},
    {"ingredient_slug": "brown_sugar", "parent_name": "Brown Sugars"}
  ]
}
```

---

## Validation Checklist

Before finalizing your response, verify:

- [ ] Every ingredient from the input has an assignment
- [ ] Every `parent_name` in assignments matches a level 1 category `name`
- [ ] Every level 1 category has a `parent` that matches a level 0 category `name`
- [ ] Level 0 categories have no `parent` field
- [ ] All `slug` values are lowercase with underscores (no spaces or special characters)
- [ ] The `children` arrays in level 0 categories list all their level 1 children by name
- [ ] Level 1 categories have empty `children` arrays (existing ingredients are assigned via `assignments`)

---

## Your Task

Please categorize the following ingredients into the hierarchy structure described above. Respond with valid JSON only.

**[PASTE YOUR ingredients_export.json CONTENT HERE]**
