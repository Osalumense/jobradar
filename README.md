# JobRadar AI

JobRadar AI is a self-hosted, AI-powered job search and application platform. It automatically scrapes French job boards for **CDI**, **Alternance**, **CDD**, and **Stage** roles, ranks them per user using semantic and keyword matching, and uses Google Gemini to generate tailored CVs and cover letters based on your personal accomplishments vault.

---

## Features

- **Multi-source scraping**: Welcome to the Jungle, HelloWork, France Travail, LesJeudis, and Remotive — running on every "Scan Now" trigger.
- **Global + per-user pipeline**: Scraper collects queries from all user profiles, deduplicates, runs once, then rescores every user independently.
- **Hybrid scoring** per user:
  - *Semantic score (55%)*: Cosine similarity via Google Gemini embeddings
  - *TF-IDF score (30%)*: Keyword match against profile criteria
  - *Recency decay (15%)*: Deprioritises stale postings
- **Server-side filtering**: Filter by contract type (CDI / Alternance / Internship / CDD) or source — results come directly from the DB, not from the loaded page slice.
- **Pagination**: "Load More" button with live count (N / total); filters reset and re-fetch automatically.
- **AI application materials**: Gemini generates tailored CVs (Markdown) and French cover letters (*Moi, Vous, Nous* layout) per job posting.
- **Accomplishments Vault**: Record and tag project feats; Gemini pulls the most relevant ones into each application.
- **Application pipeline**: Kanban-style status tracking (Applied → Reviewing → Interviewing → Offer).
- **Multi-user**: Each user has isolated profile, scores, and application history. Onboarding collects matching criteria (roles, contracts, locations, tech stack).
- **Email alerts**: Resend-powered notifications for high-matching new postings.
- **Password reset**: Token-based flow with email delivery.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, asyncpg |
| Scraping | httpx, BeautifulSoup4, Algolia API (WTTJ) |
| AI / Scoring | Google Gemini API, scikit-learn TF-IDF |
| Frontend | Nuxt 3, Vue 3, Vanilla CSS |
| Database | Neon Serverless PostgreSQL |
| Queue / Dedup | Upstash Redis (REST) |
| Email | Resend |
| Containers | Docker Compose |

---

## Repository Structure

```
jobradar/
├── services/
│   └── scorer/                 # FastAPI backend + scraping pipeline
│       ├── sources/            # Board scrapers
│       │   ├── wttj.py         # Welcome to the Jungle (Algolia API)
│       │   ├── hellowork.py    # HelloWork (HTML scrape)
│       │   ├── france_travail.py  # France Travail (official API)
│       │   ├── lesjeudis.py    # LesJeudis (Apollo state)
│       │   └── remotive.py     # Remotive (JSON API)
│       ├── main.py             # FastAPI endpoints (auth, jobs, scrape, score)
│       ├── db.py               # asyncpg database client
│       ├── scorer.py           # Hybrid scoring logic
│       ├── generator.py        # Gemini CV / cover letter generation
│       └── requirements.txt
├── frontend/                   # Nuxt 3 SPA
│   └── app/
│       ├── pages/              # Dashboard, Jobs, Pipeline, Analytics, Profile
│       └── components/         # Job cards, modals, charts
├── docker-compose.yml
├── .env.example                # All required environment variables
└── README.md
```

---

## Getting Started

### 1. Clone and configure

```bash
git clone https://github.com/Osalumense/jobradar.git
cd jobradar
cp .env.example .env
# Edit .env and fill in your credentials
```

### 2. Required credentials

| Variable | Where to get it |
|----------|----------------|
| `DATABASE_URL` | [Neon](https://neon.tech) — free tier PostgreSQL |
| `JWT_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(64))"` |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) — free tier |
| `UPSTASH_REDIS_REST_URL` + `TOKEN` | [Upstash](https://console.upstash.com/) — free tier Redis |
| `RESEND_API_KEY` | [Resend](https://resend.com) — free tier (100 emails/day) |

### 3. Run with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3078
- Backend API: http://localhost:9089

### 4. First-time setup

1. Register an account at `http://localhost:3078/register`
2. Complete onboarding (upload CV, set target roles, contracts, locations)
3. Click **Scan Now** on the dashboard — scrapes all sources and scores jobs against your profile
4. Use the contract-type and source filters to narrow results instantly

---

## Database

The app manages its own schema on first run via `db.py`. Key tables:

| Table | Purpose |
|-------|---------|
| `users` | Auth credentials |
| `user_profiles` | CV, contact info, per-user |
| `profile` | Matching criteria (roles, queries, contracts) per user |
| `jobs` | All scraped job postings |
| `job_scores` | Per-user composite scores |

---

## Environment Variables Reference

See [`.env.example`](./.env.example) for the full list with descriptions.
