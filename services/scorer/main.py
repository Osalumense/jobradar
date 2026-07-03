import os
import httpx
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response, Request, status, UploadFile
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
from sources.remotive import RemotiveScraper
from sources.hellowork import HelloWorkScraper
from sources.france_travail import FranceTravailScraper
from sources.lesjeudis import LesJeudiscraper

# Authentication dependencies
from auth_utils import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user_from_cookie,
    get_optional_user_from_cookie
)

LOG_DIR = os.environ.get("JOBRADAR_LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "jobradar.log"))
    ]
)
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
    email: str
    password: str

class ForgotPasswordSchema(BaseModel):
    email: str

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class FeatCreateSchema(BaseModel):
    title: str
    description: str
    skills_used: List[str] = Field(default_factory=list)

class GenerateMaterialsSchema(BaseModel):
    selected_feat_ids: Optional[List[str]] = None
    application_questions: Optional[str] = None

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

KNOWN_TECH_TERMS = [
    "python", "php", "node", "nodejs", "node.js", "typescript", "javascript",
    "fastapi", "nestjs", "express", "laravel", "symfony", "react", "vue",
    "nuxt", "postgres", "postgresql", "mysql", "redis", "docker", "kubernetes",
    "aws", "gcp", "azure", "sql", "mongodb", "django", "flask", "graphql",
    "rest", "ci/cd", "gitlab", "github actions"
]

GENERIC_SEARCH_QUERIES = [
    "alternance développeur backend paris",
    "développeur backend cdi paris",
    "ingénieur logiciel alternance paris",
    "développeur fullstack alternance paris",
]


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for value in values:
        clean = value.strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            deduped.append(clean)
    return deduped


def extract_profile_tech(master_cv: str, explicit_tech: List[str]) -> List[str]:
    """Merge explicit UI tech choices with technologies found in the uploaded CV."""
    cv_lower = master_cv.lower()
    detected = []
    for tech in KNOWN_TECH_TERMS:
        if tech.lower() in cv_lower:
            detected.append(tech)
    return _dedupe_keep_order([*explicit_tech, *detected])


def build_search_queries(
    roles: List[str], tech: List[str], contracts: List[str], locations: List[str]
) -> List[str]:
    """Build profile-driven queries ensuring each contract type has broad coverage."""
    if not roles and not tech:
        return GENERIC_SEARCH_QUERIES

    selected_roles = roles or ["développeur backend", "développeur fullstack"]
    selected_tech = tech or [""]
    selected_contracts = [c.lower() for c in (contracts or ["cdi"])]
    selected_locations = locations or ["paris"]

    queries = []
    for contract in selected_contracts:
        is_alternance = "alternance" in contract or "apprentissage" in contract

        # Broad role-only queries per contract (no tech filter — catches more postings)
        for role in selected_roles[:3]:
            for loc in selected_locations[:2]:
                q = " ".join(p for p in [contract, role, loc] if p).strip()
                queries.append(q)

        # Tech-specific queries only for CDI/non-alternance (alternance rarely filters by stack)
        if not is_alternance:
            for role in selected_roles[:2]:
                for item in selected_tech[:3]:
                    for loc in selected_locations[:1]:
                        q = " ".join(p for p in [contract, role, item, loc] if p).strip()
                        queries.append(q)

    return _dedupe_keep_order(queries)[:20]


