# Implementation Plan - JobRadar with Gemini CV & Cover Letter Customization (v2 - Render/Free Tier Architecture)

Extend the JobRadar pipeline to scrape CDI job postings, manage a master CV, store a dump of accomplishments/feats, and use a dynamically-configured Gemini model (via environment variables) to generate tailored CVs and cover letters (French "Moi, Vous, Nous" standard) directly from the application's Kanban pipeline. 

This plan leverages a **100% free hosting stack** using Render (for web/scoring service and unified scraping triggers), cron-job.org (for scheduling), Netlify (for frontend), and Neon/Upstash (for serverless database and cache).

---

## User Review Required

> [!IMPORTANT]
> - **GCP Avoided (100% Free Hosting)**: We have restructured the architecture to run the Scraper and Scorer inside a single FastAPI web service deployed to **Render (Free Tier)**. 
> - **Cron Scheduling**: Instead of Cloud Scheduler, we will use **cron-job.org** (or GitHub Actions crons) to ping a `/api/scrape` endpoint on Render every 6 hours, which handles waking up the service and running the scraper pipeline.
> - **Gemini API & Model Configuration**: We will load both the `GEMINI_API_KEY` and `GEMINI_MODEL_NAME` from environment variables, avoiding any hardcoded model defaults.
> - **Accomplishments Dump**: We are adding a new `user_feats` table where you can dump your historical achievements, metrics, and project details. The AI generator will selectively query and weave the most relevant feats into your CV and cover letter.

---

## Open Questions

- Do you have a preferred format for exporting tailored CVs? (e.g., raw markdown download, styling as clean HTML, or generating a styled PDF directly using standard browser printing?)
- For Indeed scraping, do you want to start with a simplified headless scraping approach or stick strictly to RSS/alternative job boards due to Indeed's heavy anti-bot protections?

---

## Proposed Changes

### 1. Database Schema Extensions

We will extend our Neon Postgres schema to support the master CV structure, accomplishments/feats, and link jobs with custom-generated application assets.

#### [MODIFY] [schema.sql](file:///Users/stephenakugbe/Documents/nodejs/jobradar/infra/schema.sql)
- Extend the `contract_type` constraint in comments or application validation to explicitly process `'cdi'`.
- Add a new table `user_profiles` to store user-specific metadata and the master CV markdown.
- Add a new table `user_feats` to store a searchable repository of accomplishments.
- Add `job_materials` to store custom-generated CVs and cover letters.

```sql
-- Extend existing schema
CREATE TABLE IF NOT EXISTS user_profiles (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name    TEXT NOT NULL,
  email        TEXT NOT NULL,
  phone        TEXT,
  github_url   TEXT,
  linkedin_url TEXT,
  master_cv    TEXT NOT NULL, -- markdown representation of base CV
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Accomplishments & Feats Repository
CREATE TABLE IF NOT EXISTS user_feats (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title        TEXT NOT NULL,         -- e.g., "Scaled background queue"
  description  TEXT NOT NULL,         -- Details of what you did, metrics (e.g. "reduced latency by 40%")
  skills_used  TEXT[],                -- e.g., ARRAY['redis', 'python', 'fastapi']
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Store tailored outputs per application
CREATE TABLE IF NOT EXISTS job_materials (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  tailored_cv     TEXT NOT NULL, -- tailored CV in markdown
  cover_letter    TEXT NOT NULL, -- cover letter text
  generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  version         INT DEFAULT 1,
  UNIQUE(job_id)
);
```

---

### 2. Backend Design (`services/scorer` & Scraper expansions)

We will adhere to OOP, SOLID principles, and DRY guidelines by creating clean, extensible abstractions.

#### [NEW] [llm.py](file:///Users/stephenakugbe/Documents/nodejs/jobradar/services/scorer/llm.py)
Create an abstract LLM interface (`LLMProvider`) to follow Dependency Inversion and Open/Closed principles, allowing easy swapping of LLM models or APIs in the future.

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Asynchronously generate text based on prompts."""
        pass
```

#### [NEW] [gemini_provider.py](file:///Users/stephenakugbe/Documents/nodejs/jobradar/services/scorer/gemini_provider.py)
Implement `LLMProvider` using the official `google-genai` SDK or `google-generativeai` HTTP client wrapper. Loads model name directly from the environment.

```python
import os
from .llm import LLMProvider
import google.generativeai as genai

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        # Load model name dynamically from env, fallback only if absolutely necessary
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=self.api_key)

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        response = await model.generate_content_async(prompt)
        return response.text
```

#### [NEW] [generator.py](file:///Users/stephenakugbe/Documents/nodejs/jobradar/services/scorer/generator.py)
Design a class `ApplicationMaterialGenerator` that utilizes `LLMProvider` to produce tailored CVs and "Moi, Vous, Nous" cover letters incorporating relevant feats.

```python
class ApplicationMaterialGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _build_cv_prompt(self, base_cv: str, accomplishments: list[dict], job_description: str) -> str:
        feats_text = "\n".join([f"- [{f['title']}] {f['description']} (Skills: {', '.join(f['skills_used'])})" for f in accomplishments])
        return f"""
