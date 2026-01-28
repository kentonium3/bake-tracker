# BakeTracker Cloud Migration: Technical Implementation

**Document Purpose**: Define technical architecture, implementation patterns, and concrete code examples for cloud multi-tenant migration.

**Audience**: Senior developers, architects, and implementation engineers working on the cloud migration.

**Last Updated**: January 2026

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    BakeTracker Cloud                        │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Svelte     │         │   FastAPI    │                │
│  │   PWA        │◄───────►│   Backend    │                │
│  │   Frontend   │   API   │  + MCP       │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                           ┌───────▼────────┐               │
│                           │  PostgreSQL     │               │
│                           │  Multi-Tenant   │               │
│                           └─────────────────┘               │
│                                                             │
│  ┌──────────────┐                                          │
│  │   Gemini     │         ┌──────────────┐                │
│  │   2.5 Flash  │◄───────►│   MCP Tools  │                │
│  │   API        │         │   Server     │                │
│  └──────────────┘         └──────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| **Layer** | **Technology** | **Version** |
|-----------|---------------|-------------|
| Frontend | Svelte | 5.x |
| Build Tool | Vite | 5.x |
| UI Framework | TailwindCSS + DaisyUI | 3.x / 4.x |
| Backend | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.x |
| Database | PostgreSQL | 15+ |
| Auth | Firebase Auth | Latest |
| AI Integration | Gemini API | 2.5 Flash/Pro |
| MCP | FastMCP | 2.12.3+ |
| Hosting | Render or Railway | - |
| Storage | Cloudflare R2 | - |

---

## Database Architecture

### Multi-Tenant Schema Design

#### Pattern: Shared Database, Single Schema with `tenant_id`

**Core Principle**: Every tenant-scoped table includes `tenant_id` UUID column with PostgreSQL Row-Level Security (RLS) enforcing automatic isolation.

#### Example: Ingredients Table

```sql
-- Before (Desktop - Single User)
CREATE TABLE ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    default_unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- After (Cloud - Multi-Tenant)
CREATE TABLE ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,                    -- NEW: Tenant isolation
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    default_unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite index for efficient tenant-scoped queries
    INDEX idx_ingredients_tenant (tenant_id, id),
    INDEX idx_ingredients_tenant_name (tenant_id, name),
    
    -- Foreign key to tenants table
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Enable Row-Level Security
ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's data
CREATE POLICY tenant_isolation_policy ON ingredients
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Policy: Users can only insert into their tenant
CREATE POLICY tenant_isolation_insert ON ingredients
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
```

#### Tenants Table

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true
);

-- No RLS on tenants table (managed through auth layer)
```

#### Users Table (Auth Integration)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,  -- Firebase Auth UID
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',           -- owner, admin, member
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    INDEX idx_users_tenant (tenant_id),
    INDEX idx_users_firebase (firebase_uid)
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see users in their tenant
CREATE POLICY tenant_users_policy ON users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

---

### Migration Strategy: SQLite → PostgreSQL

#### Export from Desktop SQLite

```python
# src/migration/export_sqlite.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

def export_all_data(sqlite_path: str, output_file: str):
    """Export all tables from SQLite to JSON"""
    engine = create_engine(f'sqlite:///{sqlite_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    export_data = {
        'export_version': '1.0',
        'exported_at': datetime.utcnow().isoformat(),
        'ingredients': [],
        'recipes': [],
        'events': [],
        'purchases': [],
        'pantry_items': []
    }
    
    # Export ingredients
    for ingredient in session.query(Ingredient).all():
        export_data['ingredients'].append({
            'id': str(ingredient.id),
            'name': ingredient.name,
            'category': ingredient.category,
            'default_unit': ingredient.default_unit,
            # ... other fields
        })
    
    # Export other tables similarly
    # ...
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    session.close()
    return export_data

# Usage
export_all_data(
    sqlite_path='bake_tracker.db',
    output_file='marianne_export.json'
)
```

#### Transform: Add tenant_id

```python
# src/migration/transform_data.py
import json
import uuid

MARIANNE_TENANT_ID = str(uuid.uuid4())  # Generate once, use consistently

