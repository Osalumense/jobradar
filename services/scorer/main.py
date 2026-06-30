import os
import httpx
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from db import DatabaseClient
from job_queue import JobQueue
from scorer import CompositeScorer
from embedder import GeminiEmbedder
from keyword_matcher import KeywordMatcher
from alert import ResendAlerter
from consumer import QueueConsumer
from gemini_provider import GeminiProvider
from generator import ApplicationMaterialGenerator
from sources.wttj import WelcomeToTheJungleScraper

# Authentication dependencies
from auth_utils import (
    hash_password, verify_password, create_access_token, 
    create_refresh_token, decode_token, get_current_user_from_cookie
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobradar.api")

app = FastAPI(title="JobRadar AI Scorer Service", version="1.0.0")

# Setup CORS with credentials support (necessary for cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3078"],  # Restrict to our FE port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core clients and providers
db_client = DatabaseClient()
job_queue = JobQueue()
gemini_embedder = GeminiEmbedder()
keyword_matcher = KeywordMatcher()
composite_scorer = CompositeScorer(gemini_embedder, keyword_matcher)
resend_alerter = ResendAlerter()
gemini_provider = GeminiProvider()

# Setup consumer
consumer = QueueConsumer(
    queue=job_queue,
    db=db_client,
    scorer=composite_scorer,
    embedder=gemini_embedder,
    alerter=resend_alerter
)

# Lifecycle management
@app.on_event("startup")
async def startup():
    await db_client.connect()

@app.on_event("shutdown")
async def shutdown():
    await db_client.disconnect()


# --- Pydantic Schema Models ---
class UserAuthSchema(BaseModel):
    username: str
    password: str

class FeatCreateSchema(BaseModel):
    title: str
    description: str
    skills_used: List[str] = Field(default_factory=list)

class UserProfileSchema(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    master_cv: str
    # Onboarding structured inputs
    target_roles: List[str] = Field(default_factory=list)
    target_tech: List[str] = Field(default_factory=list)
    target_contracts: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)


# --- Helper: LLM Search Query Compiler ---
async def compile_search_queries(
    roles: List[str], tech: List[str], contracts: List[str], locations: List[str]
) -> List[str]:
    """Ask Gemini to generate natural French search query terms from onboarding preferences."""
    if not roles or not tech:
        # Fallback to combinatorial if inputs are empty
        return ["alternance backend python", "développeur node cdi"]

    prompt = f"""
    Create a clean list of exactly 6 optimized French job board search queries (comma-separated, e.g. "alternance développeur node paris") 
    based on my preferences:
    - Target Roles: {', '.join(roles)}
    - Primary Technologies: {', '.join(tech)}
    - Contract Types: {', '.join(contracts)}
    - Target Locations: {', '.join(locations)}

    Output ONLY the comma-separated search terms. Do not include introductory text, numbers, or code blocks.
    """
    
    try:
        raw_output = await gemini_provider.generate_text(
            prompt, 
            system_instruction="You are a job search optimization bot. Output comma-separated query strings only."
        )
        queries = [q.strip().replace('"', '').replace("'", "") for q in raw_output.split(",")]
        # Keep only non-empty queries
        return [q for q in queries if q][:8]
    except Exception as e:
        logger.error(f"Error compiling search queries via Gemini: {e}")
        # Deterministic fallback combination
        fallback = []
        for role in roles[:2]:
            for t in tech[:2]:
                for contract in contracts[:2]:
                    loc = locations[0] if locations else "paris"
                    fallback.append(f"{contract} {role} {t} {loc}")
        return fallback[:6]


# --- Background Worker Trigger helper ---
async def run_scraper_and_consume():
    """Runs all scrapers, enqueues raw jobs, and starts processing."""
    # 1. Fetch active search queries from the DB profile
    profile = await db_client.get_profile()
    search_queries = []
    if profile and profile.get("search_queries"):
        search_queries = profile.get("search_queries")
    
    if not search_queries:
        # Defaults if no profile configuration is set
        search_queries = ["alternance backend python", "développeur node cdi paris"]

    # Instantiate scrapers
    scraper = WelcomeToTheJungleScraper()
    # Override scraper default search queries with user's custom database queries
    scraper.search_queries = search_queries

    started_at = datetime.utcnow()
    async with httpx.AsyncClient() as client:
        run_id = await db_client.log_scrape_run(scraper.source, started_at)
        try:
            # 1. Run scraping pipeline
            raw_jobs = await scraper.run()
            new_jobs_count = 0
            
            # 2. Push to queue if not seen
            for job in raw_jobs:
                is_duplicate = await job_queue.is_seen(client, job.content_hash)
                if not is_duplicate:
                    await job_queue.enqueue(client, job.to_dict())
                    new_jobs_count += 1
            
            # 3. Log run stats
            async with db_client.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE scrape_runs SET finished_at = NOW(), jobs_found = $1, jobs_new = $2 WHERE id = $3",
                    len(raw_jobs), new_jobs_count, run_id
                )
        except Exception as e:
            logger.error(f"Scraper error for {scraper.source}: {e}", exc_info=True)
            async with db_client.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE scrape_runs SET finished_at = NOW(), error = $1 WHERE id = $2",
                    str(e), run_id
                )

        # 4. Trigger Queue consumption
        await consumer.consume_all(client)


