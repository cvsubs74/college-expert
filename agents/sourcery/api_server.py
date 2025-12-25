"""
DataMine API Server

FastAPI backend for the DataMine goal-to-data pipeline.
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Setup paths
AGENT_DIR = Path(__file__).parent
CONFIGS_DIR = AGENT_DIR / "configs"
CONFIGS_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(AGENT_DIR))

# Load environment
env_path = AGENT_DIR.parent / "university_profile_collector" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import ADK components
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# ============== PYDANTIC MODELS ==============

class GoalRequest(BaseModel):
    goal: str
    examples: Optional[List[str]] = None


class DataCategory(BaseModel):
    name: str
    description: str
    fields: List[str]
    priority: str = "high"


class SchemaField(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class GeneratedSchema(BaseModel):
    goal: str
    categories: List[DataCategory]
    schema: Dict[str, Any]


class SourceRequest(BaseModel):
    schema: Dict[str, Any]
    categories: List[str]


# ============== GCS STORAGE ==============
GCS_BUCKET_NAME = os.getenv("GCS_DATAMINE_BUCKET", "datamine-configs")
USE_GCS = os.getenv("USE_GCS", "true").lower() == "true"


def save_config_to_storage(config_id: str, data: dict):
    """Save config to GCS and local file."""
    yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    # Save locally
    config_path = CONFIGS_DIR / f"{config_id}.yaml"
    with open(config_path, 'w') as f:
        f.write(yaml_content)
    
    # Save to GCS if available
    if USE_GCS:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(f"configs/{config_id}.yaml")
            blob.upload_from_string(yaml_content, content_type='text/yaml')
            logger.info(f"Saved {config_id} to GCS")
        except Exception as e:
            logger.warning(f"GCS save failed: {e}")


# ============== LIFESPAN ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DataMine API starting...")
    yield
    logger.info("DataMine API shutting down...")


# ============== FASTAPI APP ==============

app = FastAPI(
    title="DataMine API",
    description="Goal-to-data pipeline API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== API ROUTES ==============

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "datamine"}


@app.post("/api/analyze-goal")
async def analyze_goal(request: GoalRequest):
    """Analyze a goal and suggest data categories."""
    
    # Use Gemini to analyze the goal
    from google import genai
    
    client = genai.Client()
    
    prompt = f"""You are a data architect. Analyze this research goal and suggest what data categories would be useful to collect.

Goal: {request.goal}

Return a JSON object with this structure:
{{
  "summary": "Brief summary of the research domain",
  "categories": [
    {{
      "name": "Category Name",
      "description": "What this category covers",
      "fields": ["field1", "field2", "field3"],
      "priority": "high" or "medium" or "low"
    }}
  ]
}}

Suggest 4-6 categories with 3-6 fields each. Focus on actionable, collectible data."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        return {
            "success": True,
            "goal": request.goal,
            "analysis": result
        }
    except Exception as e:
        logger.error(f"Goal analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/generate-schema")
async def generate_schema(request: dict):
    """Generate a JSON schema from approved categories."""
    
    goal = request.get("goal", "")
    categories = request.get("categories", [])
    
    from google import genai
    client = genai.Client()
    
    prompt = f"""You are a JSON Schema architect. Create a detailed JSON Schema for collecting this data.

Goal: {goal}

Categories to include:
{json.dumps(categories, indent=2)}

Return a valid JSON Schema (draft-07) with:
1. Proper type definitions
2. Descriptions for each field
3. Required fields marked
4. Nested objects where appropriate

Return ONLY the JSON Schema object, no explanation."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        schema = json.loads(response.text)
        
        # Generate config ID
        config_id = f"dm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "success": True,
            "config_id": config_id,
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Schema generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/discover-sources")
async def discover_sources(request: dict):
    """Discover sources that can fill the schema."""
    
    schema = request.get("schema", {})
    goal = request.get("goal", "")
    
    from google import genai
    client = genai.Client()
    
    prompt = f"""You are a data source discovery expert. Find potential data sources for this schema.

