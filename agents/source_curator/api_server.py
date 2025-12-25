"""
FastAPI Server for Source Curator Agent

Exposes the source curator agent as a REST API for the React frontend.
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
from io import BytesIO

import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Setup paths
AGENT_DIR = Path(__file__).parent
SOURCES_DIR = AGENT_DIR / "sources" / "universities"
API_KEYS_FILE = AGENT_DIR / ".api_keys.json"
sys.path.insert(0, str(AGENT_DIR))

# Load environment
env_path = AGENT_DIR.parent / "university_profile_collector" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import agent components
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import root_agent
from tools import validate_url

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store for discovery jobs
discovery_jobs = {}

# In-memory API key cache (loaded from file on startup)
api_keys_cache = {}

# ============== CLOUD STORAGE CONFIGURATION ==============
GCS_BUCKET_NAME = os.getenv("GCS_SOURCES_BUCKET", "college-counselor-sources")
USE_GCS = os.getenv("USE_GCS", "true").lower() == "true"
_gcs_client = None
_gcs_bucket = None


def get_gcs_bucket():
    """Get or create GCS bucket client."""
    global _gcs_client, _gcs_bucket
    
    if not USE_GCS:
        return None
        
    if _gcs_bucket is None:
        try:
            from google.cloud import storage
            _gcs_client = storage.Client()
            _gcs_bucket = _gcs_client.bucket(GCS_BUCKET_NAME)
            logger.info(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
        except Exception as e:
            logger.warning(f"GCS not available: {e}. Falling back to local storage.")
            return None
    return _gcs_bucket


def save_yaml_to_storage(university_id: str, data: dict):
    """Save YAML to GCS (if available) and local file."""
    yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    # Always save locally as backup
    yaml_path = SOURCES_DIR / f"{university_id}.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    
    # Also save to GCS if available
    bucket = get_gcs_bucket()
    if bucket:
        try:
            blob = bucket.blob(f"universities/{university_id}.yaml")
            blob.upload_from_string(yaml_content, content_type='text/yaml')
            logger.info(f"Uploaded {university_id}.yaml to GCS")
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")


def load_yaml_from_storage(university_id: str) -> Optional[dict]:
    """Load YAML from GCS (if available) or local file."""
    bucket = get_gcs_bucket()
    
    # Try GCS first
    if bucket:
        try:
            blob = bucket.blob(f"universities/{university_id}.yaml")
            if blob.exists():
                content = blob.download_as_text()
                logger.info(f"Loaded {university_id}.yaml from GCS")
                return yaml.safe_load(content)
        except Exception as e:
            logger.warning(f"Failed to load from GCS: {e}")
    
    # Fall back to local
    yaml_path = SOURCES_DIR / f"{university_id}.yaml"
    if yaml_path.exists():
        with open(yaml_path, 'r') as f:
            return yaml.safe_load(f)
    
    return None


def list_yamls_from_storage() -> list:
    """List all university YAMLs from storage."""
    universities = []
    
    bucket = get_gcs_bucket()
    if bucket:
        try:
            blobs = bucket.list_blobs(prefix="universities/")
            for blob in blobs:
                if blob.name.endswith('.yaml'):
                    uni_id = blob.name.replace("universities/", "").replace(".yaml", "")
                    universities.append(uni_id)
            if universities:
                logger.info(f"Found {len(universities)} universities in GCS")
                return universities
        except Exception as e:
            logger.warning(f"Failed to list GCS: {e}")
    
    # Fall back to local
    if SOURCES_DIR.exists():
        for f in SOURCES_DIR.glob("*.yaml"):
            universities.append(f.stem)
    
    return universities


def load_api_keys():
    """Load API keys from file."""
    global api_keys_cache
    if API_KEYS_FILE.exists():
        try:
            with open(API_KEYS_FILE, 'r') as f:
                api_keys_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            api_keys_cache = {}


def save_api_keys():
    """Save API keys to file."""
    try:
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(api_keys_cache, f)
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")


def get_api_key(key_name: str) -> Optional[str]:
    """Get API key from cache, env, or return None."""
    # First check env var
    env_key = os.getenv(key_name)
    if env_key:
        return env_key
    # Then check cache
    return api_keys_cache.get(key_name)


# Pydantic models
class DiscoveryRequest(BaseModel):
    university_name: str


class APIKeyInput(BaseModel):
    key_name: str
    api_key: str


class SourceUpdate(BaseModel):
    url: Optional[str] = None
    is_active: Optional[bool] = None
    extraction_config: Optional[dict] = None
    notes: Optional[str] = None


class DiscoveryStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    university_name: str
    steps: list
    result: Optional[dict] = None
    error: Optional[str] = None


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    load_api_keys()
    logger.info("Source Curator API started")
    yield
    # Shutdown
    logger.info("Source Curator API shutting down")


app = FastAPI(
    title="Source Curator API",
    description="API for discovering and curating university data sources",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_discovery(job_id: str, university_name: str):
    """Background task to run source discovery."""
    job = discovery_jobs[job_id]
    job["status"] = "running"
    job["steps"].append({"time": datetime.now().isoformat(), "step": "Started discovery"})
    
    try:
        # Create session service
        session_service = InMemorySessionService()
        
        # Create runner
        runner = Runner(
            agent=root_agent,
            app_name="source_curator_api",
            session_service=session_service
        )
        
        # Create session with initial state
        university_id = university_name.lower().replace(" ", "_").replace(",", "")
        session = await session_service.create_session(
            app_name="source_curator_api",
            user_id="api_user",
            state={
                "university_name": university_name,
                "university_id": university_id
            }
        )
        
        # Create message
        query = f"Find and curate sources for: {university_name}"
        message_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )
        
        job["steps"].append({"time": datetime.now().isoformat(), "step": "Running agents..."})
        
        # Run the agent
        async for event in runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=message_content
        ):
            # Log events for debugging
            if hasattr(event, 'author'):
                job["steps"].append({
                    "time": datetime.now().isoformat(),
                    "step": f"Agent: {event.author}"
                })
        
        # Get the generated YAML and save to GCS
        yaml_path = SOURCES_DIR / f"{university_id}.yaml"
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                result = yaml.safe_load(f)
            
            # Save to GCS for persistence
            save_yaml_to_storage(university_id, result)
            
            job["result"] = result
            job["status"] = "completed"
            job["steps"].append({"time": datetime.now().isoformat(), "step": "Discovery completed and saved to cloud"})
        else:
            job["status"] = "failed"
            job["error"] = "YAML file was not generated"
            
    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        job["status"] = "failed"
        job["error"] = str(e)
        job["steps"].append({"time": datetime.now().isoformat(), "step": f"Error: {str(e)}"})


# ============== API ROUTES (must be defined before static file catch-all) ==============

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# API configuration for required keys
API_KEY_CONFIGS = {
    "DATA_GOV_API_KEY": {
        "name": "College Scorecard API Key",
        "description": "Required for accessing U.S. Department of Education College Scorecard data",
        "signup_url": "https://api.data.gov/signup/",
        "docs_url": "https://collegescorecard.ed.gov/data/documentation/",
        "apis": ["college_scorecard"]
    }
}


@app.get("/api/keys")
async def get_api_keys_status():
    """Get status of all required API keys."""
    keys_status = {}
    for key_name, config in API_KEY_CONFIGS.items():
        has_key = bool(get_api_key(key_name))
        keys_status[key_name] = {
            **config,
            "configured": has_key,
            "source": "environment" if os.getenv(key_name) else ("cached" if api_keys_cache.get(key_name) else None)
        }
    return {"keys": keys_status}


@app.post("/api/keys")
async def save_api_key(input: APIKeyInput):
    """Save an API key for later use."""
    if input.key_name not in API_KEY_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown key: {input.key_name}")
    
    # Store in cache and persist to file
    api_keys_cache[input.key_name] = input.api_key
    save_api_keys()
    
    logger.info(f"Saved API key: {input.key_name}")
    
    return {
        "success": True,
        "key_name": input.key_name,
        "message": f"API key '{API_KEY_CONFIGS[input.key_name]['name']}' saved successfully"
    }
class APIKeyTest(BaseModel):
    test_key: str


@app.post("/api/keys/{key_name}/test")
async def test_api_key(key_name: str, body: Optional[APIKeyTest] = None):
    """Test an API key without saving it."""
    if key_name not in API_KEY_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown key: {key_name}")
    
    # Get key from body or from stored keys
    test_key = body.test_key if body else None
    api_key = test_key or get_api_key(key_name)
    
    if not api_key:
        return {
            "success": False,
            "error": "No API key provided or configured",
            "config": API_KEY_CONFIGS[key_name]
        }
    
    # Test the key based on type
    import requests
    
    if key_name == "DATA_GOV_API_KEY":
        try:
            # Fetch sample data to test and show results
            fields = [
                "school.name",
                "school.city", 
                "school.state",
                "latest.admissions.admission_rate.overall",
                "latest.cost.tuition.in_state",
                "latest.cost.tuition.out_of_state",
                "latest.student.size"
            ]
            
            response = requests.get(
                "https://api.data.gov/ed/collegescorecard/v1/schools",
                params={
                    "api_key": api_key, 
                    "per_page": 3,  # Get 3 schools as sample
                    "fields": ",".join(fields),
                    "school.operating": 1  # Active schools only
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Format sample data
                sample_schools = []
                for school in results[:3]:
                    sample_schools.append({
                        "name": school.get("school.name"),
                        "location": f"{school.get('school.city')}, {school.get('school.state')}",
                        "admission_rate": school.get("latest.admissions.admission_rate.overall"),
                        "tuition_in_state": school.get("latest.cost.tuition.in_state"),
                        "tuition_out_of_state": school.get("latest.cost.tuition.out_of_state"),
                        "student_size": school.get("latest.student.size")
                    })
                
                return {
                    "success": True,
                    "message": f"✅ API key valid! Retrieved {len(results)} schools.",
                    "sample_data": sample_schools,
                    "total_available": data.get("metadata", {}).get("total", 0)
                }
            elif response.status_code == 403:
                return {"success": False, "error": "Invalid API key - access denied"}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}: {response.text[:100]}"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "API request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Unknown key type"}


@app.post("/api/discover", response_model=DiscoveryStatus)
async def start_discovery(request: DiscoveryRequest, background_tasks: BackgroundTasks):
    """Start source discovery for a university."""
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.university_name.lower().replace(' ', '_')[:20]}"
    
    discovery_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "university_name": request.university_name,
        "steps": [{"time": datetime.now().isoformat(), "step": "Job created"}],
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_discovery, job_id, request.university_name)
    
    return DiscoveryStatus(**discovery_jobs[job_id])


@app.get("/api/discover/{job_id}", response_model=DiscoveryStatus)
async def get_discovery_status(job_id: str):
    """Get status of a discovery job."""
    if job_id not in discovery_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return DiscoveryStatus(**discovery_jobs[job_id])


@app.get("/api/sources")
async def list_sources():
    """List all discovered source configurations."""
    sources = []
    if SOURCES_DIR.exists():
        for yaml_file in SOURCES_DIR.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                sources.append({
                    "university_id": data.get("university_id", yaml_file.stem),
                    "official_name": data.get("official_name", yaml_file.stem),
                    "ipeds_id": data.get("ipeds_id"),
                    "file": yaml_file.name
                })
            except Exception as e:
                logger.error(f"Error reading {yaml_file}: {e}")
    return {"sources": sources}


@app.get("/api/sources/{university_id}")
async def get_source(university_id: str):
    """Get a specific source configuration."""
    data = load_yaml_from_storage(university_id)
    if not data:
        raise HTTPException(status_code=404, detail="Source not found")
    return data


@app.put("/api/sources/{university_id}/{source_key}")
async def update_source(university_id: str, source_key: str, update: SourceUpdate):
    """Update a specific source within a config."""
    data = load_yaml_from_storage(university_id)
    if not data:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Find and update the source
    if "sources" in data and source_key in data["sources"]:
        source = data["sources"][source_key].get("primary", data["sources"][source_key])
        
        if update.url is not None:
            source["url"] = update.url
        if update.is_active is not None:
            source["is_active"] = update.is_active
            if update.is_active:
                source["last_validated"] = datetime.now().strftime("%Y-%m-%d")
        if update.extraction_config is not None:
            source["extraction_config"] = update.extraction_config
        if update.notes is not None:
            source["notes"] = update.notes
        
        # Save to GCS
        save_yaml_to_storage(university_id, data)
        
        return {"success": True, "updated": source_key}
    else:
        raise HTTPException(status_code=404, detail=f"Source key '{source_key}' not found")


@app.post("/api/sources/{university_id}/{source_key}/validate")
async def validate_source_url(university_id: str, source_key: str):
    """Re-validate a source URL or API with actual data fetching."""
    data = load_yaml_from_storage(university_id)
    if not data:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if "sources" not in data or source_key not in data["sources"]:
        raise HTTPException(status_code=404, detail=f"Source key '{source_key}' not found")
    
    source = data["sources"][source_key].get("primary", data["sources"][source_key])
    url = source.get("url")
    source_type = source.get("source_type", "WEB")
    extraction_config = source.get("extraction_config", {})
    ipeds_id = data.get("ipeds_id") or extraction_config.get("ipeds_id") or extraction_config.get("unitid")
    
    if not url:
        raise HTTPException(status_code=400, detail="Source has no URL")
    
    # Check if this is an API source that needs special validation
    if source_type == "API" or "api.data.gov" in url or "educationdata.urban.org" in url:
        result = await validate_api_source(source_key, url, ipeds_id, extraction_config)
    else:
        # Enhanced URL validation with content fetch
        result = await validate_web_url(url)
    
    # Save validation result to YAML
    if result.get("accessible"):
        source["is_active"] = True
        source["last_validated"] = datetime.now().strftime("%Y-%m-%d")
        source["notes"] = f"Validated successfully on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    else:
        source["is_active"] = False
        source["notes"] = f"Validation failed: {result.get('error', 'Unknown error')}"
    
    # Save to GCS
    save_yaml_to_storage(university_id, data)
    
    return {
        "source_key": source_key,
        "url": url,
        "source_type": source_type,
        "validation": result
    }


async def validate_web_url(url: str) -> dict:
    """Validate a web URL and fetch content preview."""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CollegeCounselor/1.0'
        }
        
        response = requests.get(url, timeout=15, allow_redirects=True, headers=headers)
        
        content_type = response.headers.get("Content-Type", "unknown")
        is_pdf = "pdf" in content_type.lower() or url.lower().endswith(".pdf")
        is_html = "html" in content_type.lower()
        
        result = {
            "url": url,
            "accessible": response.status_code == 200,
            "status_code": response.status_code,
            "content_type": content_type,
            "is_pdf": is_pdf,
            "is_html": is_html,
            "final_url": response.url
        }
        
        if response.status_code == 200:
            if is_html:
                # Parse HTML and extract preview
                try:
                    soup = BeautifulSoup(response.text[:50000], 'html.parser')
                    
                    # Get title
                    title = soup.find('title')
                    title_text = title.get_text().strip() if title else None
                    
                    # Get meta description
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    description = meta_desc.get('content', '').strip() if meta_desc else None
                    
                    # Get headings for content preview
                    headings = []
                    for h in soup.find_all(['h1', 'h2', 'h3'])[:5]:
                        text = h.get_text().strip()
                        if text and len(text) < 100:
                            headings.append(text)
                    
                    # Count links and tables (useful for data pages)
                    links = len(soup.find_all('a'))
                    tables = len(soup.find_all('table'))
                    
                    result["sample_data"] = {
                        "title": title_text,
                        "description": description,
                        "headings": headings[:5],
                        "link_count": links,
                        "table_count": tables,
                        "content_length": len(response.text)
                    }
                    result["message"] = f"✅ Page loaded: {title_text or 'No title'}"
                    
                except Exception as e:
                    result["sample_data"] = {"parse_error": str(e)}
                    result["message"] = "✅ URL accessible but could not parse HTML"
                    
            elif is_pdf:
                result["sample_data"] = {
                    "file_size": len(response.content),
                    "file_type": "PDF"
                }
                result["message"] = f"✅ PDF accessible ({len(response.content) / 1024:.1f} KB)"
            else:
                result["sample_data"] = {
                    "content_length": len(response.content),
                    "content_type": content_type
                }
                result["message"] = f"✅ Content accessible ({content_type})"
        else:
            result["error"] = f"HTTP {response.status_code}"
            result["message"] = f"❌ Server returned {response.status_code}"
            
        return result
        
    except requests.exceptions.Timeout:
        return {"accessible": False, "error": "Request timed out after 15 seconds", "url": url}
    except requests.exceptions.ConnectionError as e:
        return {"accessible": False, "error": f"Connection error: Unable to reach server", "url": url}
    except Exception as e:
        return {"accessible": False, "error": str(e), "url": url}


async def validate_api_source(source_key: str, base_url: str, ipeds_id: int, config: dict) -> dict:
    """Validate an API source by actually fetching data."""
    import requests
    
    # College Scorecard API
    if "api.data.gov" in base_url or source_key == "college_scorecard":
        api_key = get_api_key("DATA_GOV_API_KEY")
        
        if not api_key:
            return {
                "accessible": False,
                "needs_api_key": True,
                "key_name": "DATA_GOV_API_KEY",
                "key_config": API_KEY_CONFIGS.get("DATA_GOV_API_KEY", {}),
                "api_type": "college_scorecard",
                "error": "API key required",
                "message": "Click 'Configure Key' to add your College Scorecard API key"
            }
        
        try:
            # Fetch sample data from College Scorecard
            fields = config.get("fields", [
                "school.name",
                "school.city", 
                "school.state",
                "latest.admissions.admission_rate.overall",
                "latest.cost.tuition.in_state",
                "latest.cost.tuition.out_of_state",
                "latest.student.size"
            ])
            
            params = {
                "api_key": api_key,
                "id": ipeds_id,
                "fields": ",".join(fields) if isinstance(fields, list) else fields
            }
            
            response = requests.get(
                "https://api.data.gov/ed/collegescorecard/v1/schools",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                results = resp_data.get("results", [])
                
                if results:
                    school_data = results[0]
                    # Format sample data for display
                    sample = {
                        "school_name": school_data.get("school.name"),
                        "location": f"{school_data.get('school.city')}, {school_data.get('school.state')}",
                        "admission_rate": school_data.get("latest.admissions.admission_rate.overall"),
                        "tuition_in_state": school_data.get("latest.cost.tuition.in_state"),
                        "tuition_out_of_state": school_data.get("latest.cost.tuition.out_of_state"),
                        "student_size": school_data.get("latest.student.size")
                    }
                    return {
                        "accessible": True,
                        "api_type": "college_scorecard",
                        "status_code": 200,
                        "sample_data": sample,
                        "total_results": resp_data.get("metadata", {}).get("total", 1),
                        "message": f"Successfully fetched data for {sample['school_name']}"
                    }
                else:
                    return {
                        "accessible": True,
                        "api_type": "college_scorecard",
                        "status_code": 200,
                        "sample_data": None,
                        "error": f"No results found for IPEDS ID {ipeds_id}"
                    }
            else:
                return {
                    "accessible": False,
                    "api_type": "college_scorecard",
                    "status_code": response.status_code,
                    "error": f"API returned status {response.status_code}: {response.text[:200]}"
                }
                
        except requests.exceptions.Timeout:
            return {"accessible": False, "error": "API request timed out", "api_type": "college_scorecard"}
        except Exception as e:
            return {"accessible": False, "error": str(e), "api_type": "college_scorecard"}
    
    # Urban Institute IPEDS API
    elif "educationdata.urban.org" in base_url or source_key == "urban_ipeds":
        try:
            # Fetch admissions data from Urban Institute
            endpoint = f"https://educationdata.urban.org/api/v1/college-university/ipeds/admissions-enrollment/2022/?unitid={ipeds_id}"
            
            response = requests.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                resp_data = response.json()
                results = resp_data.get("results", [])
                
                if results:
                    # Get first result (usually total)
                    enrollment_data = results[0]
                    sample = {
                        "year": enrollment_data.get("year"),
                        "applicants_total": enrollment_data.get("applicants_total"),
                        "admissions_total": enrollment_data.get("admissions_total"),
                        "enrolled_total": enrollment_data.get("enrolled_total"),
                        "admit_rate": round(enrollment_data.get("admissions_total", 0) / max(enrollment_data.get("applicants_total", 1), 1) * 100, 1) if enrollment_data.get("applicants_total") else None
                    }
                    return {
                        "accessible": True,
                        "api_type": "urban_ipeds",
                        "status_code": 200,
                        "sample_data": sample,
                        "total_results": len(results),
                        "message": f"Found {len(results)} enrollment records"
                    }
                else:
                    return {
                        "accessible": True,
                        "api_type": "urban_ipeds", 
                        "status_code": 200,
                        "sample_data": None,
                        "error": f"No results for IPEDS ID {ipeds_id} in 2022"
                    }
            else:
                return {
                    "accessible": False,
                    "api_type": "urban_ipeds",
                    "status_code": response.status_code,
                    "error": f"API returned status {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {"accessible": False, "error": "API request timed out", "api_type": "urban_ipeds"}
        except Exception as e:
            return {"accessible": False, "error": str(e), "api_type": "urban_ipeds"}
    
    # Fallback to standard URL validation
    return validate_url(None, base_url)


@app.post("/api/sources/{university_id}/finalize")
async def finalize_sources(university_id: str, activate_sources: list[str]):
    """Finalize and activate specified sources."""
    data = load_yaml_from_storage(university_id)
    if not data:
        raise HTTPException(status_code=404, detail="Source not found")
    
    activated = []
    for source_key in activate_sources:
        if "sources" in data and source_key in data["sources"]:
            source = data["sources"][source_key].get("primary", data["sources"][source_key])
            source["is_active"] = True
            source["last_validated"] = datetime.now().strftime("%Y-%m-%d")
            source["notes"] = "Validated and activated"
            activated.append(source_key)
    
    # Update metadata
    data["discovery_metadata"]["requires_user_validation"] = False
    data["discovery_metadata"]["finalized_at"] = datetime.now().isoformat()
    
    # Save to GCS
    save_yaml_to_storage(university_id, data)
    
    return {
        "success": True,
        "university_id": university_id,
        "activated_sources": activated
    }


# ============== STATIC FILE SERVING (must be last to not override API routes) ==============
STATIC_DIR = AGENT_DIR / "static"

if STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    # Mount assets first
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # Serve index.html for root
    @app.get("/")
    async def serve_root():
        return FileResponse(STATIC_DIR / "index.html")
    
    # Catch-all for SPA routing (must be defined last)
    @app.get("/{catch_all:path}")
    async def serve_spa(catch_all: str):
        # Don't catch API routes
        if catch_all.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        # Try to serve static file
        file_path = STATIC_DIR / catch_all
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # SPA fallback
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root_api():
        return {"message": "Source Curator API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
