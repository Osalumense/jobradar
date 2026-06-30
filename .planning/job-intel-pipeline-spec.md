# JobRadar — Paris Alternance Intelligence Pipeline
### Project Spec v1.0 — Ready for AI Builder

---

## 0. What This Is

A self-hosted job intelligence system that:
- Scrapes French job boards every 6 hours for alternance/backend roles
- Deduplicates, normalizes, and scores every posting against a target profile
- Stores everything in Postgres with full history
- Sends Telegram alerts only for high-scoring new jobs
- Exposes a dashboard to track postings, scores, and application status

This is a **running production system**, not a demo. It accumulates real data over time.

---

## 1. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Scrapers | Python 3.12 + httpx + BeautifulSoup4 | Async HTTP, lightweight parsing |
| Scoring service | FastAPI + asyncio | Matches CV claims exactly |
| Embeddings | `sentence-transformers` (model: `paraphrase-multilingual-MiniLM-L12-v2`) | Free, runs in-process, French-aware |
| TF-IDF fallback | `scikit-learn` TfidfVectorizer | Keyword matching layer |
| Queue | Upstash Redis (REST API) | Serverless, free tier, no always-on cost |
| Deduplication | Upstash Redis SET | O(1) lookup per job hash |
| Database | Neon Postgres (serverless) | Auto-suspends, free tier, standard Postgres |
| Scheduler | GCP Cloud Run Jobs + Cloud Scheduler | Cron-triggered, pay per execution |
| Scoring API | GCP Cloud Run Service | Always-available HTTP endpoint |
| Alerting | Telegram Bot API | Simple, free, instant |
| Frontend | Nuxt 3 (SSR) | Matches CV stack |
| Frontend host | Netlify | Free, CI/CD from GitHub |
| CI/CD | GitHub Actions | Build → test → deploy to Cloud Run |

---

## 2. Repository Structure

```
jobradar/
├── services/
│   ├── scraper/                  # Cloud Run Job
│   │   ├── main.py               # Entry point, runs all scrapers
│   │   ├── sources/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract BaseScraper class
│   │   │   ├── wttj.py           # Welcome to the Jungle
│   │   │   ├── indeed.py         # Indeed France
│   │   │   ├── linkedin.py       # LinkedIn (careful, rate limits)
│   │   │   └── apec.py           # APEC
│   │   ├── models.py             # RawJob dataclass
│   │   ├── queue.py              # Upstash Redis publisher
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── scorer/                   # Cloud Run Service (HTTP)
│   │   ├── main.py               # FastAPI app
│   │   ├── embedder.py           # sentence-transformers wrapper
│   │   ├── tfidf.py              # TF-IDF fallback scorer
│   │   ├── scorer.py             # Composite scoring logic
│   │   ├── consumer.py           # Redis queue consumer (background task)
│   │   ├── models.py             # ScoredJob, JobRecord Pydantic models
│   │   ├── db.py                 # Neon Postgres connection (asyncpg)
│   │   ├── alert.py              # Telegram alerting
│   │   ├── Dockerfile
│   │   └── requirements.txt
│
├── frontend/                     # Nuxt 3 app
│   ├── pages/
│   │   ├── index.vue             # Dashboard — ranked jobs today
│   │   ├── pipeline.vue          # Kanban: new → applied → response
│   │   ├── trends.vue            # Charts: postings over time, top companies
│   │   └── settings.vue          # Update target profile, score thresholds
│   ├── components/
│   │   ├── JobCard.vue
│   │   ├── ScoreBadge.vue
│   │   ├── TrendChart.vue
│   │   └── PipelineBoard.vue
│   ├── server/api/               # Nuxt server routes (thin API layer)
│   │   ├── jobs/
│   │   │   ├── index.get.ts      # GET /api/jobs — paginated, filtered
│   │   │   └── [id].patch.ts     # PATCH /api/jobs/:id — update status
│   │   ├── trends/
│   │   │   └── index.get.ts      # GET /api/trends — aggregated stats
│   │   └── rescore.post.ts       # POST /api/rescore — trigger scorer
│   ├── netlify.toml
│   └── package.json
│
├── infra/
│   ├── schema.sql                # Full Postgres schema
│   ├── cloud-run-scraper.yaml    # Cloud Run Job definition
│   ├── cloud-run-scorer.yaml     # Cloud Run Service definition
│   └── scheduler.yaml            # Cloud Scheduler config
│
├── .github/
│   └── workflows/
│       ├── deploy-scraper.yml
│       └── deploy-scorer.yml
│
└── README.md                     # Architecture diagram + setup guide
```

