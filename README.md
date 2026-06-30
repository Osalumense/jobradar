# JobRadar AI 🚀

JobRadar AI is a self-hosted, fully automated job intelligence pipeline and application agent. It automatically scrapes French job boards for **CDI** and **Alternance** roles, filters and ranks them using semantic matching models, and leverages the Google Gemini API to generate customized CVs and French standard (*Moi, Vous, Nous*) cover letters on the fly based on your personal vault of achievements.

Designed for 100% free hosting using Render, Netlify, Neon Postgres, Upstash Redis, and cron-job.org.

---

## 🌟 Features

- **Automated Web Scraping**: Periodic cron-based scraping of Welcome to the Jungle, APEC, Indeed, and LinkedIn (RSS fallback) for Backend / Fullstack roles.
- **Smart Deduplication & Queue**: Rapid deduplication in Upstash Redis (O(1) checks) and asynchronous job parsing queues.
- **Hybrid Similarity Scoring**:
  - *Semantic Score (55%)*: Cosine similarity using `sentence-transformers` for multilingual (French) job matching.
  - *TF-IDF Score (30%)*: Strict keyword matches and exclusions.
  - *Recency Decay (15%)*: Prioritizes fresh job postings.
- **Telegram Bot Integration**: Real-time push alerts for high-matching opportunities.
- **Accomplishments Vault**: A personal logs manager to record and tag your project feats, allowing the AI agent to pull highly-relevant achievements dynamically.
- **Gemini Application Tailoring**:
  - Generates tailored CVs (Markdown format) that match job descriptions while remaining completely truthful.
  - Drafts Lettres de Motivation (cover letters) following the classic French standard layout (*Moi, Vous, Nous*).
- **Kanban Board & Dashboard**: Clean Nuxt 3 web interface with drag-and-drop state transitions, charts, and configuration panels.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, FastAPI, BeautifulSoup4, `httpx`, `sentence-transformers`, `scikit-learn`
- **Frontend**: Nuxt 3 (SSR), Vue 3, Tailwind CSS or Vanilla CSS, Chart.js
- **Database**: Neon Serverless Postgres
- **Deduplication / Queue**: Upstash Redis (REST API)
- **AI Engine**: Google Gemini API (`GEMINI_API_KEY`)
- **Hosting / Scheduler**: Render (FastAPI API), Netlify (Frontend), cron-job.org (Periodic Triggers)

---

## 📂 Repository Structure

```
jobradar/
├── .planning/                  # Project specifications, implementation plans, and wireframes
├── services/
│   └── scorer/                 # Unified Python FastAPI & Scraper web application
│       ├── sources/            # Individual board scrapers (WTTJ, APEC, Indeed)
│       ├── main.py             # FastAPI REST endpoints
│       ├── generator.py        # Gemini material generation logic
│       ├── scorer.py           # Multi-layered matching scorer
│       └── requirements.txt
├── frontend/                   # Nuxt 3 Client Web App
│   ├── pages/                  # Dashboard, Kanban Board, Feats Vault, Settings
│   ├── components/             # ApplicationModal drawer, charts, job cards
│   └── package.json
└── README.md
```

---

## 🚀 Getting Started

Check the planning documents in `.planning/` for detailed database schemas, class structures, and setup workflows:
- [Original Pipeline Specification](./.planning/job-intel-pipeline-spec.md)
- [Technical Implementation Plan](./.planning/job-intel-pipeline-implementation-plan.md)
- [UI/UX Specification](./.planning/ui_design_spec.md)
