-- Run this on your Neon Postgres database instance

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (for Authentication)
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Job Postings Table
CREATE TABLE IF NOT EXISTS jobs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id     TEXT NOT NULL,          -- Source-specific unique ID
  source          TEXT NOT NULL,          -- 'wttj' | 'indeed' | 'linkedin' | 'apec'
  url             TEXT NOT NULL,
  title           TEXT NOT NULL,
  company         TEXT NOT NULL,
  location        TEXT,
  contract_type   TEXT NOT NULL,          -- 'alternance' | 'cdi' | 'cdd' | 'stage'
  tech_stack      TEXT[],                 -- Extracted list of tags/technologies
  description     TEXT NOT NULL,
  posted_at       TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Scoring Metrics
  semantic_score  FLOAT,                  -- Cosine similarity score (0-1)
  tfidf_score     FLOAT,                  -- Keyword frequency matching score (0-1)
  recency_score   FLOAT,                  -- Exponential time-decay score (0-1)
  composite_score FLOAT,                  -- Weighted aggregate score (0-1)
  scored_at       TIMESTAMPTZ,

  -- Application Tracking State
  status          TEXT NOT NULL DEFAULT 'new', 
                                          -- 'new' | 'reviewed' | 'applied' | 'interviewing' | 'rejected' | 'offer'
  notes           TEXT,
  applied_at      TIMESTAMPTZ,
  alerted         BOOLEAN DEFAULT FALSE,  -- Email notification status

  -- Deduplication check
  content_hash    TEXT NOT NULL,          -- SHA256 of (title + company + description[:200])

  UNIQUE(source, external_id),
  UNIQUE(content_hash)
);

-- Optimize search, filtering and sorting queries
CREATE INDEX IF NOT EXISTS idx_jobs_composite_score ON jobs(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_contract_type ON jobs(contract_type);

-- 3. Scraper Performance Runs Tracking Table
CREATE TABLE IF NOT EXISTS scrape_runs (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source      TEXT NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  jobs_found  INT DEFAULT 0,
  jobs_new    INT DEFAULT 0,
  error       TEXT                        -- Error details if execution fails, otherwise NULL
);

-- 4. Match Target Profile Table (Singleton containing search filters & preferences)
CREATE TABLE IF NOT EXISTS profile (
  id               INT PRIMARY KEY DEFAULT 1,
  profile_text     TEXT NOT NULL,              -- Target profile description in natural language
  keywords         TEXT[],                     -- Mandatory keywords (TF-IDF boosting)
  excluded         TEXT[],                     -- Exclusion terms (leads to automatic zero match)
  min_score        FLOAT DEFAULT 0.65,         -- Minimum composite score required for alerts
  target_roles     TEXT[] DEFAULT ARRAY[]::TEXT[],
  target_tech      TEXT[] DEFAULT ARRAY[]::TEXT[],
  target_contracts TEXT[] DEFAULT ARRAY[]::TEXT[],
  target_locations TEXT[] DEFAULT ARRAY[]::TEXT[],
  search_queries   TEXT[] DEFAULT ARRAY[]::TEXT[], -- Automatically compiled search terms
  updated_at       TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT single_row CHECK (id = 1)
);

-- 5. User Master CV Profile Table
CREATE TABLE IF NOT EXISTS user_profiles (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name    TEXT NOT NULL,
  email        TEXT NOT NULL,
  phone        TEXT,
  github_url   TEXT,
  linkedin_url TEXT,
  master_cv    TEXT NOT NULL,               -- Full base CV written in Markdown
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. User Accomplishments & Feats Repository
CREATE TABLE IF NOT EXISTS user_feats (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title        TEXT NOT NULL,               -- Short descriptive title (e.g. "Database Optimization")
  description  TEXT NOT NULL,               -- Full achievement, metrics, tasks
  skills_used  TEXT[],                      -- Associated tech stack keys
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Generated Tailored Application Materials
CREATE TABLE IF NOT EXISTS job_materials (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  tailored_cv     TEXT NOT NULL,               -- AI Tailored CV markdown
  cover_letter    TEXT NOT NULL,               -- French standard "Moi, Vous, Nous" cover letter text
  generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  version         INT DEFAULT 1,
  UNIQUE(job_id)
);

-- Seed initial target profile for scoring and scraper queries
INSERT INTO profile (
  id, profile_text, keywords, excluded, min_score, 
  target_roles, target_tech, target_contracts, target_locations, search_queries
) 
VALUES (
  1,
  'Développeur backend spécialisé en Python, Node.js et TypeScript. Expérience avec FastAPI, NestJS, Postgres, Redis, Docker et architectures de pipelines asynchrones ou systèmes distribués.',
  ARRAY['backend', 'python', 'node', 'typescript', 'fastapi', 'nestjs', 'postgres', 'redis', 'docker'],
  ARRAY['java', '.net', 'c#', 'php', 'senior 5+ ans', 'stage uniquement'],
  0.65,
  ARRAY['développeur backend', 'ingénieur backend'],
  ARRAY['python', 'node', 'typescript'],
  ARRAY['cdi', 'alternance'],
  ARRAY['paris'],
  ARRAY['alternance backend python', 'développeur node typescript cdi', 'alternance fastapi nestjs']
)
ON CONFLICT (id) DO NOTHING;

-- Migration: add Q&A answers column to job_materials
ALTER TABLE job_materials ADD COLUMN IF NOT EXISTS qa_answers TEXT;
