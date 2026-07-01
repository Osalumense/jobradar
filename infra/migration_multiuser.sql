-- Migration: Multi-user support
-- Jobs remain shared/deduplicated; scores are per-user via job_scores junction table.
-- profile table becomes per-user (drop singleton constraint).

-- 1. Per-user scores table
CREATE TABLE IF NOT EXISTS job_scores (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  semantic_score  FLOAT,
  keyword_score   FLOAT,
  recency_score   FLOAT,
  composite_score FLOAT,
  tech_stack      TEXT[],
  scored_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  alerted         BOOLEAN DEFAULT FALSE,
  UNIQUE(job_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_job_scores_user ON job_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_job_scores_composite ON job_scores(user_id, composite_score DESC);

-- 2. Add user_id to profile table (nullable first for migration safety)
ALTER TABLE profile ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- 3. Drop singleton constraint so each user can have their own profile row
ALTER TABLE profile DROP CONSTRAINT IF EXISTS single_row;

-- 4. Make profile.id a sequence instead of hardcoded 1
-- (Keep existing id=1 row — just remove the check constraint above)