---

## 3. Database Schema

```sql
-- Run this on Neon

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE jobs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id     TEXT NOT NULL,          -- source-specific ID
  source          TEXT NOT NULL,          -- 'wttj' | 'indeed' | 'linkedin' | 'apec'
  url             TEXT NOT NULL,
  title           TEXT NOT NULL,
  company         TEXT NOT NULL,
  location        TEXT,
  contract_type   TEXT,                   -- 'alternance' | 'cdi' | 'cdd' | 'stage'
  tech_stack      TEXT[],                 -- extracted from description
  description     TEXT NOT NULL,
  posted_at       TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Scoring
  semantic_score  FLOAT,                  -- cosine similarity (0-1)
  tfidf_score     FLOAT,                  -- keyword match score (0-1)
  recency_score   FLOAT,                  -- decay function output (0-1)
  composite_score FLOAT,                  -- weighted final score (0-1)
  scored_at       TIMESTAMPTZ,

  -- User tracking
  status          TEXT NOT NULL DEFAULT 'new',
                                          -- 'new' | 'reviewed' | 'applied' | 'interviewing' | 'rejected' | 'offer'
  notes           TEXT,
  applied_at      TIMESTAMPTZ,
  alerted         BOOLEAN DEFAULT FALSE,

  -- Dedup
  content_hash    TEXT NOT NULL,          -- SHA256 of (title + company + description[:200])

  UNIQUE(source, external_id),
  UNIQUE(content_hash)
);

CREATE INDEX idx_jobs_composite_score ON jobs(composite_score DESC);
CREATE INDEX idx_jobs_scraped_at ON jobs(scraped_at DESC);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_source ON jobs(source);

CREATE TABLE scrape_runs (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source      TEXT NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  jobs_found  INT DEFAULT 0,
  jobs_new    INT DEFAULT 0,
  error       TEXT                        -- null if clean run
);

CREATE TABLE profile (
  id              INT PRIMARY KEY DEFAULT 1,  -- singleton row
  profile_text    TEXT NOT NULL,              -- natural language target profile
  keywords        TEXT[],                     -- required keywords
  excluded        TEXT[],                     -- disqualifying keywords (e.g. 'Java only', 'senior 5+ ans')
  min_score       FLOAT DEFAULT 0.65,         -- alert threshold
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT single_row CHECK (id = 1)
);

-- Seed the profile (update this to match your actual target)
INSERT INTO profile (profile_text, keywords, excluded) VALUES (
  'Alternance cycle ingénieur backend développeur Python Node.js TypeScript FastAPI NestJS Redis PostgreSQL GCP AWS Docker systèmes distribués pipelines asynchrones Paris Île-de-France 2026',
  ARRAY['alternance', 'apprentissage', 'backend', 'python', 'node', 'typescript', 'fastapi', 'nestjs', 'redis', 'postgresql', 'docker', 'gcp', 'aws'],
  ARRAY['5 ans minimum', '3 ans expérience minimum', 'java', '.net', 'c#', 'stage uniquement']
);
```

---

## 4. Core Service Implementations

### 4.1 Base Scraper (`services/scraper/sources/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator
import hashlib


@dataclass
class RawJob:
    external_id: str
    source: str
    url: str
    title: str
    company: str
    location: str | None
    contract_type: str | None
    description: str
    posted_at: datetime | None
    tech_stack: list[str] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        raw = f"{self.title}{self.company}{self.description[:200]}"
        return hashlib.sha256(raw.encode()).hexdigest()


