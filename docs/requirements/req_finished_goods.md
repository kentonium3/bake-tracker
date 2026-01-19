# Finished Goods - Requirements Document

**Component:** Finished Goods (Units, FinishedGoods, Packages)
**Version:** 0.3
**Last Updated:** 2025-01-08
**Status:** Current
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Finished Goods represent the **outputs of the baking process** in bake-tracker. They exist in a three-tier hierarchy: FinishedUnits (individual baked items), FinishedGoods (consumer-packaged collections), and Packages (logistics containers). This taxonomy supports diverse output modes from bulk delivery to individual gift packaging.

### 1.2 Business Purpose

The Finished Goods system serves multiple business functions:

1. **Production Planning:** Defines what may be baked for events
2. **Assembly Management:** Tracks bundling of items for delivery
3. **Output Flexibility:** Supports multiple delivery modes (bulk, bundled, packaged, per-serving)
4. **Inventory Tracking:** Manages stock of produced items (Phase 3)
5. **Event Fulfillment:** Links production to event requirements

### 1.3 Design Rationale

**Three-Tier Hierarchy:** Real-world baking operations involve multiple levels of "finished" state:
- **FinishedUnit:** Individual items fresh from the oven (1 cookie, 1 cake)
- **FinishedGood:** Consumer-facing packages (bag of 6 cookies, box of brownies), representing an assembly of FinishedUnits.
- **Package:** Logistics containers for delivery (gift basket with multiple FinishedGoods)

This hierarchy supports both simple workflows (bulk cookie trays) and complex workflows (multi-FinishedGood gift packages with deferred material decisions).

**Material vs Ingredient Separation:** Materials (bags, boxes, ribbon) have fundamentally different metadata and tracking needs than ingredients (flour, sugar). Materials are deferred to separate requirements (req_materials.md).

---

## 2. Finished Goods Hierarchy

### 2.1 Three-Tier Model

| Level      | Name         | Purpose                          | Example                                                        |
| ---------- | ------------ | -------------------------------- | -------------------------------------------------------------- |
| **Tier 1** | FinishedUnit | Individual baked items           | 1 Chocolate Chip Cookie, 1 Vanilla Cake, 1 Truffle             |
| **Tier 2** | FinishedGood | Consumer-packaged assemblies     | Bag of 6 Cookies, Box of 12 Brownies, Tin of 24 Truffles       |
| **Tier 3** | Package      | Logistics containers             | Gift Basket (3 FinishedGoods), Shipping Box (multiple recipients) |

### 2.2 Hierarchy Rules

**FinishedUnit (Tier 1):**
- Atomic baked item produced from a recipe.
- Can be delivered as-is (bulk mode) OR assembled into FinishedGoods.
- Inventory is tracked at the unit level.

**FinishedGood (Tier 2):**
- A collection of FinishedUnits, representing an assembly.
- Contents: One or more FinishedUnits.
- Packaging material: Cellophane bag, decorative box, tin, basket.
- Material selection can be deferred until assembly (see F026).
- Inventory of assembled FinishedGoods is tracked.

**Package (Tier 3):**
- Logistics container for delivery/shipping.
- Contents: One or more FinishedGoods and/or FinishedUnits.
- Packaging material: Shipping box, gift basket, delivery tray.
- May be pre-assigned to recipient or bulk delivery.
- Not tracked in inventory (consumed at delivery).

### 2.3 Key Principle

**Hierarchy is compositional, not categorical:**
- A FinishedUnit (cake) may BE a finished good for delivery (no assembly).
- A FinishedGood may BE the final package (no additional packaging).
- System supports all permutations based on output mode.

---

## 3. Scope & Boundaries

### 3.1 In Scope

**FinishedUnit Management:**
- ✅ Define FinishedUnits and link to recipe variants
- ✅ Track which recipe produces which FinishedUnit
- ✅ Calculate production quantities from event requirements
- ✅ Phase 3: Inventory tracking for cross-event use

**FinishedGood Management:**
- ✅ Define FinishedGood contents (FinishedUnit quantities)
- ✅ Calculate assembly requirements from event needs
- ✅ Deferred packaging material selection (Phase 2+)
- ✅ Phase 3: Inventory tracking and assembly runs

