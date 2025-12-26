---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "FK Resolver Service"
phase: "Phase 2 - Import Services"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "65041"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - FK Resolver Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create shared FK resolution logic with create/map/skip options for CLI and UI.

**Success Criteria**:
1. ResolutionChoice enum with CREATE, MAP, SKIP values
2. MissingFK and Resolution dataclasses capture resolution context
3. FKResolverCallback protocol enables pluggable resolution strategies
4. Entity creation works for Supplier, Ingredient, Product
5. Fuzzy search finds close matches for "map to existing"
6. Unit tests achieve >70% coverage

## Context & Constraints

**Owner**: Claude (Track B - Import)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-016 through FR-021
- `kitty-specs/030-enhanced-export-import/data-model.md`: FKResolver Protocol
- `src/services/catalog_import_service.py`: Session=None pattern
- `CLAUDE.md`: Session management warnings

**Constraints**:
- MUST use session=None pattern for transactional composition
- MUST follow dependency order: Supplier/Ingredient before Product
- MUST validate required fields before entity creation

## Subtasks & Detailed Guidance

### Subtask T016 - Create Resolution dataclasses

**Purpose**: Define data structures for FK resolution.

**Steps**:
1. Create `src/services/fk_resolver_service.py`
2. Add imports: `dataclasses`, `enum`, `typing`, `Protocol`
3. Define `ResolutionChoice` enum:
   ```python
   class ResolutionChoice(str, Enum):
       CREATE = "create"
       MAP = "map"
       SKIP = "skip"
   ```
4. Define `MissingFK` dataclass:
   ```python
   @dataclass
   class MissingFK:
       entity_type: str  # "supplier", "ingredient", "product"
       missing_value: str  # The slug/name that wasn't found
       field_name: str  # e.g., "supplier_name", "ingredient_slug"
       affected_record_count: int
       sample_records: List[Dict]  # First 3 affected records for context
   ```
5. Define `Resolution` dataclass:
   ```python
   @dataclass
   class Resolution:
       choice: ResolutionChoice
       entity_type: str
       missing_value: str
       mapped_id: Optional[int] = None  # For MAP choice
       created_entity: Optional[Dict] = None  # For CREATE choice
   ```

**Files**: `src/services/fk_resolver_service.py`
**Parallel?**: No (foundation)

### Subtask T017 - Define FKResolverCallback protocol

**Purpose**: Enable pluggable resolution strategies for CLI and UI.

**Steps**:
1. Define protocol using typing.Protocol:
   ```python
   class FKResolverCallback(Protocol):
       def resolve(self, missing: MissingFK) -> Resolution:
           """Called for each missing FK. Returns user's resolution choice."""
           ...
   ```
2. Document that CLI will implement with text prompts
3. Document that UI will implement with dialog

**Files**: `src/services/fk_resolver_service.py`
**Parallel?**: No (depends on T016)

### Subtask T018 - Implement resolve_missing_fks core logic

**Purpose**: Main resolution orchestration with dependency ordering.

**Steps**:
1. Implement main function:
   ```python
   def resolve_missing_fks(
       missing_fks: List[MissingFK],
       resolver: FKResolverCallback,
       session: Session = None
   ) -> Tuple[Dict[str, Dict[str, int]], List[Resolution]]:
       """
       Resolve missing FKs in dependency order.

       Returns:
           - mapping: {entity_type: {missing_value: resolved_id}}
           - resolutions: List of all Resolution objects made
       """
   ```
2. Sort missing_fks by dependency order:
   - Suppliers first (no dependencies)
   - Ingredients second (no dependencies)
   - Products last (depends on ingredients)
3. For each missing FK:
   - Call resolver.resolve(missing)
   - Handle CREATE: create entity, store ID in mapping
   - Handle MAP: store mapped_id in mapping
   - Handle SKIP: mark as skipped (no mapping entry)
4. Return mapping and resolutions for logging

**Files**: `src/services/fk_resolver_service.py`
**Parallel?**: No

### Subtask T019 - Implement entity creation support

**Purpose**: Create new entities during import resolution.

**Steps**:
1. Implement `_create_supplier(data: Dict, session: Session) -> int`
   - Required fields: name, city, state, zip
   - Return created supplier.id
2. Implement `_create_ingredient(data: Dict, session: Session) -> int`
   - Required fields: slug, display_name, category
   - Return created ingredient.id
3. Implement `_create_product(data: Dict, session: Session) -> int`
   - Required fields: ingredient_id, package_unit, package_unit_quantity
   - Resolve ingredient_id from ingredient_slug if needed
   - Return created product.id
4. Validate required fields before creation, raise ValidationError if missing

**Files**: `src/services/fk_resolver_service.py`
**Parallel?**: Yes (independent of T020)

### Subtask T020 - Implement fuzzy search for mapping

**Purpose**: Find close matches for "map to existing" option.

**Steps**:
1. Implement `find_similar_entities(entity_type: str, search_value: str, session: Session, limit: int = 5) -> List[Dict]`:
   ```python
   def find_similar_entities(entity_type: str, search_value: str, session: Session, limit: int = 5) -> List[Dict]:
       """Find entities with similar names for mapping."""
       search_lower = search_value.lower()

       if entity_type == "supplier":
           matches = session.query(Supplier).filter(
               Supplier.name.ilike(f"%{search_lower}%")
           ).limit(limit).all()
           return [{"id": s.id, "name": s.name, "city": s.city} for s in matches]
       # Similar for ingredient, product
   ```
2. Return list of potential matches with id and display fields
3. Use case-insensitive substring matching initially

**Files**: `src/services/fk_resolver_service.py`
**Parallel?**: Yes (independent of T019)

### Subtask T021 - Write unit tests

**Purpose**: Verify FK resolution functionality.

**Steps**:
1. Create `src/tests/services/test_fk_resolver.py`
2. Test cases:
   - CREATE resolution creates entity and returns ID
   - MAP resolution returns mapped_id
   - SKIP resolution excludes from mapping
   - Dependency ordering (suppliers before products)
   - find_similar_entities returns close matches
   - Validation error on missing required fields
3. Mock resolver callback for testing

**Files**: `src/tests/services/test_fk_resolver.py`
**Parallel?**: No (after implementation)

## Test Strategy

- Unit tests for each resolution path
- Mock FKResolverCallback for controlled testing
- Test dependency ordering explicitly

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow session=None pattern strictly |
| Incomplete entity creation | Validate required fields before create |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] ResolutionChoice, MissingFK, Resolution dataclasses work
- [ ] FKResolverCallback protocol defined
- [ ] resolve_missing_fks handles all three resolution types
- [ ] Entity creation works for Supplier, Ingredient, Product
- [ ] Fuzzy search returns similar entities
- [ ] >70% test coverage on service
- [ ] tasks.md updated with status change

## Review Guidance

- Verify session=None pattern used throughout
- Verify dependency ordering logic
- Verify required field validation before entity creation
- Verify fuzzy search is case-insensitive

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T02:26:57Z – claude – shell_pid=65041 – lane=doing – Started implementation
- 2025-12-26T02:35:40Z – claude – shell_pid=65041 – lane=for_review – Moved to for_review
- 2025-12-26T03:36:12Z – claude – shell_pid=65041 – lane=done – Code review passed: All 32 tests pass, session=None pattern correct, dependency ordering implemented