class BaseScraper(ABC):
    source: str
    base_url: str
    search_queries: list[str] = [
        "alternance backend python",
        "alternance développeur node typescript",
        "apprentissage ingénieur logiciel paris",
        "alternance fastapi nestjs",
    ]

    @abstractmethod
    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        """Yield RawJob objects for a given search query."""
        ...

    async def run(self) -> list[RawJob]:
        jobs = {}
        for query in self.search_queries:
            async for job in self.fetch_listings(query):
                # deduplicate within run by content_hash
                jobs[job.content_hash] = job
        return list(jobs.values())
```

### 4.2 Scoring Logic (`services/scorer/scorer.py`)

```python
from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass
class ScoreComponents:
    semantic: float      # 0-1, cosine similarity
    tfidf: float         # 0-1, keyword density
    recency: float       # 0-1, time decay
    composite: float     # weighted final


WEIGHTS = {
    "semantic": 0.55,
    "tfidf": 0.30,
    "recency": 0.15,
}


def recency_score(posted_at: datetime | None) -> float:
    """Exponential decay: 1.0 today, ~0.5 at 7 days, ~0.1 at 30 days."""
    if posted_at is None:
        return 0.5  # unknown date, neutral
    now = datetime.now(timezone.utc)
    age_days = (now - posted_at).total_seconds() / 86400
    return math.exp(-0.1 * age_days)


def composite_score(semantic: float, tfidf: float, posted_at: datetime | None) -> ScoreComponents:
    recency = recency_score(posted_at)
    composite = (
        semantic * WEIGHTS["semantic"] +
        tfidf * WEIGHTS["tfidf"] +
        recency * WEIGHTS["recency"]
    )
    return ScoreComponents(
        semantic=round(semantic, 4),
        tfidf=round(tfidf, 4),
        recency=round(recency, 4),
        composite=round(composite, 4),
    )
```

### 4.3 Queue Interface (`services/scraper/queue.py`)

```python
import httpx
import json
import os
from .sources.base import RawJob


UPSTASH_URL = os.environ["UPSTASH_REDIS_REST_URL"]
UPSTASH_TOKEN = os.environ["UPSTASH_REDIS_REST_TOKEN"]
QUEUE_KEY = "jobradar:queue"
SEEN_KEY = "jobradar:seen"


async def is_seen(client: httpx.AsyncClient, content_hash: str) -> bool:
    resp = await client.get(
        f"{UPSTASH_URL}/sismember/{SEEN_KEY}/{content_hash}",
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
    )
    return resp.json()["result"] == 1


async def mark_seen(client: httpx.AsyncClient, content_hash: str) -> None:
    await client.get(
        f"{UPSTASH_URL}/sadd/{SEEN_KEY}/{content_hash}",
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
    )


async def enqueue(client: httpx.AsyncClient, job: RawJob) -> None:
    payload = json.dumps({
        "external_id": job.external_id,
        "source": job.source,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "contract_type": job.contract_type,
        "description": job.description,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "tech_stack": job.tech_stack,
        "content_hash": job.content_hash,
    })
    await client.get(
        f"{UPSTASH_URL}/rpush/{QUEUE_KEY}/{payload}",
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
    )
```

### 4.4 Telegram Alerting (`services/scorer/alert.py`)

```python
import httpx
import os


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def format_alert(job: dict) -> str:
    score_pct = int(job["composite_score"] * 100)
    stars = "🟢" if score_pct >= 80 else "🟡" if score_pct >= 70 else "🟠"
    return (
        f"{stars} *{score_pct}% match*\n"
        f"*{job['title']}* — {job['company']}\n"
        f"📍 {job['location'] or 'Non précisé'}\n"
        f"🔗 [Voir l'offre]({job['url']})\n"
        f"_Sémantique: {int(job['semantic_score']*100)}% | "
        f"Mots-clés: {int(job['tfidf_score']*100)}%_"
    )