Goal: {goal}

Schema fields to fill:
{json.dumps(schema.get('properties', {}), indent=2)}

For each major field or category, suggest data sources:
1. APIs (with actual URLs if known)
2. Government databases
3. Official websites
4. PDF reports/documents

Return JSON:
{{
  "sources": [
    {{
      "name": "Source Name",
      "type": "API" or "PDF" or "WEB",
      "url": "https://...",
      "description": "What data this provides",
      "fields_covered": ["field1", "field2"],
      "reliability": "high" or "medium" or "low",
      "api_key_required": true or false
    }}
  ]
}}

Focus on reliable, authoritative sources. Include real URLs when possible."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        return {
            "success": True,
            "sources": result.get("sources", [])
        }
    except Exception as e:
        logger.error(f"Source discovery failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/save-config")
async def save_config(request: dict):
    """Save finalized config to storage."""
    
    config_id = request.get("config_id", f"dm_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    config = {
        "config_id": config_id,
        "goal": request.get("goal", ""),
        "created_at": datetime.now().isoformat(),
        "schema": request.get("schema", {}),
        "sources": request.get("sources", []),
        "source_patterns": request.get("source_patterns", {}),
        "entities": request.get("entities", {}),
        "status": "ready"
    }
    
    save_config_to_storage(config_id, config)
    
    return {
        "success": True,
        "config_id": config_id,
        "message": f"Config saved as {config_id}"
    }


@app.post("/api/discover-samples")
async def discover_samples(request: dict):
    """
    Sample Source Agent: Pick 5 sample entities and find their sources.
    Uses ADK agent with Google Search to prevent hallucination.
    This is Phase 2 Step 1 of the agent-driven architecture.
    """
    
    goal = request.get("goal", "")
    schema = request.get("schema", {})
    
    try:
        # Import ADK agent
        from sub_agents import sample_discovery_agent
        
        # Create runner with session
        session_service = InMemorySessionService()
        runner = Runner(
            agent=sample_discovery_agent,
            app_name="datamine_sample_discovery",
            session_service=session_service
        )
        
        # Create session with goal and schema
        session = await runner.session_service.create_session()
        await session.add_context_variables({
            "goal": goal,
            "schema": schema
        })
        
        # Run agent
        response = await runner.run(
            user_prompt=f"Discover 5 sample entities for this research goal: {goal}",
            session_id=session.session_id
        )
        
        # Extract result from session state
        result = session.get_context_variable("sample_discovery_result")
        
        if result:
            return {
                "success": True,
                "entity_type": result.get("entity_type", "entity"),
                "entity_type_plural": result.get("entity_type_plural", "entities"),
                "samples": result.get("samples", [])
            }
        else:
            return {
                "success": False,
                "error": "Agent did not produce sample_discovery_result"
            }
            
    except Exception as e:
        logger.error(f"Sample discovery failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/derive-structure")
