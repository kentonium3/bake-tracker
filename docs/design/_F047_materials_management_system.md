# Feature Specification: Materials Management System

**Feature ID**: F047
**Feature Name**: Materials Management System (Packaging Materials Foundation)
**Priority**: High
**Estimated Complexity**: 28-32 hours
**Dependencies**: F046 (Finished Goods, Bundles & Assembly Tracking)
**Enables**: F048 (Shopping Lists), F049 (Assembly Workflows Enhancement)
**Requirements Document**: docs/requirements/req_materials.md v2.1

---

## Executive Summary

Implement a comprehensive materials management system that parallels the existing ingredient management system, enabling proper handling of non-edible materials (ribbon, boxes, bags, tissue, etc.) used in baking assemblies. This feature establishes foundational extensibility architecture for multi-user web version and potential e-commerce integration.

**Key Capabilities:**
- Materials ontology (3-level hierarchy: Category → Subcategory → Material → Product)
- MaterialUnit model (atomic consumption units, parallel to FinishedUnit)
- Purchasing workflow with weighted average costing
- Aggregate inventory tracking
- Flexible material assignment timing (F026 deferred decision pattern)
- Complete identity snapshot capture for historical reconstruction
- Integration with FinishedGood composition and AssemblyRun workflows

---

## Problem Statement

**Current State:**
- Materials incorrectly modeled as Ingredients (temporary workaround)
- Cannot properly track packaging materials with appropriate metadata
- Pollutes ingredient model with non-food items
- Blocks complete FinishedGood assemblies (cannot add ribbon/boxes)
- No support for deferred material decisions during production workflow

**Required State:**
- Separate materials ontology and product catalog
- Materials purchasing, inventory, and consumption workflows
- Materials integrated into assembly cost calculations
- Materials work alongside ingredients in all observability/reporting
- Flexible material decision timing (catalog or assembly stage)
- Complete identity capture for "what did I make" historical queries

---

## Architecture Overview

### Data Model (8 New Models)

```
MaterialCategory (Level 1)
  ↓
MaterialSubcategory (Level 2)
  ↓
Material (Level 3 - Abstract)
  ↓
MaterialProduct (Physical - Purchasable)
  
MaterialUnit (Atomic consumption unit)

MaterialPurchase (Purchasing transactions)
MaterialConsumption (Assembly consumption with identity snapshots)

AssemblyRun (Enhanced with material costs)
```

### Definition/Instantiation Pattern

**Definition Layer (Catalog - NO stored costs):**
- Material, MaterialProduct, MaterialUnit
- MaterialProduct.current_unit_cost (weighted average, recalculated)
- Costs calculated dynamically

**Instantiation Layer (Transactional - Immutable snapshots):**
- MaterialPurchase (cost + identity snapshot)
- MaterialConsumption (cost + identity snapshot)
- AssemblyRun (aggregate costs)

### Integration Points

1. **Composition Table**: Enhanced to support Material (generic placeholder)
2. **FinishedGood**: Can include MaterialUnits or Material placeholders
3. **AssemblyRun**: Enhanced with material costs and reconciliation flag
4. **Event Planning**: Shows estimated/actual material costs
5. **Import/Export**: Materials catalog and view data

---

## Detailed Design

### 3.1 Data Models

#### MaterialCategory

```python
class MaterialCategory(BaseModel):
    """Top-level material categorization"""
    __tablename__ = 'material_categories'
    
    id: int = Column(Integer, primary_key=True)
    display_name: str = Column(String(100), nullable=False, unique=True)
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Relationships
    subcategories: List['MaterialSubcategory'] = relationship(
        'MaterialSubcategory',
        back_populates='category',
        cascade='all, delete-orphan'
    )
```

**Examples**: "Ribbons", "Boxes", "Tissue Paper", "Bags"

#### MaterialSubcategory

```python
class MaterialSubcategory(BaseModel):
    """Second-level material categorization"""
    __tablename__ = 'material_subcategories'
    
    id: int = Column(Integer, primary_key=True)
    category_id: int = Column(Integer, ForeignKey('material_categories.id'), nullable=False)
    display_name: str = Column(String(100), nullable=False)
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Unique per category
    __table_args__ = (
        UniqueConstraint('category_id', 'display_name'),
    )
    
    # Relationships
    category: 'MaterialCategory' = relationship('MaterialCategory', back_populates='subcategories')
    materials: List['Material'] = relationship(
        'Material',
        back_populates='subcategory',
        cascade='all, delete-orphan'
    )
```

**Examples**: "Satin Ribbon", "Grosgrain Ribbon", "Gift Boxes", "Cellophane Bags"

#### Material

```python
class Material(BaseModel):
    """Abstract material definition (third level)"""
    __tablename__ = 'materials'
    
    id: int = Column(Integer, primary_key=True)
    subcategory_id: int = Column(Integer, ForeignKey('material_subcategories.id'), nullable=False)
    display_name: str = Column(String(200), nullable=False)
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Unique per subcategory
    __table_args__ = (
        UniqueConstraint('subcategory_id', 'display_name'),
    )
    
    # Relationships
    subcategory: 'MaterialSubcategory' = relationship('MaterialSubcategory', back_populates='materials')
    products: List['MaterialProduct'] = relationship(
        'MaterialProduct',
        back_populates='material',
        cascade='all, delete-orphan'
    )
    material_units: List['MaterialUnit'] = relationship(
        'MaterialUnit',
        back_populates='material'
    )
    
    # For Composition table (generic placeholder)
    compositions: List['Composition'] = relationship(
        'Composition',
        back_populates='material',
        foreign_keys='Composition.material_id'
    )
```

**Examples**: "Red Satin Ribbon", "Small Gift Box 6x6x3", "6\" Cellophane Bag"

#### MaterialProduct

```python
class MaterialProduct(BaseModel):
    """Physical purchasable material product"""
    __tablename__ = 'material_products'
    
    id: int = Column(Integer, primary_key=True)
    material_id: int = Column(Integer, ForeignKey('materials.id'), nullable=False)
    display_name: str = Column(String(200), nullable=False, unique=True)
    default_unit: str = Column(String(50), nullable=False)  # 'each', 'linear_inches', 'square_feet'
    inventory_count: Decimal = Column(Numeric(10, 3), nullable=False, default=Decimal('0.0'))
    current_unit_cost: Decimal = Column(Numeric(10, 4), nullable=True)  # Weighted average
    supplier_id: int = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Constraints
    __table_args__ = (
        CheckConstraint('inventory_count >= 0', name='material_product_inventory_non_negative'),
        CheckConstraint('current_unit_cost >= 0', name='material_product_cost_non_negative'),
        CheckConstraint("default_unit IN ('each', 'linear_inches', 'square_feet')", name='material_product_valid_unit'),
    )
    
    # Relationships
    material: 'Material' = relationship('Material', back_populates='products')
    supplier: 'Supplier' = relationship('Supplier', back_populates='material_products')
    purchases: List['MaterialPurchase'] = relationship(
        'MaterialPurchase',
        back_populates='material_product',
        order_by='MaterialPurchase.purchased_at.desc()'
    )
    material_units: List['MaterialUnit'] = relationship(
        'MaterialUnit',
        back_populates='material_product'
    )
```