async def send_alert(job: dict) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": format_alert(job),
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        )
```

---

## 5. Environment Variables

### Scraper service
```env
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
DATABASE_URL=postgresql://user:pass@host/jobradar?sslmode=require
```

### Scorer service
```env
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
DATABASE_URL=postgresql://user:pass@host/jobradar?sslmode=require
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ALERT_THRESHOLD=0.65
```

### Frontend (Netlify)
```env
DATABASE_URL=postgresql://user:pass@host/jobradar?sslmode=require
SCORER_API_URL=https://scorer-xxxx.run.app
```

---

## 6. Cloud Run Configs

### Scraper Job (`infra/cloud-run-scraper.yaml`)
```yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: jobradar-scraper
  region: europe-west1
spec:
  template:
    spec:
      containers:
        - image: gcr.io/PROJECT_ID/jobradar-scraper:latest
          resources:
            limits:
              memory: 512Mi
              cpu: "1"
          env:
            - name: UPSTASH_REDIS_REST_URL
              valueFrom:
                secretKeyRef:
                  name: jobradar-secrets
                  key: UPSTASH_REDIS_REST_URL
            - name: UPSTASH_REDIS_REST_TOKEN
              valueFrom:
                secretKeyRef:
                  name: jobradar-secrets
                  key: UPSTASH_REDIS_REST_TOKEN
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: jobradar-secrets
                  key: DATABASE_URL
      maxRetries: 2
      timeoutSeconds: 600
```

### Cloud Scheduler (every 6 hours)
```yaml
schedule: "0 */6 * * *"
timeZone: "Europe/Paris"
target:
  uri: https://cloudrunjobs.googleapis.com/v1/projects/PROJECT_ID/locations/europe-west1/jobs/jobradar-scraper:run
  httpMethod: POST
  oauthToken:
    serviceAccountEmail: jobradar-scheduler@PROJECT_ID.iam.gserviceaccount.com
```

---

## 7. GitHub Actions — Deploy Scraper

```yaml
# .github/workflows/deploy-scraper.yml
name: Deploy Scraper

on:
  push:
    branches: [main]
    paths:
      - 'services/scraper/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Build and push image
        run: |
          gcloud builds submit services/scraper \
            --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/jobradar-scraper:latest

      - name: Update Cloud Run Job
        run: |
          gcloud run jobs update jobradar-scraper \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/jobradar-scraper:latest \
            --region europe-west1