# --- Helper: LLM Search Query Compiler ---
async def compile_search_queries(
    roles: List[str], tech: List[str], contracts: List[str], locations: List[str]
) -> List[str]:
    """Ask Gemini to generate natural French search query terms from onboarding preferences."""
    if not roles or not tech:
        return build_search_queries(roles, tech, contracts, locations)

    has_alternance = any("alternance" in c.lower() or "apprentissage" in c.lower() for c in contracts)
    prompt = f"""
    Create exactly 10 optimized French job board search queries (comma-separated) based on these preferences:
    - Target Roles: {', '.join(roles)}
    - Primary Technologies: {', '.join(tech)}
    - Contract Types: {', '.join(contracts)}
    - Target Locations: {', '.join(locations)}

    Rules:
    - Include 3–4 broad queries per contract type (role + location only, NO tech stack) — these catch the most results
    - Include 2–3 tech-specific queries for non-alternance contracts only
    {"- Alternance queries must NOT include specific tech stacks (too restrictive). Use broad terms like 'alternance développeur backend paris', 'alternance ingénieur informatique paris'" if has_alternance else ""}
    - Write queries in French as they would be typed on a French job board
    - Output ONLY comma-separated terms, no numbers, no quotes, no extra text.
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
        return build_search_queries(roles, tech, contracts, locations)


# --- Background Worker Trigger helper ---
async def run_scraper_and_consume(user_id: Optional[str] = None):
    """Scrape jobs using ALL users' combined queries, then rescore for every user."""
    # Collect search queries from every user profile — global scrape pool
    all_profiles = await db_client.get_all_profiles()
    seen_queries: set = set()
    search_queries: list = []

    for p in all_profiles:
        qs = p.get("search_queries") or []
        if not qs:
            qs = build_search_queries(
                p.get("target_roles", []),
                p.get("target_tech", []),
                p.get("target_contracts", []),
                p.get("target_locations", []),
            )
        for q in qs:
            q_norm = q.strip().lower()
            if q_norm not in seen_queries:
                seen_queries.add(q_norm)
                search_queries.append(q)

    if not search_queries:
        search_queries = GENERIC_SEARCH_QUERIES

    logger.info(f"Scraping with {len(search_queries)} deduplicated queries from {len(all_profiles)} user profiles")

    scrapers = [
        WelcomeToTheJungleScraper(),
        HelloWorkScraper(),
        FranceTravailScraper(),
        LesJeudiscraper(),
        RemotiveScraper(),
    ]

    # Remotive needs clean English keywords
    stopwords = {"alternance", "cdi", "stage", "cdd", "paris", "développeur", "ingénieur", "france", "ile-de-france"}
    cleaned_queries = list({
        " ".join(w for w in q.split() if w.lower() not in stopwords) or "developer"
        for q in search_queries
    })

    started_at = datetime.utcnow()
    total_enqueued = 0
    async with httpx.AsyncClient() as client:
        for scraper in scrapers:
            scraper.search_queries = cleaned_queries if scraper.source == "remotive" else search_queries
            run_id = await db_client.log_scrape_run(scraper.source, started_at)
            try:
                raw_jobs = await scraper.run()
                new_jobs_count = 0
                for job in raw_jobs:
                    if not await job_queue.is_seen(client, job.content_hash):
                        await job_queue.enqueue(client, job.to_dict())
                        new_jobs_count += 1
                total_enqueued += new_jobs_count
                logger.info(f"Scraper '{scraper.source}': {len(raw_jobs)} fetched, {new_jobs_count} new")
                async with db_client.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE scrape_runs SET finished_at=NOW(), jobs_found=$1, jobs_new=$2 WHERE id=$3",
                        len(raw_jobs), new_jobs_count, run_id
                    )
            except Exception as e:
                logger.error(f"Scraper error for {scraper.source}: {e}", exc_info=True)
                async with db_client.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE scrape_runs SET finished_at=NOW(), error=$1 WHERE id=$2", str(e), run_id
                    )

        logger.info(f"All scrapers done. {total_enqueued} new jobs. Consuming queue...")
        # Consume the queue (score + embed) for the triggering user first for fast feedback
        await consumer.consume_all(client, user_id=user_id)

    # After scraping, rescore all other users in the background so everyone's feed updates
    other_user_ids = [p["user_id"] for p in all_profiles if p.get("user_id") and p["user_id"] != user_id]
    for uid in other_user_ids:
        try:
            await _rescore_jobs_background(limit=200, user_id=uid)
        except Exception as e:
            logger.error(f"Post-scrape rescore failed for user {uid}: {e}")


# --- Authentication REST Endpoints ---