**Package Management:**
- ✅ Define Package contents (FinishedGood/FinishedUnit quantities)
- ✅ Support recipient assignment (pre-assigned vs bulk)
- ⏳ Phase 3+: Full packaging workflow

**Cost Visibility**
- Cost calculation per finished good is available when FinishedGoods are selected for an event


**Output Modes:**
- ✅ BULK_COUNT: Deliver FinishedUnits on trays/baskets
- ✅ ASSEMBLED: Deliver FinishedGoods (bags, boxes, tins)
- ⏳ Phase 3: PACKAGED (multi-FinishedGood containers)
- ⏳ Phase 3: PER_SERVING (guest-count based)
- ⏳ Phase 3: RECIPIENT_ASSIGNED (per-recipient packages)

### 3.2 Out of Scope (Phase 2)

**Explicitly NOT Yet Supported:**
- ❌ Cross-event inventory tracking (Phase 3)
- ❌ Inventory transactions (consume/add) (Phase 3 - see F040)
- ❌ Material management system (separate req_materials.md)
- ❌ Historical production tracking
- ❌ Nutrition calculation per finished good

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Define what a recipe can produce (FinishedUnit) so FinishedGoods can be defined.
2. Define what I can produce (FinishedGoods) from available recipes so I can plan production and assembly.
3. See how many batches to make of which recipe based on finished goods needed
4. Create FinishedGood assemblies (gift bags, boxes) so I can package items attractively
5. Track what's been produced, what's pending, and what needs assembly
6. Defer packaging material choices until assembly time

**As an event planner, I want to:**
1. Specify event requirements in terms of finished goods (assemblies or units)
2. See total production needed to fulfill event
3. See the status of FinishedGoods needed/produced.
4. Confirm when assembly is complete
5. See the estimated cost of FinishedGoods as a definition and in aggregate for an event.
6. Support different output modes (trays vs bags vs gift boxes)

**As a gift coordinator, I want to:**
1. Create multi-FinishedGood packages for VIP recipients
2. Make assembly and packaging materials decisions as late as assembly time
3. Pre-assign packages to specific recipients

### 4.2 Use Case: Bulk Delivery (Trays)

**Actor:** Baker
**Precondition:** Event requires FinishedUnits delivered loose
**Output Mode:** BULK_COUNT

**Main Flow:**
1. User creates event: "House Party"
2. Sets output mode: BULK_COUNT
3. Specifies requirements:
   - 100 Chocolate Chip Cookies (FinishedUnit)
   - 50 Brownies (FinishedUnit)
   - 3 Cakes (FinishedUnit)
1. System calculates production plan (recipe batches)
2. User produces items
3. User delivers on trays (no assembly required)

**Postconditions:**
- Production plan shows 100 cookies, 50 brownies, 3 cakes
- No assembly/package assembly needed
- Event fulfilled with bulk delivery

### 4.3 Use Case: Assembled Gifts

**Actor:** Baker
**Precondition:** Event requires packaged FinishedGoods
**Output Mode:** ASSEMBLED

**Main Flow:**
1. User creates event: "Christmas Client Gifts"
2. Sets output mode: ASSEMBLED
3. Specifies requirements:
   - 50 "Cookie Assortment" (FinishedGood)
     - Each contains: 6 cookies, 3 brownies
4. System explodes to FinishedUnit quantities:
   - 150 plain sugar cookies (50 x 3) (base recipe)
   - 150 decorated sugar cookies (50 × 3) (variant recipe)
   - 150 brownies (50 × 3)
1. System calculates production plan (recipe batches)
2. System checks inventory
3. System generates shopping list if needed
4. User purchases items and enters them into the app
5. User produces items
6. System checks assembly feasibility: ✅ Can assemble 50 FinishedGoods
7. User confirms assembly complete (checklist)
8. User delivers 50 FinishedGoods to clients

**Postconditions:**
- Production plan met requirements
- Assembly feasibility confirmed
- 50 FinishedGoods assembled and delivered

### 4.4 Use Case: Deferred Packaging Material Selection

**Actor:** Baker
**Precondition:** FinishedGood defined, material choice not yet made
**Trigger:** F026 deferred packaging decisions

**Main Flow:**
1. User defines FinishedGood: "Cookie Assortment"
   - Contents: 6 cookies, 3 brownies
   - Packaging material: (not selected yet)
