# Scraping & Scoring Engine — JobRadar AI

This document details the scraping collection pipeline and the Hybrid Scoring Engine used to rank job offers against candidate profiles.

---

## 1. Scraping Engine

JobRadar AI runs parallel scrapers configured dynamically based on user criteria. Each source uses specialized methods to crawl or fetch job postings:

| Source | Scraping Method | Files / Location | Description |
|---|---|---|---|
| **Welcome to the Jungle (WTTJ)** | Algolia API Client | `sources/wttj.py` | Queries WTTJ's public Algolia search API, mimicking their search interface. Returns structured JSON with tags. |
| **HelloWork** | HTML Parsing | `sources/hellowork.py` | Performs HTTP requests and extracts job attributes using BeautifulSoup4 parser rules. |
| **France Travail** | Official API | `sources/france_travail.py` | Connects using France Travail (Pôle Emploi) Partner Credentials to read their official search index API. |
| **LesJeudis** | Apollo State Extraction | `sources/lesjeudis.py` | Parses the landing script tag containing the `__APOLLO_STATE__` to deserialize data. |
| **Remotive** | Public JSON API | `sources/remotive.py` | Fetches JSON directly from Remotive's official public API feed for developer roles. |

### Deduplication
To prevent database bloating and redundant Gemini API scoring cost, **Upstash Redis** acts as a deduplication cache.
1. When a job is fetched, its unique URL is sanitized.
2. The URL is checked in Redis using `GET job:url:<hashed_url>`.
3. If present, the scraper skips it. If not, the job metadata is saved to Postgres, and the key is set in Redis with an expiration time.

---

## 2. Hybrid Scoring Engine

Once new jobs are loaded, the backend ranks them individually for each user using a **Hybrid Scoring Formula**.

```
CompositeScore = ( 
    0.45 * SemanticScore + 
    0.40 * KeywordScore + 
    0.15 * RecencyScore 
) * PreferenceMismatchFactor
```

### Components Details

#### A. Semantic Similarity Score (45% Weight)
- **Model**: Google Gemini `text-embedding-004`.
- **Logic**: Computes a vector representation for the candidate's master CV and the scraped job description text.
- **Metric**: Cosine similarity is computed between the two embedding vectors.
- **Goal**: Captures contextual matches (e.g. if the CV says "expert in fast-paced startup environments" and the job describes "scaling backend APIs in high-growth setups", they score highly even without exact word matches).

#### B. Keyword Match Score (40% Weight)
- **Model**: Exact substring boundary matching.
- **Logic**: Evaluates target technologies, languages, and tools specified in the user's target tech profile.
- **Calculation**: 
  $$\text{KeywordScore} = \frac{\text{Number of Matched Keywords}}{\text{Total Profile Keywords}}$$
- **Goal**: Ensures strict alignment with specific tech stack expectations (e.g. `fastapi`, `nuxt`, `docker`).

#### C. Recency Decay (15% Weight)
- **Logic**: Applies exponential decay to older job posts.
- **Formula**:
  $$\text{RecencyScore} = e^{-0.1 \times \text{age in days}}$$
- **Values**:
  - **0 days (today)**: `1.0`
  - **7 days old**: `~0.50`
  - **30 days old**: `~0.05`
  - **Unknown date**: fallback value of `0.5`

---

## 3. Preference Mismatch Factor

To prevent jobs that don't match critical criteria (e.g., location or contract type) from floating to the top (while still showing them in the feed with a low score), a **Preference Mismatch Factor** of `0.75` is applied.

1. **Contract Type Check**: If the user set target contract types (e.g. `Alternance`, `CDI`) and the job's contract doesn't match, the score is multiplied by `0.75`.
2. **Location Check**: If the user has target locations and the job location doesn't match, the score is multiplied by `0.75`.
3. **Double Penalty**: If both location and contract mismatch, the score is multiplied by `0.75 * 0.75` (`0.5625`).