@app.post("/api/auth/register")
async def register(auth_data: UserAuthSchema):
    """Register a new user account."""
    existing = await db_client.get_user_by_email(auth_data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    hashed = hash_password(auth_data.password)
    user_id = await db_client.create_user(auth_data.email, hashed)
    return {"message": "Account registered successfully.", "user_id": user_id}

@app.post("/api/auth/login")
async def login(auth_data: UserAuthSchema, response: Response):
    """Authenticate credentials and set HttpOnly session cookies."""
    user = await db_client.get_user_by_email(auth_data.email)
    if not user or not verify_password(auth_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate tokens
    user_payload = {"sub": user["email"], "user_id": str(user["id"])}
    access_token = create_access_token(user_payload)
    refresh_token = create_refresh_token(user_payload)
    
    # Set cookies with secure attributes
    # secure=False is allowed for localhost development
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=15 * 60  # 15 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth/refresh",  # Only sent during refreshes
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {"message": "Login successful", "email": user["email"], "user_id": str(user["id"])}

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
        samesite="lax",
        max_age=15 * 60
    )
    
    return {"message": "Session token refreshed"}

@app.post("/api/auth/logout")
async def logout(response: Response):
    """Delete authentication cookies."""
    response.delete_cookie(key="access_token", samesite="lax")
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh", samesite="lax")
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user_from_cookie)):
    """Retrieve logged-in user information."""
    return {"email": user["sub"], "user_id": user["user_id"]}

@app.post("/api/auth/forgot-password")
async def forgot_password(data: ForgotPasswordSchema):
    """Generate a reset token and email it via Resend. Always returns 200 to prevent email enumeration."""
    import secrets
    from datetime import datetime, timedelta, timezone
    user = await db_client.get_user_by_email(data.email)
    if user:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db_client.set_reset_token(data.email, token, expires)
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3078")
        reset_link = f"{frontend_url}/reset-password?token={token}"
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {os.environ.get('RESEND_API_KEY', '').strip()}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": os.environ.get("ALERT_FROM_EMAIL", "JobRadar AI <onboarding@resend.dev>"),
                    "to": [data.email],
                    "subject": "Reset your JobRadar AI password",
                    "html": f"""
                    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
                      <h2 style="color:#10b981">JobRadar AI</h2>
                      <p>You requested a password reset. Click the button below — this link expires in <strong>1 hour</strong>.</p>
                      <a href="{reset_link}" style="display:inline-block;background:#10b981;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">Reset Password</a>
                      <p style="color:#64748b;font-size:0.875rem">If you didn't request this, ignore this email.</p>
                    </div>
                    """
                }
            )
    return {"message": "If an account with that email exists, a reset link has been sent."}