2. User plans event requiring 50 of these FinishedGoods
3. System calculates production (300 cookies, 150 brownies)
4. User produces items
5. System checks assembly feasibility: ✅
6. **At assembly time:** User selects material:
   - Choice: Snowflake cellophane bags (not Christmas tree)
7. User assembles 50 FinishedGoods with selected material
8. User delivers FinishedGoods

**Postconditions:**
- Material choice deferred until assembly
- Flexibility maintained for creative decisions
- Assembly completed with selected materials

---

## 5. Functional Requirements

### 5.1 FinishedUnit Management

**Core Concept:** A FinishedUnit represents a specific, named yield from a single recipe (e.g., "Large Chocolate Chip Cookie"). It is the atomic unit of production.

**REQ-FG-001:** The system SHALL allow a user to define a FinishedUnit with a descriptive name and the quantity produced from a single batch of a linked recipe.
**REQ-FG-002:** Every FinishedUnit SHALL be linked to exactly one Recipe. A single Recipe can produce multiple types of FinishedUnits.
**REQ-FG-003:** The system SHALL calculate the planning cost for a single FinishedUnit by dividing the parent recipe's current cost by the yield quantity. This cost is always calculated dynamically and is not stored.
**REQ-FG-004:** The system SHALL allow users to view all FinishedUnits that can be produced from a given recipe.

### 5.2 FinishedGood Management (Definition)

**Core Concept:** A FinishedGood is a **definition** of an assembly. It describes what components (FinishedUnits or packaging materials) are needed to create a consumer-facing product, like a "Holiday Gift Box". It does not have a stored cost.

**REQ-FG-005:** The system SHALL allow a user to define a FinishedGood with a descriptive name.
**REQ-FG-006:** Each FinishedGood definition SHALL contain a list of one or more components, where each component is a specific FinishedUnit and a quantity.
**REQ-FG-007:** The system SHALL support defining FinishedGoods with mixed component types (e.g., multiple different FinishedUnits).
**REQ-FG-008:** The system SHALL allow the selection of packaging materials for a FinishedGood to be deferred.
**REQ-FG-009:** The system SHALL validate that a FinishedGood definition has at least one component and that component quantities are positive integers.

### 5.3 Package Management (Definition)

**Core Concept:** A Package is a **definition** for a logistics or gift container that holds multiple FinishedGoods and/or individual FinishedUnits.

**REQ-FG-010:** The system SHALL allow a user to define a Package with a descriptive name.
**REQ-FG-011:** Each Package definition SHALL contain a list of one or more components, where each component can be a FinishedGood or a FinishedUnit, with a specified quantity.
**REQ-FG-012:** The system SHALL allow recipient assignment for a Package to be optional.

### 5.4 Assembly Management (Instantiation)

**Core Concept:** An AssemblyRun is an **instantiation** that records the physical act of assembling a specific quantity of a FinishedGood at a specific time. This record captures costs as an immutable snapshot.

**REQ-FG-013:** The system SHALL allow a user to record an AssemblyRun for a given FinishedGood definition.
**REQ-FG-014:** When an AssemblyRun is recorded, the system SHALL capture an immutable snapshot of the total cost of all components and the calculated cost per assembled unit at that moment.
**REQ-FG-015:** The system SHALL create a consumption record for each component (FinishedUnit) used in the AssemblyRun, detailing the quantity consumed and its cost at the time of assembly.
**REQ-FG-016:** The system SHALL decrement the inventory for each FinishedUnit consumed in an AssemblyRun.
**REQ-FG-017:** The system SHALL prevent the recording of an AssemblyRun if there is insufficient inventory of any required component.

### 5.5 Output Mode Support

**REQ-FG-018:** The system SHALL support different output modes for events, including:
- **BULK_COUNT:** Requirements are specified as quantities of individual FinishedUnits.
- **ASSEMBLED:** Requirements are specified as quantities of FinishedGoods.
- **PACKAGED:** Requirements are specified as quantities of Packages.

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-FG-NFR-001:** The hierarchy (Unit → FinishedGood → Package) SHALL be intuitive to non-technical bakers.
**REQ-FG-NFR-002:** Defining the contents of a FinishedGood SHALL be a simple and clear process.
**REQ-FG-NFR-003:** The catalog view for defining FinishedGoods and Packages SHALL NOT display any cost information. Costs are only displayed for planning estimates and in historical assembly records.
**REQ-FG-NFR-004:** The status of component availability for an assembly SHALL be clearly visible to the user.