**Examples**: "Michaels Red Satin 100ft Roll", "Amazon 6x6x3 White Box 50pk"

**Key Points:**
- Inventory tracked at MaterialProduct level (NOT Material level)
- current_unit_cost is weighted average (recalculated on each purchase)
- Shared Supplier table with ingredients

#### MaterialUnit

```python
class MaterialUnit(BaseModel):
    """Atomic material consumption unit (parallel to FinishedUnit)"""
    __tablename__ = 'material_units'
    
    id: int = Column(Integer, primary_key=True)
    material_id: int = Column(Integer, ForeignKey('materials.id'), nullable=False)
    display_name: str = Column(String(200), nullable=False, unique=True)
    quantity_per_unit: Decimal = Column(Numeric(10, 3), nullable=False)
    unit_type: str = Column(String(50), nullable=False)  # 'each', 'linear_inches'
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # NO material_product_id - MaterialUnit is a DEFINITION
    # Specific MaterialProduct selected at consumption time (assembly)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity_per_unit > 0', name='material_unit_quantity_positive'),
        CheckConstraint("unit_type IN ('each', 'linear_inches', 'square_feet')", name='material_unit_valid_type'),
    )
    
    # Relationships
    material: 'Material' = relationship('Material', back_populates='material_units')
    compositions: List['Composition'] = relationship(
        'Composition',
        back_populates='material_unit',
        foreign_keys='Composition.material_unit_id'
    )
    consumptions: List['MaterialConsumption'] = relationship(
        'MaterialConsumption',
        back_populates='material_unit'
    )
    
    def calculate_available_inventory(self) -> Decimal:
        """Calculate available units by aggregating MaterialProduct inventories"""
        total_material_inventory = sum(
            product.inventory_count 
            for product in self.material.products
        )
        return total_material_inventory / self.quantity_per_unit
```

**Examples**: "6\" Red Ribbon", "6\" Cellophane Bag", "Small Gift Box"

**Key Design Decision**: MaterialUnit has NO material_product_id
- MaterialUnit is a DEFINITION (how much material per unit)
- Specific MaterialProduct selection deferred until assembly time
- Supports F026 deferred decision pattern

#### MaterialPurchase

```python
class MaterialPurchase(BaseModel):
    """Material purchase transaction with package-level tracking"""
    __tablename__ = 'material_purchases'
    
    id: int = Column(Integer, primary_key=True)
    material_product_id: int = Column(Integer, ForeignKey('material_products.id'), nullable=False)
    package_unit_count: Decimal = Column(Numeric(10, 3), nullable=False)  # e.g., 25 bags per pack
    packages_purchased: Decimal = Column(Numeric(10, 3), nullable=False)  # e.g., 4 packs
    total_units: Decimal = Column(Numeric(10, 3), nullable=False)  # Calculated: 25 × 4 = 100
    calculated_unit_cost: Decimal = Column(Numeric(10, 4), nullable=False)  # Immutable snapshot
    total_cost: Decimal = Column(Numeric(10, 2), nullable=False)
    purchased_at: DateTime = Column(DateTime, nullable=False)
    supplier_id: int = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Constraints
    __table_args__ = (
        CheckConstraint('package_unit_count > 0', name='material_purchase_package_count_positive'),
        CheckConstraint('packages_purchased > 0', name='material_purchase_packages_positive'),
        CheckConstraint('total_units > 0', name='material_purchase_total_units_positive'),
        CheckConstraint('total_cost >= 0', name='material_purchase_cost_non_negative'),
        CheckConstraint('calculated_unit_cost >= 0', name='material_purchase_unit_cost_non_negative'),
    )
    
    # Relationships
    material_product: 'MaterialProduct' = relationship('MaterialProduct', back_populates='purchases')
    supplier: 'Supplier' = relationship('Supplier', back_populates='material_purchases')
```

**Purchase Workflow:**
1. User enters: package_unit_count (25), packages_purchased (4), total_cost ($40)
2. System calculates: total_units (100), calculated_unit_cost ($0.40)
3. System updates: MaterialProduct.inventory_count (+100)
4. System recalculates: MaterialProduct.current_unit_cost (weighted average)

**Cost Snapshot**: calculated_unit_cost is IMMUTABLE (historical record)

#### MaterialConsumption

```python
class MaterialConsumption(BaseModel):
    """Material consumption in assembly with complete identity snapshot"""
    __tablename__ = 'material_consumption'
    
    id: int = Column(Integer, primary_key=True)
    assembly_run_id: int = Column(Integer, ForeignKey('assembly_runs.id'), nullable=False)
    
    # IDENTITY CAPTURE (immutable snapshot)
    material_id: int = Column(Integer, ForeignKey('materials.id'), nullable=False)
    material_product_id: int = Column(Integer, ForeignKey('material_products.id'), nullable=False)
    quantity_per_unit: Decimal = Column(Numeric(10, 3), nullable=False)
    display_name_snapshot: str = Column(String(200), nullable=False)
    
    # QUANTITY
    quantity_consumed: Decimal = Column(Numeric(10, 3), nullable=False)
    
    # COST SNAPSHOT (immutable)
    per_unit_cost: Decimal = Column(Numeric(10, 4), nullable=False)
    
    created_at: DateTime
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity_per_unit > 0', name='material_consumption_quantity_per_unit_positive'),
        CheckConstraint('quantity_consumed > 0', name='material_consumption_quantity_positive'),
        CheckConstraint('per_unit_cost >= 0', name='material_consumption_cost_non_negative'),
    )
    
    # Relationships
    assembly_run: 'AssemblyRun' = relationship('AssemblyRun', back_populates='material_consumptions')
    material: 'Material' = relationship('Material')
    material_product: 'MaterialProduct' = relationship('MaterialProduct')
```

**Identity Snapshot Fields:**
- `material_id`: Material type (enables "what type of material")
- `material_product_id`: Specific product (enables "which design/brand")
- `quantity_per_unit`: Unit size (enables "what size was it")
- `display_name_snapshot`: Human-readable name (enables "what was it called then")

**Historical Reconstruction:**
User can query 2 years later: "What materials did I use in AssemblyRun #15?"
- Answer includes: material type, specific product, size, name (as it was called then), quantity, cost
- No catalog dependency - all identity preserved in snapshot

#### Enhanced Composition Model

```python
class Composition(BaseModel):
    """Component of a FinishedGood (food OR material)"""
    __tablename__ = 'compositions'
    
    id: int = Column(Integer, primary_key=True)
    finished_good_id: int = Column(Integer, ForeignKey('finished_goods.id'), nullable=False)
    
    # Polymorphic component (EXACTLY ONE must be set)
    finished_unit_id: int = Column(Integer, ForeignKey('finished_units.id'), nullable=True)
    material_unit_id: int = Column(Integer, ForeignKey('material_units.id'), nullable=True)
    material_id: int = Column(Integer, ForeignKey('materials.id'), nullable=True)  # Generic placeholder
    
    quantity: int = Column(Integer, nullable=False)
    created_at: DateTime
    updated_at: DateTime
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='composition_quantity_positive'),
        CheckConstraint(
            '(finished_unit_id IS NOT NULL AND material_unit_id IS NULL AND material_id IS NULL) OR '
            '(finished_unit_id IS NULL AND material_unit_id IS NOT NULL AND material_id IS NULL) OR '
            '(finished_unit_id IS NULL AND material_unit_id IS NULL AND material_id IS NOT NULL)',
            name='composition_exactly_one_component'
        ),
    )
    
    # Relationships
    finished_good: 'FinishedGood' = relationship('FinishedGood', back_populates='compositions')
    finished_unit: 'FinishedUnit' = relationship('FinishedUnit', back_populates='compositions')
    material_unit: 'MaterialUnit' = relationship('MaterialUnit', back_populates='compositions')
    material: 'Material' = relationship('Material', back_populates='compositions')  # Generic placeholder
```