@app.post("/api/auth/reset-password")
async def reset_password(data: ResetPasswordSchema):
    """Verify reset token and update password."""
    user = await db_client.get_user_by_reset_token(data.token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link.")
    hashed = hash_password(data.new_password)
    await db_client.reset_password(str(user["id"]), hashed)
    return {"message": "Password updated successfully. You can now log in."}


# --- Protected Application REST Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "time": datetime.utcnow().isoformat()}

@app.post("/api/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Trigger the scraper and consumer queue for the authenticated user."""
    user_id = user.get("user_id") if user else None
    background_tasks.add_task(run_scraper_and_consume, user_id)
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

@app.delete("/api/feats/{feat_id}")
async def delete_feat(feat_id: str, user: Dict[str, Any] = Depends(get_current_user_from_cookie)):
    deleted = await db_client.delete_feat(feat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feat not found")
    return {"message": "Accomplishment deleted."}

# --- CV File Parsing Endpoint ---
@app.post("/api/profile/parse-cv")
async def parse_cv_file(
    file: UploadFile,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Extract plain text from an uploaded CV file (PDF, DOCX, or TXT)."""
    filename = (file.filename or "").lower()
    content = await file.read()

    try:
        if filename.endswith(".pdf"):
            import io, re
            import pdfplumber
            pages_text = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
                    if not words:
                        continue
                    # Reconstruct lines by grouping words with similar y-coordinate,
                    # then sort lines top-to-bottom. This handles any column layout.
                    LINE_TOLERANCE = 5  # px — words within this y-range are on the same line
                    lines: dict[int, list] = {}
                    for w in words:
                        y_bucket = round(w["top"] / LINE_TOLERANCE) * LINE_TOLERANCE
                        lines.setdefault(y_bucket, []).append(w)
                    page_lines = []
                    for y in sorted(lines):
                        line_words = sorted(lines[y], key=lambda w: w["x0"])
                        page_lines.append(" ".join(w["text"] for w in line_words))
                    pages_text.append("\n".join(page_lines))

            text = "\n\n".join(pages_text)
            # Collapse any remaining multi-space runs; preserve newlines
            text = re.sub(r'[ \t]{2,}', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
        elif filename.endswith(".docx"):
            import io
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif filename.endswith((".txt", ".md")):
            text = content.decode("utf-8", errors="replace")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF, DOCX, TXT, or MD file.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read file: {str(e)}")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="No text could be extracted from this file.")

    return {"text": text, "chars": len(text)}

# --- User Profile & Onboarding Settings Endpoints ---
@app.get("/api/profile")
async def get_profile(user: Optional[Dict[str, Any]] = Depends(get_optional_user_from_cookie)):
    user_email = user.get("sub") if user else None
    user_id = user.get("user_id") if user else None
    profile = await db_client.get_user_profile(user_email)
    matching_criteria = await db_client.get_profile(user_id)
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
    
    profile_tech = extract_profile_tech(profile.master_cv, profile.target_tech)

    # 2. Compile optimized scraper queries via Gemini
    search_queries = await compile_search_queries(
        roles=profile.target_roles,
        tech=profile_tech,
        contracts=profile.target_contracts,
        locations=profile.target_locations
    )
    
    # 3. Update active scoring profile parameters.
    # Excluded terms are retained as metadata but no longer hard-delete jobs from scoring.
    excluded = []

    # Upsert profile settings in the database (per-user if authenticated)
    uid = user.get("user_id") if user else None
    async with db_client.pool.acquire() as conn:
        if uid:
            existing_id = await conn.fetchval("SELECT id FROM profile WHERE user_id = $1", uid)
            if existing_id:
                await conn.execute(
                    """
                    UPDATE profile SET profile_text=$1, keywords=$2, excluded=$3, min_score=0.75,
                        target_roles=$4, target_tech=$5, target_contracts=$6, target_locations=$7,
                        search_queries=$8, updated_at=NOW()
                    WHERE user_id=$9
                    """,
                    profile.master_cv[:2000], profile_tech, excluded,
                    profile.target_roles, profile_tech, profile.target_contracts,
                    profile.target_locations, search_queries, uid
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO profile (profile_text, keywords, excluded, min_score,
                        target_roles, target_tech, target_contracts, target_locations, search_queries, user_id, updated_at)
                    VALUES ($1, $2, $3, 0.75, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                    profile.master_cv[:2000], profile_tech, excluded,
                    profile.target_roles, profile_tech, profile.target_contracts,
                    profile.target_locations, search_queries, uid
                )
        else:
            # Fallback: unauthenticated or missing user_id — upsert against user_id IS NULL row
            anon_id = await conn.fetchval("SELECT id FROM profile WHERE user_id IS NULL LIMIT 1")
            if anon_id:
                await conn.execute(
                    """
                    UPDATE profile SET profile_text=$1, keywords=$2, excluded=$3, min_score=0.75,
                        target_roles=$4, target_tech=$5, target_contracts=$6, target_locations=$7,
                        search_queries=$8, updated_at=NOW()
                    WHERE id=$9
                    """,
                    profile.master_cv[:2000], profile_tech, excluded,
                    profile.target_roles, profile_tech, profile.target_contracts,
                    profile.target_locations, search_queries, anon_id
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO profile (profile_text, keywords, excluded, min_score,
                        target_roles, target_tech, target_contracts, target_locations, search_queries, updated_at)
                    VALUES ($1, $2, $3, 0.75, $4, $5, $6, $7, $8, NOW())
                    """,
                    profile.master_cv[:2000], profile_tech, excluded,
                    profile.target_roles, profile_tech, profile.target_contracts,
                    profile.target_locations, search_queries
                )
        
    return {
        "message": "Master profile and matching preferences successfully updated.",
        "compiled_queries": search_queries
    }

# --- AI Materials Generation Endpoints ---
@app.post("/api/jobs/{job_id}/suggest-feats")
async def suggest_feats_for_job(
    job_id: str,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Ask Gemini to rank the user's feats by relevance to this specific job."""
    job = await db_client.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    all_feats = await db_client.get_feats()
    if not all_feats:
        return {"feats": []}

    try:
        generator = ApplicationMaterialGenerator(gemini_provider)
        ranked = await generator.suggest_feats(all_feats, job)
        return {"feats": ranked}
    except Exception as e:
        logger.error(f"suggest-feats error: {e}", exc_info=True)
        # Fallback: return all feats unranked
        return {"feats": [{**f, "suggested": True, "reason": ""} for f in all_feats]}

@app.post("/api/jobs/{job_id}/materials")
async def generate_application_materials(
    job_id: str,
    body: GenerateMaterialsSchema,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Generate tailored CV, cover letter, and optional Q&A answers via Gemini."""
    job = await db_client.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job posting {job_id} not found.")

    user_email = user.get("sub")
    profile = await db_client.get_user_profile(user_email)
    if not profile or not profile.get("master_cv"):
        raise HTTPException(status_code=400, detail="Master CV must be configured in Settings first.")

    all_feats = await db_client.get_feats()
    if body.selected_feat_ids is not None:
        feats_to_use = [f for f in all_feats if str(f["id"]) in body.selected_feat_ids]
    else:
        feats_to_use = all_feats[:6]

    try:
        generator = ApplicationMaterialGenerator(gemini_provider)
        materials = await generator.generate(
            base_cv=profile["master_cv"],
            accomplishments=feats_to_use,
            job=job,
            application_questions=body.application_questions
        )

        await db_client.save_materials(
            job_id=job_id,
            tailored_cv=materials["tailored_cv"],
            cover_letter=materials["cover_letter"],
            qa_answers=materials.get("qa_answers")
        )
        return {
            "message": "Materials generated successfully.",
            "tailored_cv": materials["tailored_cv"],
            "cover_letter": materials["cover_letter"],
            "qa_answers": materials.get("qa_answers"),
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

@app.get("/api/jobs")
async def get_all_jobs(
    limit: int = 20,
    offset: int = 0,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user_from_cookie)
):
    """Fetch ranked jobs list with pagination. Returns per-user scores when authenticated."""
    user_id = user.get("user_id") if user else None
    jobs = await db_client.get_jobs(limit, offset=offset, user_id=user_id)
    total = await db_client.count_jobs()
    return {"jobs": jobs, "total": total, "offset": offset, "limit": limit}

@app.post("/api/rescore")
async def rescore_existing_jobs(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    user: Dict[str, Any] = Depends(get_current_user_from_cookie)
):
    """Recalculate scores for all stored jobs against the requesting user's profile."""
    user_id = user.get("user_id") if user else None
    background_tasks.add_task(_rescore_jobs_background, limit, user_id)
    return {"message": f"Rescore scheduled for up to {limit} jobs. Running in background."}


async def _rescore_jobs_background(limit: int, user_id: Optional[str] = None):
    """Background worker: re-embeds and rescores stored jobs for a specific user."""
    profile = await db_client.get_profile(user_id)
    if not profile:
        logger.error("Rescore aborted: no profile configured.")
        return

    profile_text = profile.get("profile_text", "")
    logger.info(f"Rescore: fetching profile embedding (user={user_id})...")
    profile_embedding = await gemini_embedder.get_embedding(profile_text)

    async with db_client.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT $1", limit
        )

    logger.info(f"Rescore: scoring {len(rows)} jobs for user={user_id}...")
    rescored = 0
    for row in rows:
        job = dict(row)
        try:
            scores = await composite_scorer.score_job(
                description=job.get("description", ""),
                posted_at=job.get("posted_at"),
                profile_text=profile_text,
                profile_embedding=profile_embedding,
                keywords=profile.get("keywords", []),
                excluded=profile.get("excluded", []),
                contract_type=job.get("contract_type"),
                location=job.get("location"),
                target_contracts=profile.get("target_contracts", []),
                target_locations=profile.get("target_locations", [])
            )
            await db_client.update_job_scores(str(job["id"]), scores, user_id)
            rescored += 1
            logger.info(
                f"Rescored [{rescored}/{len(rows)}]: {job.get('title','?')[:50]} "
                f"— composite={scores['composite']:.2f} semantic={scores['semantic']:.2f}"
            )
        except Exception as e:
            logger.error(f"Rescore failed for job {job.get('id')}: {e}", exc_info=True)

    logger.info(f"Rescore complete: {rescored}/{len(rows)} jobs updated.")