### 6.2 Data Integrity

**REQ-FG-NFR-005:** The system SHALL prevent a FinishedGood definition from being deleted if it is used in a Package or an AssemblyRun.
**REQ-FG-NFR-006:** The system SHALL prevent a FinishedUnit from being deleted if it is a component in a FinishedGood definition.
**REQ-FG-NFR-007:** The system SHALL prevent circular references (e.g., a FinishedGood cannot contain itself).

### 6.3 Flexibility

**REQ-FG-NFR-008:** The system SHALL support creating new FinishedGood and Package definitions easily without requiring schema changes.
**REQ-FG-NFR-009:** The deferral of packaging material selection SHALL not block production or assembly planning.

---

## 7. Data Model Summary

This summary describes the conceptual data entities and their relationships, not a literal database schema.

### 7.1 Core Entities

-   **FinishedUnit**: A sellable or giftable item produced by a recipe (e.g., "Large Cookie"). It has a yield quantity from its parent recipe.
-   **FinishedGood**: A definition of an assembly, composed of multiple FinishedUnits (e.g., "Cookie Assortment Box"). It is a template for what can be assembled.
-   **Package**: A definition of a larger container, composed of FinishedGoods and/or FinishedUnits (e.g., "VIP Gift Basket").
-   **AssemblyRun**: A record of an assembly event, capturing the specific FinishedGood, quantity assembled, timestamp, and an immutable cost snapshot.
-   **AssemblyConsumption**: A ledger entry detailing the exact quantity and cost of a specific FinishedUnit consumed as part of an AssemblyRun.

### 7.2 Key Relationships

-   A **Recipe** can produce many **FinishedUnits**. Each **FinishedUnit** comes from one **Recipe**.
-   A **FinishedGood** is composed of many **FinishedUnits** (via a composition table). A **FinishedUnit** can be a component in many **FinishedGoods**.
-   A **Package** can contain many **FinishedGoods** and many **FinishedUnits**.
-   An **AssemblyRun** is an instance of one **FinishedGood**.
-   An **AssemblyRun** involves many **AssemblyConsumption** records (one for each component type consumed).

---

## 8. Output Modes

### 8.1 BULK_COUNT

**Description:** Deliver FinishedUnits loose.
**Event Requirements Input:** A list of FinishedUnits and their quantities.
**Planning Calculation:** No explosion needed. Calculate recipe batches directly. No assembly required.

### 8.2 ASSEMBLED

**Description:** Deliver pre-defined FinishedGoods (assemblies).
**Event Requirements Input:** A list of FinishedGoods and their quantities.
**Planning Calculation:** Explode FinishedGoods to their component FinishedUnit quantities to determine production needs.

### 8.3 PACKAGED

**Description:** Deliver pre-defined Packages.
**Event Requirements Input:** A list of Packages and their quantities.
**Planning Calculation:** Explode Packages to FinishedGoods and FinishedUnits, then explode the contained FinishedGoods to determine total production needs.

---

## 9. Assembly Workflow

### 9.1 Assembly Decision Tiers

**Tier 1: Content Decisions (Definition Phase)**
- **What:** Define the components and quantities for FinishedGoods and Packages.
- **Must Decide:** Yes - this is required before they can be used in planning or assembly.

**Tier 2: Material Decisions (Can Defer)**
- **What:** Choose specific packaging materials (e.g., bag design, box style).
- **Can Defer:** Yes - this choice can be made at the moment of assembly.

### 9.2 Assembly Recording (Instantiation Phase)

**Purpose:** To create a permanent, costed record of an assembly event and update inventory.

**Behavior:**
1. User selects a FinishedGood definition and specifies a quantity to assemble.
2. System validates that sufficient inventory of all component FinishedUnits is available.
3. Upon confirmation, the system:
    - Creates an `AssemblyRun` record.
    - Captures the current cost of all components as an immutable cost snapshot on the `AssemblyRun`.
    - Creates `AssemblyConsumption` records for each component, decrementing `FinishedUnit` inventory.
    - Increments the inventory for the assembled `FinishedGood`.

