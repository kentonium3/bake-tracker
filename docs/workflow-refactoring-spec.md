📐 Production and Inventory Refactoring Specification
Status: Early User Testing Phase (Desktop) Constitutional Goal: Assess existing architecture against Principles III (Future-Proof Schema) and VII (Pragmatic Aspiration). Identify gaps to prepare for the Near-Term Evolution (Web Migration) phase. UI/UX Directive: The architectural terms (e.g., BOM, FG Assembly) MUST remain in the service/data layers. The UI layer will use user-centric language (e.g., "My Pantry," "Making a Batch," "Creating Gift Packages").

1. 🌐 Conceptual Flow Diagram (Mermaid Graph)
This graph illustrates the desired operational flow, emphasizing how inventory moves between stock types and how packaging materials are consumed.

Code snippet

graph TD
    subgraph Input & Definition
        A[INGREDIENT]
        B[PACKAGING_PRODUCT]
        C[RECIPE]
    end

    subgraph Inventory
        D[PANTRY (Raw Material Stock)]
        E[FINISHED_ITEM_INV (Atomic Stock)]
        F[FINISHED_GOOD_INV (Sellable Stock)]
    end

    subgraph Production Processes
        G(BATCH RUN - Process 1)
        H(FG ASSEMBLY - Process 2)
        I(PACKAGE ASSEMBLY - Process 3)
    end

    subgraph Output
        J[PACKAGE (Final Logistics Unit)]
    end

    %% Definition Flow
    C -- calls for --> A

    %% Input Flow
    A & B --> D

    %% Consumption/Production 1: Batch Run
    G -- consumes ingredients --> D
    G -- yields --> E

    %% Consumption/Production 2: Finished Good Assembly (Intermediate Inventory)
    H -- consumes atomic items --> E
    H -- consumes packaging (BOM 1) --> B
    H -- yields --> F

    %% Consumption/Production 3: Package Assembly (Final Order)
    I -- consumes assembled goods --> F
    I -- consumes packaging (BOM 2) --> B
    I -- yields --> J

    style A fill:#F9E79F,stroke:#000
    style B fill:#F9E79F,stroke:#000
    style C fill:#D6EAF8,stroke:#000
    style D fill:#A9DFBF,stroke:#000
    style E fill:#A9DFBF,stroke:#000
    style F fill:#A9DFBF,stroke:#000
2. 🗃️ Entity Relationship Diagram (ERD)
This diagram focuses on the database model and the relationships, specifically introducing the Bill of Materials (BOM) concept.

Code snippet

erDiagram
    %% DEFINITIONS
    RECIPE ||--o{ RECIPE_INGREDIENT : calls_for
    INGREDIENT ||--o{ PRODUCT : implemented_by
    PRODUCT ||--o{ INVENTORY_STOCK : tracked_in

    %% NEW ENTITY FOR PACKAGING MATERIALS
    PACKAGING_PRODUCT ||--o{ INVENTORY_STOCK : tracked_in

    %% PRODUCTION
    BATCH ||--|{ INVENTORY_STOCK : consumes_raw
    BATCH ||--|{ FINISHED_ITEM : yields_atomic_unit

    %% INTERMEDIATE INVENTORY & BOM 1 (Finished Good)
    FINISHED_GOOD ||--|{ FG_BOM_LINE : requires_materials
    FG_BOM_LINE }|--|| FINISHED_ITEM : requires_item
    FG_BOM_LINE }|--o{ PACKAGING_PRODUCT : requires_packaging_1

    FINISHED_GOOD ||--o{ FINISHED_GOOD_STOCK : tracked_in

    %% FINAL ASSEMBLY & BOM 2 (Package)
    PACKAGE ||--|{ PKG_BOM_LINE : requires_materials
    PKG_BOM_LINE }|--o{ FINISHED_GOOD : requires_assembled_good
    PKG_BOM_LINE }|--o{ PACKAGING_PRODUCT : requires_packaging_2

    %% INVENTORY NOTE: INVENTORY_STOCK tracks all raw/packaging items.
3. 📦 Core Concepts & Requirements
A. Introduction of Packaging Products
Concept: A new entity, PACKAGING_PRODUCT, must be defined.

Requirement: These items must be tracked in the Raw Material Stock (PANTRY) alongside food ingredients.

B. Bill of Materials (BOM)
Concept: The BOM structure defines the required components for assembling a composite item.

Requirement 1: Finished Good BOM (FG_BOM): Defines which Finished Items and which Packaging Products are consumed to create one unit of a Finished Good.

Requirement 2: Package BOM (PKG_BOM): Defines which assembled Finished Goods and which Packaging Products are consumed to create one Package.

C. Inventory Separation
The system requires three distinct inventory tracking tables/services:

INVENTORY_STOCK (Raw/Packaging): Tracks PRODUCT (raw ingredients) and PACKAGING_PRODUCT inventory.

FINISHED_ITEM_STOCK (Atomic): Tracks individual items yielded by a BATCH (e.g., single cookies, single cakes).

FINISHED_GOOD_STOCK (Assembled): Tracks ready-to-sell, assembled units that are pulled for packaging (e.g., bags of cookies, complete cakes).

4. 📝 Assessment Task for Claude
Review the two Mermaid diagrams and the Core Concepts above, and compare them against the existing schema and services. Consult the attached constitution.md to ensure the proposed architecture is aligned with Principle V (Layered Architecture Discipline).

Your response should be structured to explicitly identify the gaps in three categories:

Schema Gaps (DB): Which entities or required relationships (especially the two BOM tables and the three inventory tables) are missing or incorrectly modeled in the existing schema?

Service/Logic Gaps: Which services need to be built or refactored (e.g., the service that performs consumption based on the BOM, or the inventory calculation service)?

UI Gaps (Focusing on Desktop to Web Transition): What new UI components or screens will be required to manage the new entities (PACKAGING_PRODUCT) and processes (FG ASSEMBLY, Package BOM definition), keeping in mind that the eventual web migration requires clean separation of UI from Services?