**Three Specification Levels:**
1. **finished_unit_id**: Specific baked good (food component)
2. **material_unit_id**: Specific material (material choice made)
3. **material_id**: Generic material (material choice deferred - F026 pattern)

#### Enhanced AssemblyRun Model

```python
class AssemblyRun(BaseModel):
    """Assembly execution with material costs and reconciliation tracking"""
    __tablename__ = 'assembly_runs'
    
    id: int = Column(Integer, primary_key=True)
    finished_good_id: int = Column(Integer, ForeignKey('finished_goods.id'), nullable=False)
    quantity_assembled: int = Column(Integer, nullable=False)
    assembled_at: DateTime = Column(DateTime, nullable=False)
    
    # Cost tracking
    total_component_cost: Decimal = Column(Numeric(10, 2), nullable=False)  # FinishedUnit costs
    per_assembly_cost: Decimal = Column(Numeric(10, 4), nullable=False)  # Components only (legacy)
    
    total_material_cost: Decimal = Column(Numeric(10, 2), nullable=False, default=Decimal('0.0'))  # NEW
    total_assembly_cost: Decimal = Column(Numeric(10, 2), nullable=False)  # Components + materials
    per_unit_assembly_cost: Decimal = Column(Numeric(10, 4), nullable=False)  # Total per unit
    
    # Deferred decision tracking
    requires_material_reconciliation: bool = Column(Boolean, nullable=False, default=False)  # NEW
    
    notes: str = Column(Text, nullable=True)
    created_at: DateTime
    updated_at: DateTime
    
    # Relationships
    finished_good: 'FinishedGood' = relationship('FinishedGood', back_populates='assembly_runs')
    assembly_consumptions: List['AssemblyConsumption'] = relationship(
        'AssemblyConsumption',
        back_populates='assembly_run',
        cascade='all, delete-orphan'
    )
    material_consumptions: List['MaterialConsumption'] = relationship(  # NEW
        'MaterialConsumption',
        back_populates='assembly_run',
        cascade='all, delete-orphan'
    )
```

**New Fields:**
- `total_material_cost`: Sum of material costs
- `total_assembly_cost`: total_component_cost + total_material_cost
- `per_unit_assembly_cost`: total_assembly_cost / quantity_assembled
- `requires_material_reconciliation`: True if "Record Anyway" bypass used

---

### 3.2 Service Layer

#### MaterialCategoryService

```python
class MaterialCategoryService:
    """Manage material categories"""
    
    def create_category(self, display_name: str, notes: str = None) -> MaterialCategory:
        """Create new material category"""
        
    def list_categories(self) -> List[MaterialCategory]:
        """List all categories with subcategory counts"""
        
    def update_category(self, category_id: int, display_name: str = None, notes: str = None) -> MaterialCategory:
        """Update category"""
        
    def delete_category(self, category_id: int) -> None:
        """Delete category (cascade to subcategories/materials/products)"""
        # Validation: Cannot delete if has products with inventory > 0
```

#### MaterialSubcategoryService

```python
class MaterialSubcategoryService:
    """Manage material subcategories"""
    
    def create_subcategory(self, category_id: int, display_name: str, notes: str = None) -> MaterialSubcategory:
        """Create new subcategory within category"""
        
    def list_subcategories(self, category_id: int = None) -> List[MaterialSubcategory]:
        """List subcategories (optionally filtered by category)"""
        
    def update_subcategory(self, subcategory_id: int, display_name: str = None, notes: str = None) -> MaterialSubcategory:
        """Update subcategory"""
        
    def delete_subcategory(self, subcategory_id: int) -> None:
        """Delete subcategory (cascade to materials/products)"""
        # Validation: Cannot delete if has products with inventory > 0
```

#### MaterialService

```python
class MaterialService:
    """Manage materials (abstract definitions)"""
    
    def create_material(self, subcategory_id: int, display_name: str, notes: str = None) -> Material:
        """Create new material"""
        
    def list_materials(self, subcategory_id: int = None, search: str = None) -> List[Material]:
        """List materials with product counts and aggregate inventory"""
        # Returns: [(material, product_count, total_inventory)]
        
    def get_material_with_products(self, material_id: int) -> Tuple[Material, List[MaterialProduct]]:
        """Get material with all its products"""
        
    def calculate_aggregate_inventory(self, material_id: int) -> Decimal:
        """Calculate total inventory across all MaterialProducts"""
        return sum(product.inventory_count for product in material.products)
    
    def calculate_weighted_average_cost(self, material_id: int) -> Decimal:
        """Calculate weighted average cost across all MaterialProducts"""
        total_value = sum(
            product.inventory_count * product.current_unit_cost
            for product in material.products
            if product.current_unit_cost
        )
        total_inventory = self.calculate_aggregate_inventory(material_id)
        return total_value / total_inventory if total_inventory > 0 else Decimal('0.0')
    
    def update_material(self, material_id: int, display_name: str = None, notes: str = None) -> Material:
        """Update material"""
        
    def delete_material(self, material_id: int) -> None:
        """Delete material"""
        # Validation: Cannot delete if:
        #   - Has products with inventory > 0
        #   - Used in MaterialUnit
        #   - Used in Composition as placeholder
```

#### MaterialProductService

```python
class MaterialProductService:
    """Manage material products (purchasable items)"""
    
    def create_product(
        self,
        material_id: int,
        display_name: str,
        default_unit: str,
        supplier_id: int = None,
        notes: str = None
    ) -> MaterialProduct:
        """Create new material product"""
        # Validation: default_unit in ('each', 'linear_inches', 'square_feet')
        
    def list_products(
        self,
        material_id: int = None,
        supplier_id: int = None,
        search: str = None
    ) -> List[MaterialProduct]:
        """List products with inventory and cost info"""
        
    def get_product_with_purchase_history(
        self,
        product_id: int
    ) -> Tuple[MaterialProduct, List[MaterialPurchase]]:
        """Get product with purchase history"""
        
    def update_product(
        self,
        product_id: int,
        display_name: str = None,
        default_unit: str = None,
        supplier_id: int = None,
        notes: str = None
    ) -> MaterialProduct:
        """Update product"""
        # Note: Cannot change default_unit if MaterialUnit exists referencing this product
        
    def adjust_inventory(
        self,
        product_id: int,
        adjustment_type: str,  # 'count' or 'percentage'
        adjustment_value: Decimal,
        notes: str = None
    ) -> MaterialProduct:
        """Manual inventory adjustment"""
        # For 'count': inventory_count += adjustment_value
        # For 'percentage': inventory_count = inventory_count * adjustment_value
        
    def delete_product(self, product_id: int) -> None:
        """Delete product"""
        # Validation: Cannot delete if:
        #   - inventory_count > 0
        #   - Used in MaterialUnit
        #   - Used in MaterialConsumption
```