def add_tenant_ids(export_file: str, output_file: str):
    """Add tenant_id to all records"""
    with open(export_file, 'r') as f:
        data = json.load(f)
    
    # Add tenant_id to all records in all tables
    for table in ['ingredients', 'recipes', 'events', 'purchases', 'pantry_items']:
        for record in data[table]:
            record['tenant_id'] = MARIANNE_TENANT_ID
    
    # Add tenant record
    data['tenants'] = [{
        'id': MARIANNE_TENANT_ID,
        'name': 'Marianne Baker',
        'email': 'marianne@example.com',
        'created_at': data['exported_at']
    }]
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

# Usage
add_tenant_ids(
    export_file='marianne_export.json',
    output_file='marianne_transformed.json'
)
```

#### Import to PostgreSQL

```python
# src/migration/import_postgres.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

def import_all_data(postgres_url: str, import_file: str):
    """Import JSON data to PostgreSQL"""
    engine = create_engine(postgres_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    with open(import_file, 'r') as f:
        data = json.load(f)
    
    try:
        # Import tenants first (foreign key dependency)
        for tenant_data in data['tenants']:
            tenant = Tenant(**tenant_data)
            session.add(tenant)
        session.commit()
        
        # Import ingredients
        for ingredient_data in data['ingredients']:
            ingredient = Ingredient(**ingredient_data)
            session.add(ingredient)
        session.commit()
        
        # Import other tables in dependency order
        # ...
        
        print(f"✓ Import successful: {len(data['ingredients'])} ingredients, etc.")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Import failed: {e}")
        raise
    finally:
        session.close()

# Usage
import_all_data(
    postgres_url='postgresql://user:pass@localhost/baketracker',
    import_file='marianne_transformed.json'
)
```

---

## Backend Architecture

### Service Layer Refactoring

#### Before: Desktop (Implicit Single User)

```python
# src/services/ingredient_service.py (Desktop)
from sqlalchemy.orm import Session
from src.models import Ingredient

class IngredientService:
    def __init__(self, session: Session):
        self.session = session
    
    def create_ingredient(self, name: str, category: str) -> Ingredient:
        """Create new ingredient"""
        ingredient = Ingredient(name=name, category=category)
        self.session.add(ingredient)
        self.session.commit()
        return ingredient
    
    def get_ingredient(self, ingredient_id: UUID) -> Ingredient:
        """Get ingredient by ID"""
        return self.session.query(Ingredient).filter_by(
            id=ingredient_id
        ).first()
    
    def list_ingredients(self) -> List[Ingredient]:
        """List all ingredients"""
        return self.session.query(Ingredient).all()
```

#### After: Cloud (Explicit Tenant Isolation)

```python
# src/services/ingredient_service.py (Cloud)
from sqlalchemy.orm import Session
from src.models import Ingredient
from uuid import UUID

class IngredientService:
    def __init__(self, session: Session):
        self.session = session
    
    def create_ingredient(
        self, 
        tenant_id: UUID,      # NEW: Explicit tenant
        name: str, 
        category: str
    ) -> Ingredient:
        """Create new ingredient for tenant"""
        ingredient = Ingredient(
            tenant_id=tenant_id,  # NEW
            name=name,
            category=category
        )
        self.session.add(ingredient)
        self.session.commit()
        return ingredient
    
    def get_ingredient(
        self, 
        tenant_id: UUID,      # NEW
        ingredient_id: UUID
    ) -> Ingredient:
        """Get ingredient by ID for tenant"""
        return self.session.query(Ingredient).filter_by(
            tenant_id=tenant_id,  # NEW: Tenant filter
            id=ingredient_id
        ).first()
    
    def list_ingredients(
        self, 
        tenant_id: UUID       # NEW
    ) -> List[Ingredient]:
        """List all ingredients for tenant"""
        return self.session.query(Ingredient).filter_by(
            tenant_id=tenant_id  # NEW: Tenant filter
        ).all()
```

**Migration Pattern**: Every service method gains `tenant_id` as first parameter, and every query adds `.filter_by(tenant_id=tenant_id)`.

---

### FastAPI Route Implementation

#### Authentication Middleware

```python
# src/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from uuid import UUID

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify Firebase JWT and extract user info"""
    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(credentials.credentials)
        
        # Extract Firebase UID
        firebase_uid = decoded_token['uid']
        
        # Look up user in database
        user = session.query(User).filter_by(
            firebase_uid=firebase_uid
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Return user with tenant_id
        return {
            'user_id': user.id,
            'tenant_id': user.tenant_id,
            'firebase_uid': firebase_uid,
            'email': user.email,
            'role': user.role
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication: {str(e)}"
        )

async def get_tenant_id(
    current_user: dict = Depends(get_current_user)
) -> UUID:
    """Extract tenant_id from authenticated user"""
    return current_user['tenant_id']
```

#### Example API Routes

```python
# src/api/routes/ingredients.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from typing import List

from src.api.dependencies import get_tenant_id, get_db_session
from src.services.ingredient_service import IngredientService

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

# Request/Response Models
class IngredientCreate(BaseModel):
    name: str
    category: str
    default_unit: str

class IngredientResponse(BaseModel):
    id: UUID
    name: str
    category: str
    default_unit: str
    created_at: str
    
    class Config:
        from_attributes = True  # SQLAlchemy model compatibility

# Routes
@router.post("/", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    data: IngredientCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session = Depends(get_db_session)
):
    """Create new ingredient"""
    service = IngredientService(session)
    ingredient = service.create_ingredient(
        tenant_id=tenant_id,
        name=data.name,
        category=data.category
    )
    return ingredient

@router.get("/", response_model=List[IngredientResponse])
async def list_ingredients(
    tenant_id: UUID = Depends(get_tenant_id),
    session = Depends(get_db_session)
):
    """List all ingredients for tenant"""
    service = IngredientService(session)
    ingredients = service.list_ingredients(tenant_id)
    return ingredients

@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session = Depends(get_db_session)
):
    """Get ingredient by ID"""
    service = IngredientService(session)
    ingredient = service.get_ingredient(tenant_id, ingredient_id)
    
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    return ingredient
```

#### Setting PostgreSQL Session Variable (RLS)

```python
# src/api/dependencies.py (continued)
from sqlalchemy.orm import Session

def get_db_session(
    tenant_id: UUID = Depends(get_tenant_id)
) -> Session:
    """Get database session with tenant context set"""
    session = SessionLocal()
    
    try:
        # Set PostgreSQL session variable for RLS
        session.execute(
            text("SET app.current_tenant = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        )
        
        yield session
        
    finally:
        session.close()
```

**This ensures all queries automatically filter by tenant_id at the database level.**

---

## AI Integration via MCP

### MCP Server Setup

```python
# src/mcp/server.py
from fastapi import FastAPI
from fastmcp import FastMCP
from src.services.purchase_service import PurchaseService
from src.services.inventory_service import InventoryService
from src.services.event_service import EventService

app = FastAPI()
mcp = FastMCP("bake-tracker")

@mcp.tool()
async def add_purchase(
    tenant_id: str,
    item_name: str,
    quantity: float,
    unit: str,
    price: float,
    store: str,
    receipt_image_url: str | None = None
) -> dict:
    """
    Record a purchase from shopping trip.
    
    Use this when user describes buying ingredients, either through:
    - Voice: "I bought two pounds of flour at Costco for $8"
    - Receipt photo: Extract items, quantities, prices from image
    
    Args:
        tenant_id: User's tenant identifier
        item_name: Name of ingredient purchased
        quantity: Amount purchased (numeric)
        unit: Unit of measurement (pounds, ounces, kilograms, etc.)
        price: Total price paid
        store: Store where purchased
        receipt_image_url: Optional URL to receipt image
    
    Returns:
        dict with purchase_id and confirmation message
    """
    # Initialize service
    session = get_session()
    service = PurchaseService(session)
    
    # Create purchase
    purchase = service.create_purchase(
        tenant_id=UUID(tenant_id),
        item_name=item_name,
        quantity=quantity,
        unit=unit,
        price=price,
        store=store,
        receipt_image_url=receipt_image_url
    )
    
    session.close()
    
    return {
        "success": True,
        "purchase_id": str(purchase.id),
        "message": f"Recorded {quantity} {unit} of {item_name} for ${price}"
    }

@mcp.tool()
async def adjust_inventory(
    tenant_id: str,
    pantry_item_id: str,
    percentage_remaining: int,
    photo_evidence_url: str | None = None
) -> dict:
    """
    Adjust pantry inventory based on visual assessment.
    
    Use this when user provides a photo of an ingredient and estimates
    how much is left (e.g., "flour bag is about 40% full").
    
    Args:
        tenant_id: User's tenant identifier
        pantry_item_id: ID of pantry item to adjust
        percentage_remaining: Percentage of ingredient left (0-100)
        photo_evidence_url: Optional URL to inventory photo
    
    Returns:
        dict with new quantity and confirmation
    """
    session = get_session()
    service = InventoryService(session)
    
    # Adjust inventory using percentage
    adjustment = service.adjust_by_percentage(
        tenant_id=UUID(tenant_id),
        pantry_item_id=UUID(pantry_item_id),
        percentage_remaining=percentage_remaining,
        photo_url=photo_evidence_url
    )
    
    session.close()
    
    return {
        "success": True,
        "pantry_item_id": str(adjustment.pantry_item_id),
        "new_quantity": adjustment.new_quantity,
        "new_unit": adjustment.unit,
        "message": f"Updated to {adjustment.new_quantity} {adjustment.unit} ({percentage_remaining}% remaining)"
    }

@mcp.tool()
async def create_event_with_recipes(
    tenant_id: str,
    event_name: str,
    event_date: str,  # ISO format: "2025-12-25"
    guest_count: int,
    recipe_names: list[str]
) -> dict:
    """
    Create event and add recipes based on voice description.
    
    Use this when user describes an upcoming event:
    "I'm hosting Thanksgiving for 12 people, making cranberry tart and pumpkin pie"
    
    Args:
        tenant_id: User's tenant identifier
        event_name: Name of event (e.g., "Thanksgiving Dinner 2025")
        event_date: Date in ISO format
        guest_count: Number of guests
        recipe_names: List of recipe names user wants to make
    
    Returns:
        dict with event_id, matched recipes, and next steps
    """
    session = get_session()
    service = EventService(session)
    
    # Create event
    event = service.create_event(
        tenant_id=UUID(tenant_id),
        name=event_name,
        date=event_date,
        guest_count=guest_count
    )
    
    # Match recipe names to existing recipes (fuzzy match)
    matched_recipes = service.match_recipe_names(
        tenant_id=UUID(tenant_id),
        recipe_names=recipe_names
    )
    
    # Add recipes to event
    for recipe in matched_recipes:
        service.add_recipe_to_event(
            event_id=event.id,
            recipe_id=recipe.id
        )
    
    session.close()
    
    return {
        "success": True,
        "event_id": str(event.id),
        "event_name": event_name,
        "recipes_added": [r.name for r in matched_recipes],
        "message": f"Created '{event_name}' with {len(matched_recipes)} recipes"
    }

# Mount MCP server to FastAPI
app.include_router(mcp.router, prefix="/mcp")
```

### Gemini Integration (Frontend)

```javascript
// src/lib/gemini-client.js
import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GEMINI_API_KEY);

export class GeminiClient {
  constructor() {
    this.model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
  }

  async processVoiceWithTools(audioBlob, tools, prompt) {
    /**
     * Send voice recording to Gemini with MCP tools
     * 
     * @param {Blob} audioBlob - Recorded audio
     * @param {Array} tools - MCP tool schemas
     * @param {string} prompt - System prompt
     * @returns {Object} - Tool calls from Gemini
     */
    
    // Convert audio to base64
    const base64Audio = await this.blobToBase64(audioBlob);
    
    // Call Gemini with function calling
    const result = await this.model.generateContent({
      contents: [{
        role: "user",
        parts: [
          { inlineData: { mimeType: "audio/wav", data: base64Audio } },
          { text: prompt }
        ]
      }],
      tools: [{ functionDeclarations: tools }],
      toolConfig: { functionCallingConfig: { mode: "AUTO" } }
    });
    
    const response = result.response;
    
    // Extract function calls
    const functionCalls = response.functionCalls();
    
    return {
      toolCalls: functionCalls,
      text: response.text()
    };
  }

  async processImageWithTools(imageBlob, tools, prompt) {
    /**
     * Send image to Gemini Vision with MCP tools
     * 
     * @param {Blob} imageBlob - Captured image
     * @param {Array} tools - MCP tool schemas
     * @param {string} prompt - System prompt
     * @returns {Object} - Tool calls from Gemini
     */
    
    const base64Image = await this.blobToBase64(imageBlob);
    
    const result = await this.model.generateContent({
      contents: [{
        role: "user",
        parts: [
          { inlineData: { mimeType: imageBlob.type, data: base64Image } },
          { text: prompt }
        ]
      }],
      tools: [{ functionDeclarations: tools }],
      toolConfig: { functionCallingConfig: { mode: "AUTO" } }
    });
    
    const response = result.response;
    
    return {
      toolCalls: response.functionCalls(),
      text: response.text()
    };
  }

  async blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
}
```

---

## Frontend Architecture

### Svelte Component Structure

```
src/
├── lib/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.svelte
│   │   │   └── SignupForm.svelte
│   │   ├── ingredients/
│   │   │   ├── IngredientList.svelte
│   │   │   ├── IngredientForm.svelte
│   │   │   └── IngredientCard.svelte
│   │   ├── purchases/
│   │   │   ├── VoicePurchaseButton.svelte
│   │   │   ├── ReceiptPhotoUpload.svelte
│   │   │   └── PurchaseConfirmation.svelte
│   │   ├── inventory/
│   │   │   ├── PantryList.svelte
│   │   │   ├── InventoryPhotoCapture.svelte
│   │   │   └── PercentageSlider.svelte
│   │   └── layout/
│   │       ├── Header.svelte
│   │       ├── Sidebar.svelte
│   │       └── MobileNav.svelte
│   ├── stores/
│   │   ├── auth.js
│   │   ├── ingredients.js
│   │   └── events.js
│   ├── api/
│   │   ├── client.js
│   │   ├── auth.js
│   │   ├── ingredients.js
│   │   └── mcp.js
│   └── utils/
│       ├── gemini-client.js
│       └── validation.js
└── routes/
    ├── +layout.svelte
    ├── +page.svelte
    ├── login/+page.svelte
    ├── ingredients/+page.svelte
    ├── recipes/+page.svelte
    └── events/+page.svelte
```

### Example: Voice Purchase Component

```svelte
<!-- src/lib/components/purchases/VoicePurchaseButton.svelte -->
<script>
  import { geminiClient } from '$lib/utils/gemini-client';
  import { mcpApi } from '$lib/api/mcp';
  import { onMount } from 'svelte';
  
  let isRecording = false;
  let audioBlob = null;
  let mediaRecorder = null;
  let stream = null;
  let proposedPurchase = null;
  let showConfirmation = false;
  
  async function startRecording() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      
      const chunks = [];
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = () => {
        audioBlob = new Blob(chunks, { type: 'audio/wav' });
        processVoice();
      };
      
      mediaRecorder.start();
      isRecording = true;
    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('Please allow microphone access to use voice purchasing');
    }
  }
  
  function stopRecording() {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      stream.getTracks().forEach(track => track.stop());
      isRecording = false;
    }
  }
  
  async function processVoice() {
    try {
      // Get MCP tools schema
      const tools = await mcpApi.getTools();
      const addPurchaseTool = tools.find(t => t.name === 'add_purchase');
      
      // Send audio to Gemini with add_purchase tool
      const response = await geminiClient.processVoiceWithTools(
        audioBlob,
        [addPurchaseTool],
        "Extract purchase details from this voice recording. User is describing what they bought."
      );
      
      if (response.toolCalls && response.toolCalls.length > 0) {
        // Gemini proposed a purchase
        const toolCall = response.toolCalls[0];
        proposedPurchase = {
          toolName: toolCall.name,
          arguments: toolCall.args
        };
        showConfirmation = true;
      } else {
        alert('Could not understand purchase details. Please try again.');
      }
    } catch (error) {
      console.error('Error processing voice:', error);
      alert('Error processing voice recording');
    }
  }
  
  async function confirmPurchase() {
    try {
      // Execute MCP tool
      const result = await mcpApi.executeTool(
        proposedPurchase.toolName,
        proposedPurchase.arguments
      );
      
      if (result.success) {
        alert(`✓ Purchase recorded: ${result.message}`);
        showConfirmation = false;
        proposedPurchase = null;
        
        // Trigger refresh of purchase list (via store)
        await refreshPurchases();
      }
    } catch (error) {
      console.error('Error saving purchase:', error);
      alert('Error saving purchase');
    }
  }
  
  function cancelPurchase() {
    showConfirmation = false;
    proposedPurchase = null;
  }
</script>

<div class="voice-purchase">
  {#if !showConfirmation}
    <button 
      class="btn btn-primary" 
      on:click={isRecording ? stopRecording : startRecording}
    >
      {#if isRecording}
        🔴 Stop Recording
      {:else}
        🎤 Voice Purchase
      {/if}
    </button>
  {:else}
    <div class="confirmation-card">
      <h3>Confirm Purchase</h3>
      <div class="purchase-details">
        <p><strong>Item:</strong> {proposedPurchase.arguments.item_name}</p>
        <p><strong>Quantity:</strong> {proposedPurchase.arguments.quantity} {proposedPurchase.arguments.unit}</p>
        <p><strong>Price:</strong> ${proposedPurchase.arguments.price}</p>
        <p><strong>Store:</strong> {proposedPurchase.arguments.store}</p>
      </div>
      
      <!-- Allow editing before confirmation -->
      <form on:submit|preventDefault={confirmPurchase}>
        <label>
          Item:
          <input bind:value={proposedPurchase.arguments.item_name} />
        </label>
        <label>
          Quantity:
          <input type="number" step="0.01" bind:value={proposedPurchase.arguments.quantity} />
        </label>
        <!-- More fields... -->
        
        <div class="actions">
          <button type="submit" class="btn btn-success">✓ Confirm</button>
          <button type="button" class="btn btn-secondary" on:click={cancelPurchase}>✗ Cancel</button>
        </div>
      </form>
    </div>
  {/if}
</div>

<style>
  .confirmation-card {
    border: 2px solid var(--primary);
    padding: 1rem;
    border-radius: 8px;
    background: var(--bg-secondary);
  }
  
  .purchase-details {
    margin: 1rem 0;
    padding: 1rem;
    background: var(--bg-primary);
    border-radius: 4px;
  }
  
  .actions {
    display: flex;
    gap: 1rem;
    margin-top: 1rem;
  }
</style>
```

---

## Authentication & Authorization

### Firebase Auth Setup

```javascript
// src/lib/firebase.js
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  // ... other config
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

### Auth Store (Svelte)

```javascript
// src/lib/stores/auth.js
import { writable } from 'svelte/store';
import { auth } from '$lib/firebase';
import { 
  signInWithEmailAndPassword, 
  signOut as firebaseSignOut,
  onAuthStateChanged 
} from 'firebase/auth';

function createAuthStore() {
  const { subscribe, set, update } = writable({
    user: null,
    token: null,
    loading: true
  });

  // Listen for auth state changes
  onAuthStateChanged(auth, async (user) => {
    if (user) {
      // Get Firebase ID token
      const token = await user.getIdToken();
      
      set({
        user: {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName
        },
        token,
        loading: false
      });
    } else {
      set({ user: null, token: null, loading: false });
    }
  });

  return {
    subscribe,
    signIn: async (email, password) => {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const token = await userCredential.user.getIdToken();
      return token;
    },
    signOut: async () => {
      await firebaseSignOut(auth);
      set({ user: null, token: null, loading: false });
    }
  };
}

export const authStore = createAuthStore();
```

### API Client with Auth

```javascript
// src/lib/api/client.js
import { authStore } from '$lib/stores/auth';
import { get } from 'svelte/store';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  async request(endpoint, options = {}) {
    const auth = get(authStore);
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    // Add Bearer token if authenticated
    if (auth.token) {
      headers['Authorization'] = `Bearer ${auth.token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        // Token expired, redirect to login
        await authStore.signOut();
        window.location.href = '/login';
      }
      throw new Error(`API error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  get(endpoint) {
    return this.request(endpoint);
  }
  
  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
  
  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }
  
  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
```

---

## Testing Strategy

### Backend Tests

```python
# tests/test_ingredient_service.py
import pytest
from uuid import uuid4
from src.services.ingredient_service import IngredientService
from src.models import Ingredient

@pytest.fixture
def tenant_ids():
    """Generate two distinct tenant IDs for isolation testing"""
    return {
        'tenant_a': uuid4(),
        'tenant_b': uuid4()
    }

def test_create_ingredient_with_tenant(session, tenant_ids):
    """Test ingredient creation includes tenant_id"""
    service = IngredientService(session)
    
    ingredient = service.create_ingredient(
        tenant_id=tenant_ids['tenant_a'],
        name="Flour",
        category="Dry Goods"
    )
    
    assert ingredient.id is not None
    assert ingredient.tenant_id == tenant_ids['tenant_a']
    assert ingredient.name == "Flour"

def test_tenant_isolation(session, tenant_ids):
    """CRITICAL: Verify tenants cannot see each other's data"""
    service = IngredientService(session)
    
    # Tenant A creates flour
    flour_a = service.create_ingredient(
        tenant_id=tenant_ids['tenant_a'],
        name="Flour",
        category="Dry Goods"
    )
    
    # Tenant B creates sugar
    sugar_b = service.create_ingredient(
        tenant_id=tenant_ids['tenant_b'],
        name="Sugar",
        category="Sweeteners"
    )
    
    # Tenant A should only see flour
    tenant_a_ingredients = service.list_ingredients(tenant_ids['tenant_a'])
    assert len(tenant_a_ingredients) == 1
    assert tenant_a_ingredients[0].name == "Flour"
    
    # Tenant B should only see sugar
    tenant_b_ingredients = service.list_ingredients(tenant_ids['tenant_b'])
    assert len(tenant_b_ingredients) == 1
    assert tenant_b_ingredients[0].name == "Sugar"
    
    # Tenant A cannot access Tenant B's ingredient by ID
    result = service.get_ingredient(tenant_ids['tenant_a'], sugar_b.id)
    assert result is None  # Should not find Tenant B's ingredient

def test_rls_prevents_cross_tenant_access(session, tenant_ids):
    """Test PostgreSQL RLS blocks cross-tenant queries"""
    service = IngredientService(session)
    
    # Create ingredient for Tenant A
    ingredient = service.create_ingredient(
        tenant_id=tenant_ids['tenant_a'],
        name="Flour",
        category="Dry Goods"
    )
    
    # Set session variable to Tenant B
    session.execute(
        text("SET app.current_tenant = :tenant_id"),
        {"tenant_id": str(tenant_ids['tenant_b'])}
    )
    
    # Try to query Tenant A's ingredient (should fail)
    result = session.query(Ingredient).filter_by(id=ingredient.id).first()
    assert result is None  # RLS blocks access
```

### API Integration Tests

```python
# tests/test_api_ingredients.py
from fastapi.testclient import TestClient
from src.main import app
from uuid import uuid4

client = TestClient(app)

def test_create_ingredient_requires_auth():
    """Unauthenticated requests should be rejected"""
    response = client.post("/api/ingredients", json={
        "name": "Flour",
        "category": "Dry Goods"
    })
    assert response.status_code == 401

def test_create_ingredient_with_auth(auth_token_tenant_a):
    """Authenticated users can create ingredients"""
    response = client.post(
        "/api/ingredients",
        json={"name": "Flour", "category": "Dry Goods"},
        headers={"Authorization": f"Bearer {auth_token_tenant_a}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Flour"
    assert "id" in data

def test_list_ingredients_tenant_isolation(
    auth_token_tenant_a, 
    auth_token_tenant_b
):
    """Each tenant only sees their own ingredients"""
    # Tenant A creates flour
    client.post(
        "/api/ingredients",
        json={"name": "Flour", "category": "Dry Goods"},
        headers={"Authorization": f"Bearer {auth_token_tenant_a}"}
    )
    
    # Tenant B creates sugar
    client.post(
        "/api/ingredients",
        json={"name": "Sugar", "category": "Sweeteners"},
        headers={"Authorization": f"Bearer {auth_token_tenant_b}"}
    )
    
    # Tenant A sees only flour
    response_a = client.get(
        "/api/ingredients",
        headers={"Authorization": f"Bearer {auth_token_tenant_a}"}
    )
    ingredients_a = response_a.json()
    assert len(ingredients_a) == 1
    assert ingredients_a[0]["name"] == "Flour"
    
    # Tenant B sees only sugar
    response_b = client.get(
        "/api/ingredients",
        headers={"Authorization": f"Bearer {auth_token_tenant_b}"}
    )
    ingredients_b = response_b.json()
    assert len(ingredients_b) == 1
    assert ingredients_b[0]["name"] == "Sugar"
```

---

## Deployment

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Environment variables (set via hosting platform)
ENV PYTHONPATH=/app
ENV PORT=8000

# Run migrations and start server
CMD alembic upgrade head && \
    uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

### Railway Configuration

```yaml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[env]
PYTHONPATH = "/app"
```

### Environment Variables

```bash
# Production environment variables
DATABASE_URL=postgresql://user:pass@host:5432/baketracker
FIREBASE_ADMIN_SDK_JSON={"type":"service_account",...}
GEMINI_API_KEY=AIza...
SECRET_KEY=your-secret-key
ENVIRONMENT=production
CORS_ORIGINS=https://app.baketracker.com
S3_BUCKET=baketracker-uploads
S3_REGION=us-east-1
SENTRY_DSN=https://...@sentry.io/...
```

---

## Security Checklist

### Pre-Launch Security Audit

- [ ] **Authentication**
  - [ ] JWT tokens expire (1 hour max)
  - [ ] Refresh token rotation implemented
  - [ ] Password requirements enforced (8+ chars, complexity)
  - [ ] Rate limiting on login endpoint (5 attempts/15 min)

- [ ] **Authorization**
  - [ ] All API endpoints require authentication
  - [ ] Tenant isolation verified (100% test coverage)
  - [ ] PostgreSQL RLS policies active on all tenant-scoped tables
  - [ ] Admin vs. member role enforcement

- [ ] **Data Protection**
  - [ ] All database queries use parameterized queries (prevent SQL injection)
  - [ ] User input sanitized before storage
  - [ ] HTTPS enforced (HSTS headers)
  - [ ] Sensitive data encrypted at rest (database encryption)

- [ ] **API Security**
  - [ ] CORS configured (whitelist specific origins)
  - [ ] CSRF protection on state-changing endpoints
  - [ ] Rate limiting on all endpoints (100 req/min per user)
  - [ ] Request size limits (10MB max)
  - [ ] XSS prevention (Svelte auto-escaping)

- [ ] **Secrets Management**
  - [ ] No secrets in code or git history
  - [ ] Environment variables for all credentials
  - [ ] Firebase Admin SDK private key secured
  - [ ] Gemini API key scoped to production domain

- [ ] **Monitoring**
  - [ ] Error tracking (Sentry) configured
  - [ ] Security event logging (failed logins, unauthorized access)
  - [ ] Database connection monitoring
  - [ ] API response time tracking

---

## Performance Optimization

### Database Indexes

```sql
-- Essential indexes for multi-tenant queries
CREATE INDEX idx_ingredients_tenant_name 
ON ingredients(tenant_id, name);

CREATE INDEX idx_recipes_tenant_name 
ON recipes(tenant_id, name);

CREATE INDEX idx_events_tenant_date 
ON events(tenant_id, event_date);

CREATE INDEX idx_purchases_tenant_date 
ON purchases(tenant_id, purchase_date DESC);

-- Composite indexes for common queries
CREATE INDEX idx_pantry_items_tenant_ingredient 
ON pantry_items(tenant_id, ingredient_id);
```

### API Response Caching

```python
# src/api/cache.py
from functools import wraps
from cachetools import TTLCache
import hashlib

# Cache for 5 minutes
cache = TTLCache(maxsize=1000, ttl=300)

def cached(key_prefix: str):
    """Cache decorator for API responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from tenant_id + function args
            tenant_id = kwargs.get('tenant_id')
            cache_key = f"{key_prefix}:{tenant_id}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            # Check cache
            if cache_key in cache:
                return cache[cache_key]
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache[cache_key] = result
            return result
        return wrapper
    return decorator

# Usage
@router.get("/api/ingredients")
@cached("ingredients_list")
async def list_ingredients(tenant_id: UUID = Depends(get_tenant_id)):
    # ... implementation
```

### Frontend Bundle Optimization

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks
          'vendor-svelte': ['svelte'],
          'vendor-firebase': ['firebase/app', 'firebase/auth'],
          'vendor-gemini': ['@google/generative-ai']
        }
      }
    }
  }
});
```

---

## Monitoring & Observability

### Health Check Endpoint

```python
# src/api/routes/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
async def health_check(session = Depends(get_db_session)):
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        session.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }, 503
```

### Structured Logging

```python
# src/utils/logger.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for aggregation"""
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        
        if hasattr(record, 'tenant_id'):
            log_obj['tenant_id'] = str(record.tenant_id)
        
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

# Configure logger
logger = logging.getLogger('baketracker')
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

---

## Appendix: Useful Commands

### Local Development

```bash
# Start PostgreSQL (Docker)
docker run -d --name baketracker-db \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=baketracker \
  -p 5432:5432 \
  postgres:15

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start Svelte dev server
cd frontend && npm run dev

# Run tests
pytest tests/ -v --cov=src
```

### Database Management

```bash
# Create migration
alembic revision --autogenerate -m "Add tenant_id to ingredients"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1

# PostgreSQL CLI
psql -h localhost -U postgres -d baketracker
```

### Deployment

```bash
# Deploy to Railway (via CLI)
railway up

# View logs
railway logs

# Run migrations on production
railway run alembic upgrade head

# SSH into container (if needed)
railway run bash
```

---

**Document Status**: Ready for implementation
**Next Steps**: Review with senior developer, begin Phase 0 POC