async def derive_structure(request: dict):
    """
    Structure Discovery Agent: Analyze 5 sample source mappings to derive
    generalized YAML patterns (universal, parametric, entity-specific).
    This is Phase 2 Step 2 of the agent-driven architecture.
    """
    
    samples = request.get("samples", [])
    entity_type = request.get("entity_type", "entity")
    goal = request.get("goal", "")
    
    from google import genai
    client = genai.Client()
    
    prompt = f"""You are a data architecture pattern analyst. Analyze these 5 sample entities and their sources to derive generalizable patterns.

Entity Type: {entity_type}
Goal: {goal}

Sample Data:
{json.dumps(samples, indent=2)}

Analyze the sources across all 5 samples and categorize them into:

1. **UNIVERSAL SOURCES**: Same URL/API for all entities (just change a parameter)
   - Example: College Scorecard API works for all universities
   
2. **PARAMETRIC SOURCES**: URL follows a pattern with entity-specific parts
   - Example: {{domain}}/cds/CDS_2024.pdf (domain changes per entity)
   
3. **ENTITY-SPECIFIC DISCOVERY**: No pattern, must discover per entity
   - Example: Special research centers with unique URLs

Return JSON:
{{
  "source_patterns": {{
    "universal": [
      {{
        "name": "College Scorecard API",
        "type": "API",
        "base_url": "https://api.data.gov/ed/collegescorecard/v1/schools",
        "entity_lookup_param": "school.name",
        "api_key_required": true,
        "fields_covered": ["costs", "outcomes"]
      }}
    ],
    "parametric": [
      {{
        "name": "Common Data Set",
        "type": "PDF",
        "url_pattern": "https://{{{{domain}}}}/cds/CDS_{{{{year}}}}.pdf",
        "discovery_query": "{{{{entity_name}}}} common data set PDF",
        "fields_covered": ["admissions", "enrollment"]
      }}
    ],
    "entity_specific_discovery": {{
      "method": "web_search",
      "queries": [
        "{{{{entity_name}}}} institutional research data",
        "{{{{entity_name}}}} statistics facts"
      ]
    }}
  }},
  "required_identifiers": ["domain", "official_name"],
  "pattern_confidence": "high"
}}

Be very specific about which patterns you see across all 5 samples."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        return {
            "success": True,
            "source_patterns": result.get("source_patterns", {}),
            "required_identifiers": result.get("required_identifiers", []),
            "pattern_confidence": result.get("pattern_confidence", "medium")
        }
    except Exception as e:
        logger.error(f"Structure derivation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/discover-entities")
async def discover_entities(request: dict):
    """
    Entity Discovery Agent: Build comprehensive entity list based on goal.
    Uses ADK agent with Google Search to find REAL entity lists.
    This is Phase 3 of the agent-driven architecture.
    """
    
    goal = request.get("goal", "")
    entity_type = request.get("entity_type", "entity")
    
    try:
        # Import ADK agent
        from sub_agents import entity_discovery_agent
        
        # Create runner with session
        session_service = InMemorySessionService()
        runner = Runner(
            agent=entity_discovery_agent,
            app_name="datamine_entity_discovery",
            session_service=session_service
        )
        
        # Create session with goal and entity_type
        session = await runner.session_service.create_session()
        await session.add_context_variables({
            "goal": goal,
            "entity_type": entity_type
        })
        
        # Run agent
        response = await runner.run(
            user_prompt=f"Discover a comprehensive list of {entity_type}s for this goal: {goal}",
            session_id=session.session_id
        )
        
        # Extract result from session state
        result = session.get_context_variable("entity_discovery_result")
        
        if result:
            return {
                "success": True,
                "total_count": result.get("total_count", 0),
                "categories": result.get("categories", [])
            }
        else:
            return {
                "success": False,
                "error": "Agent did not produce entity_discovery_result"
            }
            
    except Exception as e:
        logger.error(f"Entity discovery failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/configs")
async def list_configs():
    """List all saved configs."""
    configs = []
    
    for f in CONFIGS_DIR.glob("*.yaml"):
        with open(f) as file:
            data = yaml.safe_load(file)
            configs.append({
                "config_id": data.get("config_id", f.stem),
                "goal": data.get("goal", ""),
                "created_at": data.get("created_at", ""),
                "status": data.get("status", "unknown")
            })
    
    return {"configs": sorted(configs, key=lambda x: x.get("created_at", ""), reverse=True)}


@app.get("/api/configs/{config_id}")
async def get_config(config_id: str):
    """Get a specific config."""
    config_path = CONFIGS_DIR / f"{config_id}.yaml"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    return data


# ============== STATIC FILE SERVING ==============

UI_DIR = AGENT_DIR / "ui" / "dist"

if UI_DIR.exists():
    app.mount("/assets", StaticFiles(directory=UI_DIR / "assets"), name="assets")
    
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = UI_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(UI_DIR / "index.html")


# ============== MAIN ==============

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