#### MaterialPurchaseService

```python
class MaterialPurchaseService:
    """Manage material purchases"""
    
    def record_purchase(
        self,
        material_product_id: int,
        package_unit_count: Decimal,
        packages_purchased: Decimal,
        total_cost: Decimal,
        purchased_at: datetime,
        supplier_id: int = None,
        notes: str = None
    ) -> MaterialPurchase:
        """Record material purchase and update inventory"""
        
        # 1. Calculate total_units
        total_units = package_unit_count * packages_purchased
        
        # 2. Calculate unit cost
        calculated_unit_cost = total_cost / total_units
        
        # 3. Create MaterialPurchase record (immutable snapshot)
        purchase = MaterialPurchase(
            material_product_id=material_product_id,
            package_unit_count=package_unit_count,
            packages_purchased=packages_purchased,
            total_units=total_units,
            calculated_unit_cost=calculated_unit_cost,
            total_cost=total_cost,
            purchased_at=purchased_at,
            supplier_id=supplier_id,
            notes=notes
        )
        
        # 4. Update MaterialProduct inventory
        product = self.get_product(material_product_id)
        old_inventory = product.inventory_count
        old_cost = product.current_unit_cost or Decimal('0.0')
        
        new_inventory = old_inventory + total_units
        
        # 5. Recalculate weighted average cost
        new_weighted_avg = (
            (old_inventory * old_cost) + (total_units * calculated_unit_cost)
        ) / new_inventory
        
        product.inventory_count = new_inventory
        product.current_unit_cost = new_weighted_avg
        
        return purchase
    
    def list_purchases(
        self,
        material_product_id: int = None,
        supplier_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[MaterialPurchase]:
        """List purchases with filters"""
        
    def get_purchase(self, purchase_id: int) -> MaterialPurchase:
        """Get purchase details"""
```

**Key Points:**
- Purchase creates immutable cost snapshot (calculated_unit_cost)
- MaterialProduct.current_unit_cost recalculated as weighted average
- Inventory updated atomically with purchase

#### MaterialUnitService

```python
class MaterialUnitService:
    """Manage material units (atomic consumption units)"""
    
    def create_unit(
        self,
        material_id: int,
        display_name: str,
        quantity_per_unit: Decimal,
        unit_type: str,
        notes: str = None
    ) -> MaterialUnit:
        """Create new material unit"""
        # Validation: unit_type in ('each', 'linear_inches', 'square_feet')
        # Validation: quantity_per_unit > 0
        
    def list_units(
        self,
        material_id: int = None,
        search: str = None
    ) -> List[Tuple[MaterialUnit, Decimal]]:
        """List units with available inventory"""
        # Returns: [(unit, available_inventory)]
        # available_inventory = calculate_available_inventory()
        
    def calculate_available_inventory(self, unit_id: int) -> Decimal:
        """Calculate available units from MaterialProduct inventories"""
        unit = self.get_unit(unit_id)
        total_material_inventory = sum(
            product.inventory_count 
            for product in unit.material.products
        )
        return total_material_inventory / unit.quantity_per_unit
    
    def calculate_current_cost(self, unit_id: int) -> Decimal:
        """Calculate current cost using weighted average across MaterialProducts"""
        unit = self.get_unit(unit_id)
        material_service = MaterialService()
        weighted_avg = material_service.calculate_weighted_average_cost(unit.material_id)
        return weighted_avg * unit.quantity_per_unit
    
    def update_unit(
        self,
        unit_id: int,
        display_name: str = None,
        quantity_per_unit: Decimal = None,
        notes: str = None
    ) -> MaterialUnit:
        """Update material unit"""
        # Note: Cannot change unit_type (would break consumption records)
        
    def delete_unit(self, unit_id: int) -> None:
        """Delete material unit"""
        # Validation: Cannot delete if used in Composition or MaterialConsumption
```

**Key Points:**
- MaterialUnit has NO material_product_id (generic definition)
- Available inventory aggregates across ALL MaterialProducts of the Material
- Cost calculated dynamically using weighted average

#### Enhanced AssemblyService

```python
class AssemblyService:
    """Enhanced assembly workflow with materials support"""
    
    def validate_assembly_readiness(self, finished_good_id: int, quantity: int) -> Dict[str, Any]:
        """Validate if assembly can proceed"""
        
        finished_good = self.get_finished_good(finished_good_id)
        issues = []
        warnings = []
        
        # Check component inventory
        for comp in finished_good.compositions:
            if comp.finished_unit_id:
                available = self.get_finished_unit_inventory(comp.finished_unit_id)
                required = comp.quantity * quantity
                if available < required:
                    issues.append(f"Insufficient {comp.finished_unit.display_name}: need {required}, have {available}")
            
            elif comp.material_unit_id:
                unit_service = MaterialUnitService()
                available = unit_service.calculate_available_inventory(comp.material_unit_id)
                required = comp.quantity * quantity
                if available < required:
                    issues.append(f"Insufficient {comp.material_unit.display_name}: need {required}, have {available}")
            
            elif comp.material_id:
                # HARD STOP: Generic material placeholder not resolved
                issues.append(f"Material selection pending for {comp.material.display_name}")
        
        return {
            'can_proceed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def record_assembly(
        self,
        finished_good_id: int,
        quantity: int,
        assembled_at: datetime,
        material_assignments: List[Dict[str, Any]] = None,  # For resolving material_id placeholders
        bypass_validation: bool = False,
        notes: str = None
    ) -> AssemblyRun:
        """Record assembly with material consumption"""
        
        # 1. Validate readiness (unless bypassed)
        if not bypass_validation:
            validation = self.validate_assembly_readiness(finished_good_id, quantity)
            if not validation['can_proceed']:
                raise AssemblyValidationError(validation['issues'])
        
        # 2. Create AssemblyRun
        assembly_run = AssemblyRun(
            finished_good_id=finished_good_id,
            quantity_assembled=quantity,
            assembled_at=assembled_at,
            requires_material_reconciliation=bypass_validation,
            notes=notes
        )
        
        # 3. Process FinishedUnit components
        component_cost = Decimal('0.0')
        for comp in finished_good.compositions:
            if comp.finished_unit_id:
                fu_service = FinishedUnitService()
                cost = fu_service.calculate_current_cost(comp.finished_unit_id)
                qty = comp.quantity * quantity
                
                consumption = AssemblyConsumption(
                    assembly_run_id=assembly_run.id,
                    finished_unit_id=comp.finished_unit_id,
                    quantity_consumed=qty,
                    per_unit_cost=cost
                )
                component_cost += cost * qty
                
                # Decrement FinishedUnit inventory
                fu_service.decrement_inventory(comp.finished_unit_id, qty)
        
        # 4. Process MaterialUnit/Material components
        material_cost = Decimal('0.0')
        for comp in finished_good.compositions:
            if comp.material_unit_id:
                # Specific MaterialUnit - need to resolve to MaterialProduct
                if not material_assignments:
                    raise AssemblyValidationError("Material assignments required")
                
                # Find assignment for this component
                assignment = next(
                    (a for a in material_assignments if a['composition_id'] == comp.id),
                    None
                )
                if not assignment:
                    raise AssemblyValidationError(f"No material assignment for {comp.material_unit.display_name}")
                
                # Create MaterialConsumption records (may be multiple products)
                for product_assignment in assignment['products']:
                    product_id = product_assignment['material_product_id']
                    qty_consumed = product_assignment['quantity']
                    
                    product = self.get_material_product(product_id)
                    unit_cost = product.current_unit_cost  # Snapshot
                    
                    consumption = MaterialConsumption(
                        assembly_run_id=assembly_run.id,
                        material_id=comp.material_unit.material_id,
                        material_product_id=product_id,
                        quantity_per_unit=comp.material_unit.quantity_per_unit,
                        display_name_snapshot=f"{product.display_name}",
                        quantity_consumed=qty_consumed,
                        per_unit_cost=unit_cost
                    )
                    material_cost += unit_cost * qty_consumed
                    
                    # Decrement MaterialProduct inventory
                    material_qty = qty_consumed * comp.material_unit.quantity_per_unit
                    product.inventory_count -= material_qty
            
            elif comp.material_id:
                # Generic placeholder - must be resolved via material_assignments
                if not bypass_validation:
                    raise AssemblyValidationError("Cannot proceed with unresolved material placeholders")
                # If bypassed, skip material consumption (reconciliation needed later)
        
        # 5. Calculate totals
        assembly_run.total_component_cost = component_cost
        assembly_run.total_material_cost = material_cost
        assembly_run.total_assembly_cost = component_cost + material_cost
        assembly_run.per_assembly_cost = component_cost / quantity  # Legacy
        assembly_run.per_unit_assembly_cost = (component_cost + material_cost) / quantity
        
        return assembly_run
    
    def get_pending_material_assignments(self) -> List[AssemblyRun]:
        """Get assembly runs requiring material reconciliation"""
        return self.session.query(AssemblyRun).filter(
            AssemblyRun.requires_material_reconciliation == True
        ).all()
```