# --- Authentication REST Endpoints ---

@app.post("/api/auth/register")
async def register(auth_data: UserAuthSchema):
    """Register a new user account. Locked for single-tenant safety once first user exists."""
    existing_user_count = await db_client.count_users()
    if existing_user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Only one self-hosted account is allowed."
        )
    
    hashed = hash_password(auth_data.password)
    user_id = await db_client.create_user(auth_data.username, hashed)
    return {"message": "Account registered successfully.", "user_id": user_id}

@app.post("/api/auth/login")
async def login(auth_data: UserAuthSchema, response: Response):
    """Authenticate credentials and set HttpOnly session cookies."""
    user = await db_client.get_user_by_username(auth_data.username)
    if not user or not verify_password(auth_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Generate tokens
    user_payload = {"sub": user["username"], "user_id": str(user["id"])}
    access_token = create_access_token(user_payload)
    refresh_token = create_refresh_token(user_payload)
    
    # Set cookies with secure attributes
    # secure=False is allowed for localhost development
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60  # 15 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/auth/refresh",  # Only sent during refreshes
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {"message": "Login successful", "username": user["username"]}

@app.post("/api/auth/refresh")
async def refresh_session(request: Request, response: Response):
    """Verify refresh cookie and issue new access token cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    payload = decode_token(refresh_token, require_refresh=True)
    user_payload = {"sub": payload["sub"], "user_id": payload["user_id"]}
    new_access_token = create_access_token(user_payload)
    
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60
    )
    
    return {"message": "Session token refreshed"}

@app.post("/api/auth/logout")
async def logout(response: Response):
    """Delete authentication cookies."""
    response.delete_cookie(key="access_token", samesite="strict")
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh", samesite="strict")
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user_from_cookie)):
    """Retrieve logged-in user information."""
    return {"username": user["sub"], "user_id": user["user_id"]}


# --- Protected Application REST Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "time": datetime.utcnow().isoformat()}

@app.post("/api/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Trigger the scraper and consumer queue asynchronously in the background."""
    background_tasks.add_task(run_scraper_and_consume)
    return {"message": "Scraping and matching pipeline scheduled in background."}

# --- Vault Feats Endpoints ---
@app.get("/api/feats")
async def get_feats(user: Dict[str, Any] = Depends(get_current_user_from_cookie)):
    return await db_client.get_feats()

@app.post("/api/feats")
async def create_feat(
    feat: FeatCreateSchema,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    feat_id = await db_client.insert_feat(feat.title, feat.description, feat.skills_used)
    return {"message": "Accomplishment successfully saved.", "id": feat_id}

# --- User Profile & Onboarding Settings Endpoints ---
@app.get("/api/profile")
async def get_profile(user: Dict[str, Any] = Depends(get_current_user_from_cookie)):
    profile = await db_client.get_user_profile()
    # Fetch target matching criteria to prefill settings UI
    matching_criteria = await db_client.get_profile()
    
    return {
        "profile": profile,
        "matching_criteria": matching_criteria
    }

@app.post("/api/profile")
async def save_profile(
    profile: UserProfileSchema,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    # 1. Save master user profile CV details
    await db_client.save_user_profile(
        name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        github=profile.github_url,
        linkedin=profile.linkedin_url,
        master_cv=profile.master_cv
    )
    
    # 2. Compile optimized scraper queries via Gemini
    search_queries = await compile_search_queries(
        roles=profile.target_roles,
        tech=profile.target_tech,
        contracts=profile.target_contracts,
        locations=profile.target_locations
    )
    
    # 3. Update active scoring profile parameters
    # The tech stack array becomes the TF-IDF matching keywords
    # Excluded keywords filter out mismatched posts (e.g. if Alternance is selected, Stage is blocked)
    excluded = ["java", ".net", "c#"]
    if "alternance" in profile.target_contracts and "stage" not in profile.target_contracts:
        excluded.append("stage uniquement")

    # Upsert profile settings in the database
    async with db_client.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO profile (
                id, profile_text, keywords, excluded, min_score, 
                target_roles, target_tech, target_contracts, target_locations, search_queries, updated_at
            ) VALUES (1, $1, $2, $3, 0.75, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (id) DO UPDATE
            SET profile_text = EXCLUDED.profile_text,
                keywords = EXCLUDED.keywords,
                excluded = EXCLUDED.excluded,
                target_roles = EXCLUDED.target_roles,
                target_tech = EXCLUDED.target_tech,
                target_contracts = EXCLUDED.target_contracts,
                target_locations = EXCLUDED.target_locations,
                search_queries = EXCLUDED.search_queries,
                updated_at = NOW()
            """,
            profile.master_cv[:500],  # Profile matching text (derived from CV summary)
            profile.target_tech,
            excluded,
            profile.target_roles,
            profile.target_tech,
            profile.target_contracts,
            profile.target_locations,
            search_queries
        )
        
    return {
        "message": "Master profile and matching preferences successfully updated.",
        "compiled_queries": search_queries
    }

# --- AI Materials Generation Endpoints ---
@app.post("/api/jobs/{job_id}/materials")
async def generate_application_materials(
    job_id: str, 
    selected_feat_ids: Optional[List[str]] = None,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Asynchronously tailor CV and cover letter using selected feats and Gemini API."""
    job = await db_client.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job posting {job_id} not found.")

    profile = await db_client.get_user_profile()
    if not profile or not profile.get("master_cv"):
        raise HTTPException(status_code=400, detail="Master CV must be configured in Settings first.")

    all_feats = await db_client.get_feats()
    feats_to_use = []
    
    if selected_feat_ids is not None:
        feats_to_use = [f for f in all_feats if str(f["id"]) in selected_feat_ids]
    else:
        job_stack = set([t.lower() for t in (job.get("tech_stack") or [])])
        for feat in all_feats:
            feat_tags = set([s.lower() for s in (feat.get("skills_used") or [])])
            if job_stack.intersection(feat_tags):
                feats_to_use.append(feat)
        feats_to_use = feats_to_use[:5]

    try:
        generator = ApplicationMaterialGenerator(gemini_provider)
        materials = await generator.generate(profile["master_cv"], feats_to_use, job)
        
        await db_client.save_materials(
            job_id=job_id,
            tailored_cv=materials["tailored_cv"],
            cover_letter=materials["cover_letter"]
        )
        return {
            "message": "Materials tailored successfully.",
            "tailored_cv": materials["tailored_cv"],
            "cover_letter": materials["cover_letter"]
        }
    except Exception as e:
        logger.error(f"Error generating materials via Gemini: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate materials: {str(e)}")

@app.get("/api/jobs/{job_id}/materials")
async def get_application_materials(
    job_id: str,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Retrieve pre-generated tailored documents."""
    materials = await db_client.get_materials(job_id)
    if not materials:
        raise HTTPException(status_code=404, detail="Tailored materials not generated for this application yet.")
    return materials
