
---
id: docs/architecture/ingredient_taxonomy_research
doc_type: research
title: Ingredient & Food Taxonomy — Research Summary and Recommendation
status: draft
level: L2
owners: ["Kent Gale"]
last_validated: 2025-11-06
---

# Purpose

Summarize viable external standards for modeling foods/ingredients separately from brand, supplier, and packaging, and recommend a layered approach suitable for a consumer‑grade baking planner that can evolve into SaaS.

# TL;DR Recommendation

Use a **layered model**:

- **Generic Food/Ingredient layer:** *FoodOn* as the primary ID; enrich with optional **LanguaL facets** and **EFSA FoodEx2** codes; link to **USDA FoodData Central (FDC)** for nutrient profiles.
- **Commercial Product layer:** **GS1** (GTIN + **GPC** category + **GDSN** attributes) for brand/supplier/packaging, with packaging type/material codes and packaging levels (each/inner/case/pallet).
- **Crowd & Practical enrichment:** **Open Food Facts** (OFF) taxonomy/labels/packaging shapes for synonyms, autocomplete, and non‑critical enrichment.

This cleanly separates *what the food is* from *who makes it/how it’s packaged* and is compatible with retail and regulatory ecosystems.

# Candidate Standards (Strengths / Fit / Notes)

## 1) GS1 (GPC, GDSN, GTIN, Packaging Codes)
- **What:** Commerce/retail standard for trade items. Hierarchy via **GPC** (Segment → Family → Class → Brick + Brick Attributes). **GDSN/Global Data Model** defines trade‑item attributes: brand owner, GTINs at each packaging level, net content, nutrition panels, packaging levels and **packagingType/material** code lists.
- **Why it fits:** Covers **brand, supplier, and packaging** without polluting ingredient concepts. Industry‑standard identifiers and hierarchies.
- **Caveats:** Some artifacts/tools require MO membership; plenty of public docs exist. Not an ingredient ontology.

## 2) FoodOn (OBO Foundry)
- **What:** Open ontology describing foods, commodities, ingredients, sources, and processes; contains cross‑references to EFSA, FDA/CFR, GS1, and LanguaL.
- **Why it fits:** Strong backbone for **generic ingredients** independent of brand, with rich hierarchy and links to related ontologies.
- **Caveats:** Large; we will curate a slim subset for consumer UX performance.

## 3) EFSA FoodEx2
- **What:** EU regulator food classification; widely used in dietary exposure/consumption studies.
- **Why it fits:** Helpful **reference/mapping** for analytics and interoperability.
- **Caveats:** EU‑centric; keep as optional crosswalk.

## 4) LanguaL
- **What:** Faceted thesaurus: food source, part, physical state, treatment, cooking method, preservation, etc.
- **Why it fits:** Adds precision to generic ingredients (e.g., “almonds, roasted, salted”).
- **Caveats:** Extra complexity; use as optional facets, not primary IDs.

## 5) USDA FoodData Central (FDC)
- **What:** Open (CC0) U.S. database with **Foundation/SR Legacy (generic)** and **Branded Foods**; API + bulk downloads.
- **Why it fits:** Attach **nutrition** to generic ingredients; optionally crosswalk branded items.
- **Caveats:** Branded coverage varies by partners; taxonomy is not its main focus.

## 6) Open Food Facts (OFF)
- **What:** Public ingredients/category/label/additive/packaging taxonomies + API; multilingual synonyms and packaging shapes.
- **Why it fits:** Great for **autocomplete**, synonyms and lightweight enrichment when GS1 data is missing.
- **Caveats:** Crowd‑sourced; treat as non‑authoritative.

## 7) UNSPSC
- **What:** Procurement commodity codes.
- **Why it fits:** Optional if we integrate with purchasing/ERP.
- **Caveats:** Too coarse for recipe/ingredient modeling; not recommended as a primary taxonomy.

## 8) FDA 21 CFR 170.3 Categories
- **What:** U.S. regulatory food categories used for additive tolerances/intake estimates.
- **Why it fits:** Optional regulatory tag for analytics/reporting.
- **Caveats:** Not granular; do not use as ingredient taxonomy.

# Recommended Layering (Data Ownership Boundaries)

**A) Generic Food/Ingredient (Product)**  
- Primary ID: **FoodOn ID**  
- Optional: **LanguaL facets**, **FoodEx2 code**  
- Nutrition: **USDA FDC** (Foundation/SR Legacy) link

**B) Commercial/Branded (ProductVariant)**  
- Primary ID: **GS1 GTIN** per packaging level  
- Category: **GS1 GPC Brick (+ attributes)**  
- Brand/Supplier: brand owner (optionally GLN later)  
- Packaging: **packaging level**, **packaging type/material** codes, **net content**

**C) Enrichment**  
- **Open Food Facts** terms/IDs for synonyms, labels, eco‑tags, packaging shapes (optional)

# Implementation Notes / Ingestion Strategy

- Start small: preload a curated **FoodOn subset** covering baking staples and common holiday recipe ingredients; map to FDC for nutrition.
- Keep **GTIN** optional at first; allow manual ProductVariant creation for pantry items without barcodes.
- Normalize units and packaging via **GDSN netContent + UoM** when available; otherwise user‑entered with guardrails.
- Store crosswalks in separate tables to keep core entities clean and allow multiple mappings.

# Next Steps

1. Approve the layered model (see the accompanying **Ingredient Data Model Spec**).
2. Green‑light ingestion plan for FoodOn subset + FDC nutrition mapping.
3. Decide minimal **GPC Bricks** to seed for pantry/ProductVariant UX.
4. Create import scripts/placeholders so schema can remain stable while data grows.