```

---

## 8. Scoring Algorithm — Full Detail

```
composite_score = (semantic × 0.55) + (tfidf × 0.30) + (recency × 0.15)
```

**Semantic score:** Cosine similarity between job description embedding and profile embedding using `paraphrase-multilingual-MiniLM-L12-v2`. This model handles French natively. Profile embedding is computed once on startup and cached in memory.

**TF-IDF score:** Fit a TfidfVectorizer on the last 500 stored job descriptions (re-fit weekly). Score = cosine similarity between job vector and a synthetic "ideal document" built from the profile keywords repeated with weights.

**Recency score:** `e^(-0.1 × age_in_days)`. A job posted today scores 1.0. At 7 days: 0.50. At 30 days: 0.05. Jobs with unknown dates get 0.5.

**Alert threshold:** Default 0.65 composite. Configurable in the `profile` table. Only jobs not yet alerted trigger a Telegram message.

**Exclusion filter:** Before scoring, check description against `profile.excluded` array. Any match → set composite_score to 0, skip alert. Still stored for data completeness.

---

## 9. Frontend Pages — What Each Shows

### `/` — Dashboard
- Jobs scored today, ranked by composite_score descending
- Filters: source, min score, contract type, date range
- Each card: title, company, score breakdown (semantic/tfidf/recency chips), "Mark as reviewed" button

### `/pipeline`
- Kanban board: New → Reviewed → Applied → Interviewing → Rejected / Offer
- Drag-and-drop status update (calls PATCH /api/jobs/:id)
- Shows days since applied on Applied+ cards

### `/trends`
- Line chart: daily new postings per source over last 90 days
- Bar chart: top 20 companies by posting volume
- Pie chart: contract type breakdown
- Word cloud or ranked list: most common tech stack terms

### `/settings`
- Edit profile text (re-triggers embedding recomputation)
- Edit keyword lists (required / excluded)
- Set alert threshold slider
- "Run scraper now" button → calls POST /api/rescore

---

## 10. Build Order for AI Builder

Build in this exact sequence — each step is independently testable:

1. **Schema** — Run `infra/schema.sql` on Neon. Seed the profile row.
2. **Queue module** — `services/scraper/queue.py`. Test with a manual Upstash REST call.
3. **Base scraper** — `services/scraper/sources/base.py`. No network calls yet.
4. **WTTJ scraper** — `services/scraper/sources/wttj.py`. Test with a single query, print results.
5. **Scraper main** — Wire scrapers → dedup check → enqueue. Run locally, verify Redis SET and queue fill.
6. **Embedder** — `services/scorer/embedder.py`. Load model, embed a test string, verify shape.
7. **TF-IDF scorer** — `services/scorer/tfidf.py`. Fit on dummy data, score a test job.
8. **Composite scorer** — `services/scorer/scorer.py`. Unit test all three components.
9. **DB layer** — `services/scorer/db.py`. Insert one job, query it back.
10. **Consumer** — `services/scorer/consumer.py`. Poll Redis queue, score, insert to DB.
11. **Alert** — `services/scorer/alert.py`. Send one test Telegram message.
12. **FastAPI app** — Wire consumer as background task, expose `/health` and `/rescore` endpoints.
13. **Dockerfiles** — Both services. Test builds locally.
14. **Deploy scraper** to Cloud Run Job. Trigger manually, verify DB rows appear.
15. **Deploy scorer** to Cloud Run Service. Verify consumer picks up queued jobs.
16. **Cloud Scheduler** — Set 6-hour cron on the scraper job.
17. **GitHub Actions** — CI/CD for both services.
18. **Nuxt frontend** — Pages in order: dashboard → pipeline → trends → settings.
19. **Netlify deploy** — Connect repo, set env vars, deploy.
20. **Add Indeed scraper** — Extend source coverage.
21. **Add LinkedIn scraper** — Careful with rate limits, use delays.

---

## 11. Scraper Notes Per Source

**Welcome to the Jungle (wttj.fr)**
- Has a public JSON API: `https://www.welcometothejungle.com/api/v1/jobs?query=...`
- Preferred over HTML scraping — stable, structured response
- Filter params: `contract_types[]=alternance`, `location=Paris`

**Indeed France (fr.indeed.com)**
- HTML scraping, structure changes periodically — build defensively
- Respect `robots.txt`, add 2-3s delays between requests
- Use `httpx` with realistic User-Agent headers

**APEC (apec.fr)**
- Has an unofficial JSON API used by their own frontend
- Worth reverse-engineering in browser DevTools — returns clean structured data
- Targets cadre-level roles, good for cycle ingénieur alternance

**LinkedIn**
- Most aggressive about scraping — use long delays (5-10s), rotate user agents
- Consider using their job search RSS feed as a lighter alternative
- Or skip for v1 and add later

---

## 12. What "Done" Looks Like

The project is complete when:

- [ ] Scraper runs on schedule every 6 hours without manual intervention
- [ ] New jobs appear in DB within 10 minutes of a scraper run
- [ ] Telegram alert fires for any job scoring above threshold
- [ ] Dashboard loads and shows ranked jobs
- [ ] Pipeline board correctly tracks application status
- [ ] Trends page shows real data from at least 2 weeks of scraping
- [ ] GitHub commit history shows ongoing activity (fixes, scraper updates, tuning)
- [ ] README includes architecture diagram and real numbers (jobs indexed, sources, uptime)

---

## 13. What You'll Be Able to Say In Interviews

- "I built and operate a semantic job matching pipeline processing X postings per day across 4 sources"
- "I use sentence-transformers with a multilingual model for French job description embeddings, with TF-IDF as a fallback — same pattern I used at DensOps"
- "The deduplication layer uses Redis SETs for O(1) hash lookup before any scoring happens"
- "I track scraper run health in Postgres — I can show you when Indeed changed their HTML and broke my parser in week 3"
- "After 90 days I have data showing which Paris companies post the most alternance roles and which tech stacks dominate"

Every one of those is a real answer backed by a real running system.
