import os
import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime

class DatabaseClient:
    def __init__(self):
        self.dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_DB_CONNECTION")
        if not self.dsn:
            raise ValueError("DATABASE_URL or POSTGRES_DB_CONNECTION must be set in env")
            
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize the asyncpg connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=10,
                timeout=30.0
            )

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def get_profile(self) -> Optional[Dict[str, Any]]:
        """Fetch the matching target profile settings."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM profile WHERE id = 1 LIMIT 1")
            return dict(row) if row else None

    async def save_profile(self, profile_text: str, keywords: List[str], excluded: List[str], min_score: float) -> None:
        """Upsert target profile preferences."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO profile (id, profile_text, keywords, excluded, min_score, updated_at)
                VALUES (1, $1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO UPDATE
                SET profile_text = EXCLUDED.profile_text,
                    keywords = EXCLUDED.keywords,
                    excluded = EXCLUDED.excluded,
                    min_score = EXCLUDED.min_score,
                    updated_at = NOW()
                """,
                profile_text, keywords, excluded, min_score
            )

    async def insert_job(self, job: Dict[str, Any]) -> str:
        """Insert or update a scraped job, returning its database UUID."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            # We insert with a conflict clause on content_hash or external_id (handled in database unique constraints)
            # The spec specifies: UNIQUE(source, external_id) and UNIQUE(content_hash)
            row = await conn.fetchrow(
                """
                INSERT INTO jobs (
                    external_id, source, url, title, company, location, contract_type, 
                    tech_stack, description, posted_at, content_hash
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (source, external_id) DO UPDATE 
                SET url = EXCLUDED.url,
                    title = EXCLUDED.title,
                    location = EXCLUDED.location,
                    contract_type = EXCLUDED.contract_type,
                    tech_stack = EXCLUDED.tech_stack,
                    description = EXCLUDED.description
                RETURNING id
                """,
                job["external_id"], job["source"], job["url"], job["title"], job["company"],
                job["location"], job["contract_type"], job["tech_stack"], job["description"],
                job["posted_at"], job["content_hash"]
            )
            return str(row["id"])

    async def update_job_scores(self, job_id: str, scores: Dict[str, Any]) -> None:
        """Apply matching scores to a job posting."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs 
                SET semantic_score = $1,
                    tfidf_score = $2,
                    recency_score = $3,
                    composite_score = $4,
                    tech_stack = $5,
                    scored_at = NOW()
                WHERE id = $6
                """,
                scores["semantic"], scores["keyword"], scores["recency"], scores["composite"],
                scores["tech_stack"], job_id
            )

    async def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a single job."""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1 LIMIT 1", job_id)
            return dict(row) if row else None

    async def log_scrape_run(self, source: str, started_at: datetime, finished_at: datetime | None = None, jobs_found: int = 0, jobs_new: int = 0, error: str | None = None) -> str:
        """Record the execution health of a scraper run."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scrape_runs (source, started_at, finished_at, jobs_found, jobs_new, error)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                source, started_at, finished_at, jobs_found, jobs_new, error
            )
            return str(row["id"])

    # --- Accomplishments & Feats ---
    async def get_feats(self) -> List[Dict[str, Any]]:
        """Fetch all accomplishments/feats from the vault."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM user_feats ORDER BY created_at DESC")
            return [dict(r) for r in rows]

    async def insert_feat(self, title: str, description: str, skills_used: List[str]) -> str:
        """Insert a new achievement into the accomplishments vault."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_feats (title, description, skills_used)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                title, description, skills_used
            )
            return str(row["id"])

    # --- CV & Cover Letters (Materials) ---
    async def get_materials(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch custom tailored application documents for a job."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM job_materials WHERE job_id = $1 LIMIT 1", job_id)
            return dict(row) if row else None

    async def save_materials(self, job_id: str, tailored_cv: str, cover_letter: str) -> None:
        """Save AI tailored CV and Cover letter documents."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_materials (job_id, tailored_cv, cover_letter, generated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (job_id) DO UPDATE
                SET tailored_cv = EXCLUDED.tailored_cv,
                    cover_letter = EXCLUDED.cover_letter,
                    generated_at = NOW(),
                    version = job_materials.version + 1
                """,
                job_id, tailored_cv, cover_letter
            )

    async def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Retrieve master user profile containing base CV."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            # Get first profile row if exists
            row = await conn.fetchrow("SELECT * FROM user_profiles LIMIT 1")
            return dict(row) if row else None

    async def save_user_profile(self, name: str, email: str, phone: str | None, github: str | None, linkedin: str | None, master_cv: str) -> None:
        """Save/update the master user profile."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            # Check if profile already exists
            existing = await conn.fetchval("SELECT COUNT(*) FROM user_profiles")
            if existing > 0:
                await conn.execute(
                    """
                    UPDATE user_profiles
                    SET full_name = $1, email = $2, phone = $3, github_url = $4, linkedin_url = $5, master_cv = $6, updated_at = NOW()
                    """,
                    name, email, phone, github, linkedin, master_cv
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO user_profiles (full_name, email, phone, github_url, linkedin_url, master_cv)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    name, email, phone, github, linkedin, master_cv
                )

    # --- User Accounts ---
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user credentials by username."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE username = $1 LIMIT 1", username)
            return dict(row) if row else None

    async def create_user(self, username: str, password_hash: str) -> str:
        """Register a new user account."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id",
                username, password_hash
            )
            return str(row["id"])

    async def count_users(self) -> int:
        """Get the total number of registered users."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM users")
            return count or 0