You are an expert recruiter and CV writer. I will provide my master CV (in Markdown), a target Job Description, and a list of my accomplishments/feats.
Please rewrite and reorganize my CV to highlight the experience, tech stack, and keywords relevant to this job description.
Use the relevant accomplishments/feats listed below to bolster the project descriptions or work experience on my CV. Do not invent details.

Master CV:
{base_cv}

My Dump of Accomplishments/Feats:
{feats_text}

Job Description:
{job_description}

Provide the tailored CV in clean, valid Markdown formatting only.
"""

    def _build_cover_letter_prompt(self, base_cv: str, accomplishments: list[dict], company: str, job_title: str, job_description: str) -> str:
        feats_text = "\n".join([f"- [{f['title']}] {f['description']} (Skills: {', '.join(f['skills_used'])})" for f in accomplishments])
        return f"""
Write a professional French cover letter (Lettre de Motivation) for the role of '{job_title}' at '{company}' based on my CV and specific accomplishments.
You MUST strictly follow the French standard 'Moi, Vous, Nous' (Me, You, Us) structure:
1. **Moi (Me)**: Hook highlighting my profile, key skills, and select highly-relevant feats from my accomplishments list.
2. **Vous (You)**: Focus on the company, their technical challenges, values, or target market as inferred from the job description.
3. **Nous (Us)**: Detail what we can achieve together, bridging my capabilities and listed accomplishments with their issues, followed by a formal request for an interview.

My CV:
{base_cv}

My Relevant Accomplishments/Feats:
{feats_text}

Job Description:
{job_description}

Tone: Professional, persuasive, written in perfect, formal French (using 'vouvoiement'). Do not use generic placeholders; output a ready-to-copy letter.
"""

    async def generate(self, base_cv: str, accomplishments: list[dict], job: dict) -> dict:
        cv_system = "You are a professional CV optimizer. Output only valid Markdown."
        cl_system = "You are an expert French career coach writing formal Lettres de Motivation."

        cv_prompt = self._build_cv_prompt(base_cv, accomplishments, job["description"])
        cl_prompt = self._build_cover_letter_prompt(base_cv, accomplishments, job["company"], job["title"], job["description"])

        import asyncio
        tailored_cv, cover_letter = await asyncio.gather(
            self.llm.generate_text(cv_prompt, system_instruction=cv_system),
            self.llm.generate_text(cl_prompt, system_instruction=cl_system)
        )

        return {
            "tailored_cv": tailored_cv.strip(),
            "cover_letter": cover_letter.strip()
        }
```

#### [MODIFY] [main.py (FastAPI App)](file:///Users/stephenakugbe/Documents/nodejs/jobradar/services/scorer/main.py)
In this unified service architecture on Render:
- Expose `/api/scrape` (triggered by cron-job.org) to run the scraping asynchronously in the background.
- Expose `/api/feats` endpoints to manage accomplishments.
- Expose `/api/jobs/{job_id}/materials` to perform the LLM tailors.

---

### 3. Frontend Pages (Nuxt 3)

#### [NEW] [feats.vue](file:///Users/stephenakugbe/Documents/nodejs/jobradar/frontend/pages/feats.vue)
Add a page in the Nuxt frontend to manage accomplishments:
- An input form to dump a title, description, and list of tags/skills.
- A card list showing all your accomplishments.

#### [NEW] [ApplicationModal.vue](file:///Users/stephenakugbe/Documents/nodejs/jobradar/frontend/components/ApplicationModal.vue)
A sliding side drawer showing:
- Spinner status.
- **Tab 1: Tailored CV** with markdown preview.
- **Tab 2: Cover Letter (Moi, Vous, Nous)**.
- **Tab 3: Used Feats**: Checkboxes listing all accomplishments in the DB, letting you manually select/deselect which achievements the AI should prioritize when regenerating.

---

## Edge Cases & Performance Optimizations

1. **Render Free Tier Cold Start**:
   - Render free tier instances spin down after 15 minutes of inactivity. When cron-job.org calls `POST /api/scrape` every 6 hours, Render will automatically spin up the instance (this can take 30-50 seconds). The cron-job.org HTTP timeout should be configured to a high value (like 60s or more) or trigger an initial ping endpoint to wake it up.
2. **LLM Task Lazy Loading**:
   - We generate tailored content only when you click the "Generate" button in the UI, preserving free tier limits on Gemini and database resources.
3. **Queue Deduplication**:
   - Upstash REST calls run in O(1) time complexity prior to insertion, filtering out already-seen postings immediately.

---

## Verification Plan

### Automated Tests
* Mock the LLM to verify accomplishment injection in prompts.

### Manual Verification
1. Navigate to `/feats` on the local dashboard. Add a few mock achievements.
2. Trigger material generation for a job.
3. Verify that the generated CV and Cover letter highlight that specific feat.
