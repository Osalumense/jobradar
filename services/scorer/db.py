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

    async def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Fetch all user profiles for global scrape + rescore."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM profile WHERE user_id IS NOT NULL")
            return [dict(r) for r in rows]

    async def get_profile(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch the matching target profile for a user."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            if user_id:
                row = await conn.fetchrow("SELECT * FROM profile WHERE user_id = $1 LIMIT 1", user_id)
                if row:
                    return dict(row)
            # Fallback: return any row (single-user legacy or anonymous)
            row = await conn.fetchrow("SELECT * FROM profile WHERE user_id IS NULL LIMIT 1")
            return dict(row) if row else None

    async def save_profile(self, profile_text: str, keywords: List[str], excluded: List[str], min_score: float, user_id: Optional[str] = None) -> None:
        """Upsert target profile preferences for a user."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            if user_id:
                existing = await conn.fetchval("SELECT id FROM profile WHERE user_id = $1", user_id)
                if existing:
                    await conn.execute(
                        """
                        UPDATE profile SET profile_text=$1, keywords=$2, excluded=$3, min_score=$4, updated_at=NOW()
                        WHERE user_id=$5
                        """,
                        profile_text, keywords, excluded, min_score, user_id
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO profile (profile_text, keywords, excluded, min_score, user_id, updated_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        """,
                        profile_text, keywords, excluded, min_score, user_id
                    )
            else:
                anon_id = await conn.fetchval("SELECT id FROM profile WHERE user_id IS NULL LIMIT 1")
                if anon_id:
                    await conn.execute(
                        "UPDATE profile SET profile_text=$1, keywords=$2, excluded=$3, min_score=$4, updated_at=NOW() WHERE id=$5",
                        profile_text, keywords, excluded, min_score, anon_id
                    )
                else:
                    await conn.execute(
                        "INSERT INTO profile (profile_text, keywords, excluded, min_score, updated_at) VALUES ($1, $2, $3, $4, NOW())",
                        profile_text, keywords, excluded, min_score
                    )

    async def insert_job(self, job: Dict[str, Any]) -> str:
        """Insert or update a scraped job, returning its database UUID."""
        if not self.pool:
            await self.connect()

        posted_at = job.get("posted_at")
        if isinstance(posted_at, str):
            try:
                from datetime import datetime
                posted_at = datetime.fromisoformat(posted_at)
            except ValueError:
                posted_at = None

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
                posted_at, job["content_hash"]
            )
            return str(row["id"])

    async def update_job_scores(self, job_id: str, scores: Dict[str, Any], user_id: Optional[str] = None) -> None:
        """Apply matching scores to a job. If user_id provided, writes to job_scores; else updates jobs table directly."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            if user_id:
                await conn.execute(
                    """
                    INSERT INTO job_scores (job_id, user_id, semantic_score, keyword_score, recency_score, composite_score, tech_stack, scored_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (job_id, user_id) DO UPDATE
                    SET semantic_score=$3, keyword_score=$4, recency_score=$5, composite_score=$6, tech_stack=$7, scored_at=NOW()
                    """,
                    job_id, user_id, scores["semantic"], scores["keyword"], scores["recency"],
                    scores["composite"], scores["tech_stack"]
                )
            else:
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

    async def delete_feat(self, feat_id: str) -> bool:
        """Delete an accomplishment by ID."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM user_feats WHERE id = $1", feat_id)
            return result == "DELETE 1"

    # --- CV & Cover Letters (Materials) ---
    async def get_materials(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch custom tailored application documents for a job."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM job_materials WHERE job_id = $1 LIMIT 1", job_id)
            return dict(row) if row else None

    async def save_materials(self, job_id: str, tailored_cv: str, cover_letter: str, qa_answers: Optional[str] = None) -> None:
        """Save AI tailored CV, cover letter, and optional Q&A answers."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_materials (job_id, tailored_cv, cover_letter, qa_answers, generated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (job_id) DO UPDATE
                SET tailored_cv = EXCLUDED.tailored_cv,
                    cover_letter = EXCLUDED.cover_letter,
                    qa_answers = EXCLUDED.qa_answers,
                    generated_at = NOW(),
                    version = job_materials.version + 1
                """,
                job_id, tailored_cv, cover_letter, qa_answers
            )

    async def get_user_profile(self, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve master user profile containing base CV, scoped by email."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            if email:
                row = await conn.fetchrow("SELECT * FROM user_profiles WHERE email = $1 LIMIT 1", email)
            else:
                row = await conn.fetchrow("SELECT * FROM user_profiles LIMIT 1")
            return dict(row) if row else None

    async def save_user_profile(self, name: str, email: str, phone: str | None, github: str | None, linkedin: str | None, master_cv: str) -> None:
        """Save/update the master user profile, scoped by email."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            existing = await conn.fetchval("SELECT id FROM user_profiles WHERE email = $1", email)
            if existing:
                await conn.execute(
                    """
                    UPDATE user_profiles
                    SET full_name=$1, phone=$2, github_url=$3, linkedin_url=$4, master_cv=$5, updated_at=NOW()
                    WHERE email=$6
                    """,
                    name, phone, github, linkedin, master_cv, email
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO user_profiles (full_name, email, phone, github_url, linkedin_url, master_cv)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    name, email, phone, github, linkedin, master_cv
                )

    async def count_jobs(self) -> int:
        """Return total number of scraped jobs."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM jobs")

    async def get_jobs(self, limit: int = 20, offset: int = 0, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch scraped jobs with scores and pagination support."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch(
                    """
                    SELECT j.*,
                           js.semantic_score  AS semantic_score,
                           js.keyword_score   AS tfidf_score,
                           js.recency_score   AS recency_score,
                           js.composite_score AS composite_score,
                           COALESCE(js.tech_stack, j.tech_stack) AS tech_stack,
                           js.scored_at, js.alerted
                    FROM jobs j
                    LEFT JOIN job_scores js ON js.job_id = j.id AND js.user_id = $3
                    ORDER BY js.composite_score DESC NULLS LAST, j.scraped_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit, offset, user_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM jobs ORDER BY composite_score DESC NULLS LAST, scraped_at DESC LIMIT $1 OFFSET $2",
                    limit, offset
                )
            return [dict(r) for r in rows]

    # --- User Accounts ---
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user credentials by email."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1 LIMIT 1", email.lower().strip())
            return dict(row) if row else None

    async def create_user(self, email: str, password_hash: str) -> str:
        """Register a new user account."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users (username, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
                email.lower().strip(), email.lower().strip(), password_hash
            )
            return str(row["id"])

    async def set_reset_token(self, email: str, token: str, expires_at) -> bool:
        """Store a password reset token for the given email."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET reset_token=$1, reset_token_expires=$2 WHERE email=$3",
                token, expires_at, email.lower().strip()
            )
            return result == "UPDATE 1"

    async def get_user_by_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Fetch user by a valid (non-expired) reset token."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE reset_token=$1 AND reset_token_expires > NOW()",
                token
            )
            return dict(row) if row else None

    async def reset_password(self, user_id: str, password_hash: str) -> None:
        """Update password and clear reset token."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET password_hash=$1, reset_token=NULL, reset_token_expires=NULL WHERE id=$2",
                password_hash, user_id
            )

    async def count_users(self) -> int:
        """Get the total number of registered users."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM users")
            return count or 0