---

## 10. Validation Rules

### 10.1 FinishedUnit Validation
- A FinishedUnit must have a name and be linked to a valid Recipe.
- Yield quantity must be a positive integer.

### 10.2 FinishedGood Validation
- A FinishedGood must have a name and at least one component.
- Component quantities must be positive integers.
- A FinishedGood cannot contain itself.

### 10.3 Package Validation
- A Package must have a name and at least one component.
- Component quantities must be positive integers.
- A Package cannot contain itself.

### 10.4 AssemblyRun Validation
- An AssemblyRun must be linked to a valid FinishedGood.
- Assembled quantity must be a positive integer.
- An AssemblyRun cannot be recorded if component inventory is insufficient.

---

## 11. Acceptance Criteria

**Must Have:**
- [ ] Ability to define FinishedUnits linked to recipes.
- [ ] Ability to define FinishedGoods composed of FinishedUnits.
- [ ] Ability to define Packages composed of FinishedGoods and FinishedUnits.
- [ ] Support for BULK_COUNT, ASSEMBLED, and PACKAGED output modes in event planning.
- [ ] Ability to record an AssemblyRun, which captures a cost snapshot and decrements component inventory.
- [ ] Prevention of assembly if components are not available in inventory.
- [ ] The UI for defining FinishedGoods and Packages (the catalog) must not show any cost information.

**Should Have:**
- [ ] Clear visual indicators of assembly feasibility (component availability).
- [ ] Clear error messages for all validation failures.
- [ ] Ability to see the historical cost of past assemblies.

---

## 12. Dependencies

### 12.1 Upstream Dependencies (Blocks This)
- ✅ Recipe system must be in place.

### 12.2 Downstream Dependencies (This Blocks)
- Event planning cost calculations.
- Production planning based on assembly needs.
- Inventory tracking for assembled goods.
- Shopping list generation.

---

## 13. Testing Requirements

### 13.1 Test Coverage

**Unit Tests:**
- Validation rules for all entities (FinishedUnit, FinishedGood, Package, AssemblyRun).
- Dynamic cost calculation for planning purposes.
- Explosion of FinishedGood and Package requirements into component quantities.

**Integration Tests:**
- Create a FinishedGood, then attempt to record an AssemblyRun with insufficient inventory (expect failure).
- Create a FinishedGood, ensure sufficient inventory, record an AssemblyRun, and verify cost snapshot and inventory decrements.
- Change an ingredient price, and verify that the planning cost for a Package changes, but the cost of a previously recorded AssemblyRun does not.

**User Acceptance Tests:**
- User can successfully define a multi-component FinishedGood.
- User can create an event using the ASSEMBLED output mode.
- User can record an assembly and see the cost snapshot and updated inventory levels.
- User is prevented from recording an assembly if they lack the parts.

---

## 14. Open Questions & Future Considerations

**Q1:** Should FinishedGoods support being components within other FinishedGoods (nesting)?
**A1:** Deferred. Initial implementation supports only FinishedUnits as components.

**Q2:** How to handle partial assembly (some quantity assembled, some pending)?
**A2:** The current scope is to record completed AssemblyRuns. Granular tracking of partial assemblies is deferred.

---

## 15. Change Log

| Version | Date       | Author    | Changes                                        |
| ------- | ---------- | --------- | ---------------------------------------------- |
| 0.1     | 2025-01-04 | Kent Gale | Initial seeded draft from planning discussions |
| 0.4     | 2026-01-09 | Gemini    | Aligned with F046 design spec. Standardized on FinishedGood terminology, clarified definition vs. instantiation pattern for costs, and updated data models. |

---

## 16. Approval & Sign-off

**Document Owner:** Kent Gale
**Last Review Date:** 2026-01-09
**Next Review Date:** TBD
**Status:** 📝 DRAFT

---

## 17. Related Documents

- **Design Specs:** `docs/func-spec/F046_finished_goods_bundles_assembly.md`
- **Requirements:** `req_recipes.md` (recipe → FinishedUnit linkage)
- **Requirements:** `req_planning.md` (event planning with finished goods)

---

**END OF REQUIREMENTS DOCUMENT**