**Key Points:**
- HARD STOP if material_id (generic placeholder) not resolved
- "Record Anyway" bypass sets requires_material_reconciliation = True
- material_assignments parameter resolves MaterialUnit → MaterialProduct mappings
- MaterialConsumption captures complete identity snapshot
- MaterialProduct inventory decremented atomically

---

### 3.3 UI Components

#### Materials Tab (CATALOG Mode)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ MATERIALS                                          [+ Add ▼]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─ Categories ──────────────┐ ┌─ Products ─────────────────┐│
│ │                            │ │                             ││
│ │ > Ribbons (45 products)    │ │ Material: Red Satin Ribbon  ││
│ │   > Satin Ribbon (30)      │ │                             ││
│ │   > Grosgrain Ribbon (15)  │ │ Michaels Red Satin 100ft   ││
│ │ > Boxes (28 products)      │ │   Inv: 1200" ($0.12/")     ││
│ │   > Gift Boxes (20)        │ │   Supplier: Michaels       ││
│ │   > Shipping Boxes (8)     │ │                             ││
│ │ > Bags (32 products)       │ │ Amazon Red Satin 50ft      ││
│ │   > Cellophane Bags (22)   │ │   Inv: 600" ($0.10/")      ││
│ │   > Paper Bags (10)        │ │                             ││
│ │                            │ │ [Edit] [Purchase] [Adjust] ││
│ │ [+ Category] [+ Material]  │ │                             ││
│ └────────────────────────────┘ └─────────────────────────────┘│
│                                                               │
│ ┌─ Material Units ──────────────────────────────────────────┐│
│ │ 6" Red Ribbon (linear_inches)                             ││
│ │   Available: 300 units (1800" across 2 products)          ││
│ │   Current cost: $0.66/unit (weighted average)             ││
│ │                                                            ││
│ │ 12" Red Ribbon (linear_inches)                            ││
│ │   Available: 150 units (1800" across 2 products)          ││
│ │   Current cost: $1.32/unit (weighted average)             ││
│ │                                                            ││
│ │ [+ Material Unit]                                          ││
│ └────────────────────────────────────────────────────────────┘│
│                                                               │
└─────────────────────────────────────────────────────────────┘

Footer: "Materials catalog - costs are current weighted averages"
```

**UI Features:**
- Three-panel layout: Categories/Materials | Products | Material Units
- Hierarchical navigation (Category → Subcategory → Material → Products)
- Product inventory shows current_unit_cost (weighted average, updates on purchase)
- Material Unit panel shows aggregate inventory and calculated cost

#### Material Purchase Dialog

```
┌─ Record Material Purchase ──────────────────────────────────┐
│                                                               │
│ Material Product: [Michaels Red Satin 100ft Roll      ▼]    │
│ Supplier:         [Michaels                           ▼]    │
│                                                               │
│ Package Details:                                              │
│   Unit count per package: [___100___] ft per roll            │
│   Packages purchased:     [_____2___]                        │
│   Total units:            1200 ft (calculated)               │
│                                                               │
│ Cost:                                                         │
│   Total cost:             [$__24.00_]                        │
│   Unit cost:              $0.12/ft (calculated)              │
│                                                               │
│ Purchased on: [2024-12-15 ▼]                                │
│ Notes: [____________________________________]                 │
│                                                               │
│                           [Cancel] [Record Purchase]         │
└───────────────────────────────────────────────────────────────┘

After purchase:
  MaterialProduct inventory: 600" → 1800" (+1200")
  MaterialProduct cost: $0.10/ft → $0.11/ft (new weighted average)
```

#### Inventory Adjustment Dialog

```
┌─ Adjust Material Inventory ─────────────────────────────────┐
│                                                               │
│ Product: Michaels Red Satin 100ft Roll                       │
│ Current inventory: 1200 linear_inches (100 ft)               │
│                                                               │
│ Adjustment type:                                              │
│   ○ Count adjustment (add/subtract specific amount)         │
│   ● Percentage remaining                                     │
│                                                               │
│ Percentage remaining: [____20____] %                         │
│                                                               │
│ Calculated new inventory: 240 linear_inches (20 ft)          │
│ Adjustment amount: -960 linear_inches                        │
│                                                               │
│ Reason: [Used on personal project____________________]       │
│                                                               │
│                           [Cancel] [Adjust Inventory]        │
└───────────────────────────────────────────────────────────────┘
```

#### FinishedGood Edit Dialog (Enhanced with Materials)

```
┌─ Edit Finished Good: Holiday Gift Box ──────────────────────┐
│                                                               │
│ Components:                                                   │
│                                                               │
│ ┌─ Baked Goods ──────────────────────────────────────────┐  │
│ │ 6 × Large Cookie                          [Edit] [Del] │  │
│ │ 3 × Brownie                               [Edit] [Del] │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Materials ────────────────────────────────────────────┐  │
│ │ 1 × 6" Cellophane Bag ⚠️               [Edit] [Del] │  │
│ │     (Selection pending - 4 designs available)           │  │
│ │                                                          │  │
│ │ 2 × Tissue Paper Sheet ✓                [Edit] [Del] │  │
│ │     (Specific: White Tissue 12x12)                      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ [+ Add Component ▼]                                          │
│   ├─ Finished Unit (baked good)                             │
│   ├─ Material Unit (specific)                               │
│   └─ Material (generic, defer decision)                     │
│                                                               │
│ Cost Summary:                                                 │
│   Food components:     $4.47 (actual)                        │
│   Material components: $0.82 (estimated) + $0.10 (actual)    │
│   Total:               $5.39 (estimated)                     │
│                                                               │
│                           [Cancel] [Save]                    │
└───────────────────────────────────────────────────────────────┘

Legend:
  ⚠️ = Generic material (selection pending)
  ✓ = Specific material (ready for assembly)
```

#### Add Material Component Dialog

```
┌─ Add Material to Finished Good ─────────────────────────────┐
│                                                               │
│ Material Type:                                                │
│   ● Specific Material Unit (ready for assembly)             │
│   ○ Generic Material (defer decision to assembly)           │
│                                                               │
│ Select Material Unit: [6" Cellophane Bag            ▼]      │
│                                                               │
│ Available inventory: 82 units (4 designs)                    │
│   - Snowflakes: 30 units                                     │
│   - Holly: 25 units                                          │
│   - Stars: 20 units                                          │
│   - Snowmen: 7 units                                         │
│                                                               │
│ Estimated cost: $0.25/unit (weighted average)                │
│                                                               │
│ Quantity needed: [___1___] per finished good                 │
│                                                               │
│                           [Cancel] [Add Material]            │
└───────────────────────────────────────────────────────────────┘

If "Generic Material" selected:
┌─ Add Generic Material to Finished Good ─────────────────────┐
│                                                               │
│ Material Type:                                                │
│   ○ Specific Material Unit (ready for assembly)             │
│   ● Generic Material (defer decision to assembly)           │
│                                                               │
│ Select Material: [Cellophane Bag 6"                  ▼]     │
│                                                               │
│ Available products: 4 designs (82 total units)               │
│ Estimated cost: $0.25/unit (weighted average)                │
│                                                               │
│ ⚠️ Decision will be required before assembly                 │
│                                                               │
│ Quantity needed: [___1___] per finished good                 │
│                                                               │
│                           [Cancel] [Add Material]            │
└───────────────────────────────────────────────────────────────┘
```

#### Assembly Recording Dialog (Enhanced with Hard Stop)

```
┌─ Record Assembly: Holiday Gift Box ─────────────────────────┐
│                                                               │
│ ⚠️ PACKAGING NOT FINALIZED                                   │
│                                                               │
│ The following materials need specific product selection:     │
│                                                               │
│ ┌─ 6" Cellophane Bag (50 needed) ────────────────────────┐  │
│ │                                                          │  │
│ │ Assign specific products:                               │  │
│ │   ☐ Snowflakes    Available: 30   Use: [_30_]         │  │
│ │   ☑ Holly         Available: 25   Use: [_20_]         │  │
│ │   ☐ Stars         Available: 20   Use: [____]         │  │
│ │   ☐ Snowmen       Available:  7   Use: [____]         │  │
│ │                                                          │  │
│ │   Total assigned: 50 / 50 needed ✓                     │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ Cost Summary:                                                 │
│   Component costs:     $223.50 (actual)                      │
│   Material costs:      $12.40 (actual - based on selection)  │
│   Total assembly cost: $235.90                               │
│   Per unit cost:       $4.72                                 │
│                                                               │
│ Quantity to assemble: [___50___]                            │
│ Assembled on: [2024-12-20 ▼]                                │
│                                                               │
│ [Assembly Details] [Record Assembly Anyway] [Assign & Record]│
└───────────────────────────────────────────────────────────────┘

After "Assign & Record":
  - MaterialConsumption records created (identity snapshots)
  - MaterialProduct inventories decremented
  - AssemblyRun costs captured (immutable)
```

#### Production Dashboard (Enhanced with Indicators)

```
┌─ Production Dashboard ───────────────────────────────────────┐
│                                                               │
│ In Progress Productions:                                      │
│                                                               │
│ ┌─ Holiday Gift Box (50 units) ──────────────────────────┐  │
│ │ ├─ Baking: Complete ✓                                   │  │
│ │ │   - 300 cookies baked                                 │  │
│ │ │   - 150 brownies baked                                │  │
│ │ ├─ Assembly: Pending ⚠️  [Assign Materials]           │  │
│ │ │     └─ Packaging needs selection                      │  │
│ │ └─ Delivery: Not started                                │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Wedding Favor Boxes (100 units) ───────────────────────┐  │
│ │ ├─ Baking: In Progress                                   │  │
│ │ ├─ Assembly: Ready ✓                                    │  │
│ │ └─ Delivery: Scheduled for 12/25                        │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘

Legend:
  ⚠️ = Action needed (click to resolve)
  ✓ = Ready to proceed
```

---

### 3.4 Cost Calculation Logic

#### MaterialProduct.current_unit_cost (Weighted Average)

```python
def update_weighted_average_cost(
    product: MaterialProduct,
    new_units: Decimal,
    new_unit_cost: Decimal
) -> Decimal:
    """Update MaterialProduct weighted average cost on purchase"""
    
    old_inventory = product.inventory_count
    old_cost = product.current_unit_cost or Decimal('0.0')
    
    new_inventory = old_inventory + new_units
    
    new_weighted_avg = (
        (old_inventory * old_cost) + (new_units * new_unit_cost)
    ) / new_inventory
    
    return new_weighted_avg

# Example:
# Old: 200 units @ $0.35 = $70.00
# New purchase: 100 units @ $0.40 = $40.00
# New weighted avg: ($70 + $40) / 300 = $0.3667
```

#### Material Cost (Aggregate Weighted Average)

```python
def calculate_material_weighted_average_cost(material: Material) -> Decimal:
    """Calculate weighted average across all MaterialProducts"""
    
    total_value = Decimal('0.0')
    total_inventory = Decimal('0.0')
    
    for product in material.products:
        if product.current_unit_cost:
            total_value += product.inventory_count * product.current_unit_cost
            total_inventory += product.inventory_count
    
    if total_inventory == 0:
        return Decimal('0.0')
    
    return total_value / total_inventory

# Example:
# Product A: 1200" @ $0.12/" = $144.00
# Product B: 600" @ $0.10/" = $60.00
# Product C: 900" @ $0.11/" = $99.00
# Total: 2700" for $303.00
# Weighted avg: $303 / 2700 = $0.1122/"
```

#### MaterialUnit Cost (Calculated from Material)

```python
def calculate_material_unit_cost(material_unit: MaterialUnit) -> Decimal:
    """Calculate MaterialUnit cost using material weighted average"""
    
    material_weighted_avg = calculate_material_weighted_average_cost(
        material_unit.material
    )
    
    return material_weighted_avg * material_unit.quantity_per_unit

# Example:
# Material "Red Ribbon" weighted avg: $0.1122/"
# MaterialUnit "6\" Red Ribbon": 6 inches
# Cost: $0.1122 × 6 = $0.6732
```

#### FinishedGood Cost with Materials

```python
def calculate_finished_good_cost(finished_good: FinishedGood) -> Tuple[Decimal, Decimal, str]:
    """Calculate FinishedGood cost (components + materials)"""
    
    component_cost = Decimal('0.0')
    material_cost = Decimal('0.0')
    cost_type = 'actual'  # or 'estimated'
    
    for comp in finished_good.compositions:
        if comp.finished_unit_id:
            # Food component (actual cost)
            fu_cost = calculate_finished_unit_cost(comp.finished_unit)
            component_cost += fu_cost * comp.quantity
        
        elif comp.material_unit_id:
            # Specific material (actual cost)
            mu_cost = calculate_material_unit_cost(comp.material_unit)
            material_cost += mu_cost * comp.quantity
        
        elif comp.material_id:
            # Generic material (estimated cost)
            material_weighted_avg = calculate_material_weighted_average_cost(comp.material)
            # Assume quantity_per_unit = 1 for generic (no MaterialUnit defined)
            material_cost += material_weighted_avg * comp.quantity
            cost_type = 'estimated'
    
    total_cost = component_cost + material_cost
    return (component_cost, material_cost, cost_type)

# Returns: (food_cost, material_cost, 'actual' or 'estimated')
```

#### AssemblyRun Cost Capture

```python
def capture_assembly_costs(assembly_run: AssemblyRun) -> None:
    """Capture immutable cost snapshots at assembly time"""
    
    # Component costs (from AssemblyConsumption)
    component_cost = sum(
        consumption.per_unit_cost * consumption.quantity_consumed
        for consumption in assembly_run.assembly_consumptions
    )
    
    # Material costs (from MaterialConsumption)
    material_cost = sum(
        consumption.per_unit_cost * consumption.quantity_consumed
        for consumption in assembly_run.material_consumptions
    )
    
    # Update AssemblyRun (immutable snapshots)
    assembly_run.total_component_cost = component_cost
    assembly_run.total_material_cost = material_cost
    assembly_run.total_assembly_cost = component_cost + material_cost
    assembly_run.per_assembly_cost = component_cost / assembly_run.quantity_assembled
    assembly_run.per_unit_assembly_cost = (component_cost + material_cost) / assembly_run.quantity_assembled
```

---

### 3.5 Import/Export

#### Catalog Import (Materials)

**JSON Format:**
```json
{
  "version": "4.2",
  "material_categories": [
    {
      "display_name": "Ribbons",
      "notes": "All ribbon types"
    }
  ],
  "material_subcategories": [
    {
      "category": "Ribbons",
      "display_name": "Satin Ribbon",
      "notes": null
    }
  ],
  "materials": [
    {
      "subcategory": "Satin Ribbon",
      "display_name": "Red Satin Ribbon",
      "notes": null
    }
  ],
  "material_products": [
    {
      "material": "Red Satin Ribbon",
      "display_name": "Michaels Red Satin 100ft Roll",
      "default_unit": "linear_inches",
      "supplier": "Michaels",
      "notes": null
    }
  ],
  "material_units": [
    {
      "material": "Red Satin Ribbon",
      "display_name": "6\" Red Ribbon",
      "quantity_per_unit": 6.0,
      "unit_type": "linear_inches",
      "notes": null
    }
  ]
}
```

**Import Behavior:**
- Mode: ADD_ONLY (create new, error on duplicate)
- References resolved by display_name
- Validates: unit types, constraints
- Creates in order: Categories → Subcategories → Materials → Products → Units

#### View Import/Export (Materials)

**Export Format:**
```json
{
  "version": "4.2",
  "material_purchases": [
    {
      "material_product": "Michaels Red Satin 100ft Roll",
      "package_unit_count": 100.0,
      "packages_purchased": 2.0,
      "total_units": 200.0,
      "calculated_unit_cost": 0.12,
      "total_cost": 24.00,
      "purchased_at": "2024-12-15T10:00:00",
      "supplier": "Michaels",
      "notes": null
    }
  ],
  "material_inventory": [
    {
      "material_product": "Michaels Red Satin 100ft Roll",
      "inventory_count": 1200.0,
      "current_unit_cost": 0.11,
      "as_of": "2024-12-20T15:30:00"
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: Data Models & Service Layer (12-14 hours)

**Tasks:**
1. Create MaterialCategory, MaterialSubcategory, Material models
2. Create MaterialProduct, MaterialUnit models
3. Create MaterialPurchase, MaterialConsumption models
4. Enhance Composition model (add material_id field)
5. Enhance AssemblyRun model (add material cost fields)
6. Implement MaterialCategoryService, MaterialSubcategoryService
7. Implement MaterialService, MaterialProductService
8. Implement MaterialPurchaseService, MaterialUnitService
9. Enhance AssemblyService (material validation, consumption)
10. Write unit tests for all services

**Deliverables:**
- ✅ 8 new models created
- ✅ 2 models enhanced (Composition, AssemblyRun)
- ✅ 6 service classes implemented
- ✅ Weighted average cost calculation
- ✅ Identity snapshot capture
- ✅ Unit test coverage >80%

### Phase 2: UI Implementation (10-12 hours)

**Tasks:**
1. Implement Materials tab (CATALOG mode)
   - Category/subcategory/material navigation
   - Product list with inventory display
   - Material unit management
2. Implement material purchase dialog
3. Implement inventory adjustment dialog
4. Enhance FinishedGood edit dialog
   - Add material component selection
   - Visual indicators (⚠️ generic, ✓ specific)
   - Cost summary with estimated/actual labels
5. Enhance assembly recording dialog
   - Hard stop for unresolved materials
   - Quick assignment interface
   - Material cost display
6. Enhance production dashboard
   - Pending material indicators
   - Clickable links to assignment screen

**Deliverables:**
- ✅ Materials tab functional (CRUD operations)
- ✅ Purchase/adjustment workflows working
- ✅ FinishedGood composition UI enhanced
- ✅ Assembly hard stop enforced
- ✅ Visual indicators consistent (⚠️/✓)

### Phase 3: Integration & Testing (6-8 hours)

**Tasks:**
1. Implement import/export for materials
2. Update event planning calculations (material costs)
3. Update shopping list generation (generic materials)
4. End-to-end testing:
   - Complete material workflow (catalog → purchase → assemble)
   - Deferred decision workflow (generic → resolved at assembly)
   - Cost calculations (weighted average, estimates, actuals)
   - Identity snapshot capture (historical queries)
5. User acceptance testing with Marianne
6. Documentation updates

**Deliverables:**
- ✅ Import/export working
- ✅ Event planning shows material costs
- ✅ Shopping lists include materials
- ✅ All workflows tested end-to-end
- ✅ User documentation complete

---

## Testing Strategy

### Unit Tests

**MaterialService:**
- create_material, list_materials, update_material, delete_material
- calculate_aggregate_inventory
- calculate_weighted_average_cost

**MaterialProductService:**
- create_product, update_product, delete_product
- adjust_inventory (count and percentage)
- Inventory non-negative constraint

**MaterialPurchaseService:**
- record_purchase (cost calculation, inventory update, weighted average)
- Purchase validation (positive quantities, costs)

**MaterialUnitService:**
- create_unit, update_unit, delete_unit
- calculate_available_inventory (aggregate across products)
- calculate_current_cost (weighted average)

**AssemblyService:**
- validate_assembly_readiness (check material placeholders)
- record_assembly (with material assignments)
- Material consumption creation (identity snapshots)
- requires_material_reconciliation flag

### Integration Tests

**End-to-End Workflows:**
1. **Basic Material Flow:**
   - Create material ontology
   - Create material products
   - Purchase materials (weighted average updated)
   - Create material units
   - Add to FinishedGood
   - Record assembly (consumption created)
   - Verify inventory decremented

2. **Deferred Decision Flow:**
   - Create FinishedGood with Material placeholder
   - Plan event (estimated costs shown)
   - Validate assembly (hard stop)
   - Assign specific products (quick interface)
   - Record assembly (identity snapshots captured)
   - Query historical assembly (verify snapshot data)

3. **Cost Calculation Flow:**
   - Purchase materials at different costs
   - Verify weighted average calculation
   - Create MaterialUnit
   - Verify cost calculation (weighted avg × quantity)
   - Record assembly
   - Verify immutable cost snapshots

### User Acceptance Testing

**Test Scenarios with Marianne:**
1. Create complete materials catalog for holiday baking
2. Purchase materials from different suppliers
3. Create finished goods with materials (specific and generic)
4. Plan Christmas event with materials
5. Record assembly with material selection
6. Verify costs in event summary
7. Query historical assembly (2 weeks later)
8. Adjust material inventory (percentage)

---

## Constitutional Compliance

### Principle I: User-Centric Design
✅ **Compliant**
- Materials workflow mirrors ingredient workflow (users learn by analogy)
- F026 deferred decision pattern validated with users
- Visual indicators (⚠️/✓) provide clear feedback
- Quick assignment interface resolves materials without leaving assembly screen

### Principle II: Future-Proof Schema Design
✅ **Compliant**
- Three-level ontology supports future taxonomies
- MaterialProduct separate from Material enables multi-sourcing
- Identity snapshots enable historical queries without catalog dependency
- Architecture supports web migration and e-commerce integration

### Principle III: Data Integrity
✅ **Compliant**
- Immutable cost snapshots (MaterialPurchase, MaterialConsumption)
- Immutable identity snapshots (display_name_snapshot)
- Strict separation (materials != ingredients, shared Supplier only)
- Inventory constraints (non-negative, cascade deletes)
- Assembly hard stop prevents incomplete data

### Principle IV: Layered Architecture Discipline
✅ **Compliant**
- Service layer encapsulates all business logic
- Models contain NO business logic (pure data)
- UI calls services only (never direct ORM)
- Clear separation: Models → Services → UI

### Principle V: Consistent Patterns
✅ **Compliant**
- Materials parallel Ingredients exactly (ontology, purchasing, inventory)
- Definition/instantiation pattern (catalog vs transactional)
- MaterialUnit parallels FinishedUnit (atomic consumption)
- MaterialConsumption parallels ProductionConsumption (identity + cost)

### Principle VI: Pragmatic Aspiration
✅ **Compliant**
- Delivers immediate value (materials in assemblies)
- Defers advanced features (rich metadata, templates, analytics)
- Balances flexibility (deferred decisions) with data quality (hard stop)
- 28-32 hour estimate (significant but bounded scope)

---

## Migration Notes

**No migration required** - this is a new feature with no existing data.

**Schema changes:**
- Add 8 new tables (MaterialCategory through MaterialConsumption)
- Modify Composition table (add material_id nullable column)
- Modify AssemblyRun table (add material cost fields, reconciliation flag)

**Future migration considerations:**
- If users created "packaging ingredients" workaround, manual cleanup required
- No automated migration (user must recreate as materials)

---

## Success Criteria

### Functional Requirements
1. ✅ Materials ontology hierarchy operational (3 levels)
2. ✅ MaterialProduct catalog operational (CRUD + weighted average costing)
3. ✅ MaterialUnit catalog operational (CRUD + aggregate inventory)
4. ✅ Material purchasing workflow functional (package quantities)
5. ✅ Inventory adjustments working (count and percentage)
6. ✅ FinishedGood composition supports materials (specific/generic/none)
7. ✅ Assembly hard stop enforces material resolution
8. ✅ Quick assignment interface functional
9. ✅ MaterialConsumption captures identity snapshots
10. ✅ Historical queries work ("what did I make 2 years ago")
11. ✅ Event planning shows material costs (estimated/actual)
12. ✅ Import/export works for materials

### Quality Requirements
1. ✅ Materials model exactly parallels Ingredient model
2. ✅ All business rules enforced (validation constraints)
3. ✅ UI follows existing patterns (catalog, purchasing, inventory)
4. ✅ No material data in ingredient tables (strict separation)
5. ✅ Cost calculations accurate (weighted average verified)
6. ✅ Assembly workflow consistent (matches food pattern)
7. ✅ Deferred decision workflow matches F026 pattern
8. ✅ Visual indicators clear (⚠️ = action needed, ✓ = ready)

### User Acceptance
1. ✅ Marianne can create materials catalog
2. ✅ Marianne can purchase materials and see inventory update
3. ✅ Marianne can add materials to FinishedGoods
4. ✅ Marianne can plan events with material costs
5. ✅ Marianne can defer material decisions to assembly time
6. ✅ Marianne can record assembly with material selection
7. ✅ Marianne can query historical assemblies

---

## Risks & Mitigation

### Risk 1: Complexity Underestimation
**Risk**: Full parallel to Ingredient model + deferred decisions = significant scope
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Leverage existing ingredient patterns (reduce implementation time)
- Defer advanced features (templates, analytics, rich metadata)
- Estimated 28-32 hours accounts for complexity

### Risk 2: MaterialUnit Inventory Confusion
**Risk**: Users may not understand aggregate inventory calculation
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Clear UI messaging ("Available: 450 units from 2700\" across 3 products")
- Documentation with examples
- Pattern matches FinishedUnit (users already understand)

### Risk 3: Deferred Decision Workflow Resistance
**Risk**: Users annoyed by assembly hard stop
**Likelihood**: Low (F026 validated with users)
**Impact**: Low
**Mitigation**:
- F026 pattern already validated (users accepted workflow)
- "Record Assembly Anyway" bypass available
- Quick assignment interface minimizes friction

### Risk 4: Weighted Average Cost Accuracy
**Risk**: Users expect lot-level FIFO accuracy
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Document methodology clearly
- Show weighted average calculation in UI
- Emphasis: "Materials non-perishable, weighted average sufficient"

---

## Open Questions

*None remaining - all resolved in requirements phase.*

---

## References

- **Requirements**: docs/requirements/req_materials.md v2.1
- **F026 Pattern**: docs/design/F026-deferred-packaging-decisions.md
- **F046 Dependency**: docs/design/F046-finished-goods-bundles-assembly.md
- **Constitution**: docs/constitution.md

---

**END OF SPECIFICATION**
