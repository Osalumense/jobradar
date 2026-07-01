# JobRadar Fetching Expansion Roadmap

## Goal

Expand JobRadar from a small proof-of-concept scraper set into a broader French job discovery pipeline that:

- Fetches substantially more jobs across generalist, tech, startup, alternance, and executive/cadre boards.
- Stores every fetched job even when it is imperfect or low-scoring.
- Scores jobs transparently so the user can decide whether to apply.
- Builds search queries dynamically from the uploaded CV, profile preferences, target roles, target contracts, target locations, and detected technologies.
- Avoids hardcoded stack assumptions such as Python-only or backend-only searches.

## Current State

Implemented or present in the current service:

| Source | Current Status | Notes |
|---|---:|---|
| Welcome to the Jungle | Implemented | Uses the WTTJ Algolia endpoint. Good source for startups, scaleups, tech-friendly companies, CDI, and alternance. |
| HelloWork | Implemented | Generalist/regional French source. Good for volume, alternance, and local postings. |
| France Travail | Implemented | Public employment source. Good coverage but noisier job quality. |
| Remotive | Implemented | Remote global jobs. Useful, but many jobs will not match Paris/France/alternance preferences. |

Important behavior decision:

- Scrapers should fetch broadly.
- Scoring should rank and explain.
- UI/API should show scraped jobs and score components.
- Alerts can still use `profile.min_score`, but the dashboard should not hide low-score jobs.

## Source Priorities

### Priority 1 - Best Immediate Additions

These should be added first because they match the JobRadar goal and planning documents closely.

| Source | Why Add It | Suggested Access Strategy | Implementation Notes |
|---|---|---|---|
| APEC | Strong for qualified/cadre engineering roles, software roles, and CDI roles in France. Already planned in the original spec. | Prefer public search endpoints if discoverable; otherwise HTML parsing with `httpx` + BeautifulSoup. | Add `services/scorer/sources/apec.py`. Normalize cadre/CDI roles. Use profile roles and tech terms in `motsCles`/query params. |
| JobTeaser | Strong for students, graduates, internships, and alternance. Very relevant for apprenticeship search. | Investigate public routes/API calls from the browser network tab. Fall back to HTML parsing. | Add `jobteaser.py`. Prioritize `alternance`, `apprentissage`, `stage`, junior roles, Paris/Ile-de-France. |
| Indeed France | High-volume generalist source. Original plan lists Indeed as a later source. | Prefer RSS/lightweight routes or a provider API if available. Avoid aggressive direct scraping. | Add `indeed.py` only with conservative request rates and clear failure logging. Expect anti-bot changes. |
| LinkedIn Jobs | Very important market signal and recruiter activity source. | Prefer manual import, saved-search email parsing, or official/partner API. Avoid brittle scraping as default. | If implemented, isolate behind `LINKEDIN_FETCH_ENABLED=false` by default. Treat as optional. |

### Priority 2 - Tech-Specific Sources

These improve relevance for developer and software engineering roles.

| Source | Why Add It | Suggested Access Strategy | Implementation Notes |
|---|---|---|---|
| WeLoveDevs | Developer-focused French tech board. Better signal than generic boards for engineering roles. | Inspect public search network calls. Fall back to HTML parsing. | Add `welovedevs.py`. Extract stack tags where possible; these are useful for score explanations. |
| LesJeudis | IT/digital recruiting source in France. Good for tech and infrastructure roles. | HTML parsing or public search endpoint. | Add `lesjeudis.py`. Expect ESN-heavy results; score and tag company/source clearly. |
| WeAreDevelopers France | Broad developer listings and strong tech taxonomy. | Inspect JSON embedded in page or public endpoint. | Add `wearedevelopers.py`. Good source for tech tags such as PHP, JavaScript, Python, DevOps, cloud. |
| Talent.io | Startup/tech recruitment marketplace. | Check for public job listing pages. | Add only if public listings are accessible without login. Otherwise keep as manual/source-link tracker. |
| ChooseYourBoss | French tech recruitment marketplace. | Check public listings first. | Add only if listings are publicly accessible and stable. |

### Priority 3 - Startup and Ecosystem Sources

These help surface companies that may not appear prominently on general boards.

| Source | Why Add It | Suggested Access Strategy | Implementation Notes |
|---|---|---|---|
| La French Tech / WelcomeKit | French Tech startup ecosystem, likely rich in startup engineering roles. | The French Tech job link points to a WelcomeKit-powered board; inspect public board endpoints. | Add `french_tech.py` or a generic `welcomekit.py` scraper that can accept multiple board URLs. |
| Station F Jobs | Startup jobs from Station F ecosystem. | Inspect public job routes/endpoints. | Add if listings are public. Good for startups and junior roles. |
| Bpifrance / Les Deeptech jobs | Useful for startups, innovation, AI, cloud, data, industrial tech. | Public pages first, conservative scraping. | Lower priority unless user wants startup/deeptech focus. |

### Priority 4 - Additional Generalist Sources

These increase coverage but may add noise.

| Source | Why Add It | Suggested Access Strategy | Implementation Notes |
|---|---|---|---|
| Le Figaro Emploi | General French job board with large volume. | HTML parsing or public endpoint. | Add after APEC/JobTeaser/Indeed. |
| Meteojob | Common French job site. | HTML parsing or public endpoint. | Good for regional coverage, may overlap with HelloWork. |
| Monster France | Generalist source with IT roles. | HTML parsing or public endpoint. | Lower priority because relevance may be mixed. |
| Glassdoor France | Useful but often protected and noisy. | Prefer links/imports, avoid fragile scraping. | Optional. |
| Jobijoba | Aggregator; useful for coverage but dedupe must be strong. | HTML parsing. | Mark as aggregator to avoid duplicate confusion. |

## Implementation Pattern

Every new source should follow this structure:

1. Create a new scraper file under `services/scorer/sources/<source>.py`.
2. Subclass `BaseScraper`.
3. Implement `fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]`.
4. Normalize fields into `RawJob`:
   - `external_id`
   - `source`
   - `url`
   - `title`
   - `company`
   - `location`
   - `contract_type`
   - `description`
   - `posted_at`
   - `tech_stack`
5. Add the scraper to `run_scraper_and_consume()` in `services/scorer/main.py`.
6. Log scraper run health through `scrape_runs`.
7. Add a direct smoke test script or pytest test for one query.

## Contract Normalization

All scrapers should map source-specific contract labels to the internal contract keys:

| Internal Value | Source Labels to Map |
|---|---|
| `alternance` | alternance, apprentissage, apprenticeship, contrat de professionnalisation, contrat pro |
| `cdi` | CDI, full time, full-time, permanent |
| `cdd` | CDD, temporary, contract, fixed-term |
| `stage` | stage, internship, intern |
| `freelance` | freelance, indépendant, mission, profession libérale |

Do not drop jobs with unknown or imperfect contracts. Store them with the best normalized value or the original cleaned string.

## Dynamic Query Strategy

Search queries should be generated from:

- Uploaded CV detected technologies.
- Explicit `target_tech`.
- `target_roles`.
- `target_contracts`.
- `target_locations`.

Rules:

- Do not hardcode Python, Node, PHP, or any stack as the default.
- If the user has no explicit tech terms, use role/location/contract generic queries.
- Keep source-specific query cleaning, but never reduce empty queries to a single technology.
- Limit per-run query count to keep Render/Upstash/Gemini usage controlled.

Suggested query count:

- 6 to 12 profile queries per full scrape.
- Top 10 to 20 jobs per source/query.
- Deduplicate by `content_hash` and `(source, external_id)`.

## Scoring and Display Rules

Fetching and scoring should remain separate:

- Scrapers fetch jobs.
- Queue stores jobs.
- Consumer scores jobs.
- Dashboard displays all scraped/scored jobs.
- Alerts are thresholded, but dashboard visibility is not.

Do not use excluded keywords as hard delete rules. If a job mentions a less-preferred technology, let it affect score or tags, but keep the job visible.

Recommended score display:

- Composite score.
- Semantic score.
- Keyword score.
- Recency score.
- Contract/location preference badges.
- Matched tech tags.
- Source badge.

## Recommended Build Order

1. Stabilize current four sources and dashboard score display.
2. Add APEC scraper.
3. Add JobTeaser scraper.
4. Add Indeed lightweight/RSS-style scraper if a stable route is found.
5. Add WeLoveDevs and LesJeudis for tech-specific coverage.
6. Add a generic WelcomeKit scraper, then use it for French Tech ecosystem jobs.
7. Add WeAreDevelopers France.
8. Add optional LinkedIn/import flow only after the core sources are reliable.
9. Add source health UI: last run, jobs found, jobs new, error.
10. Add per-source enable/disable settings to control noise and API cost.

## Per-Source Test Plan

For every new source:

- Run one direct scraper query locally.
- Confirm at least one job is yielded when the site has results.
- Confirm `RawJob.content_hash` is stable.
- Confirm duplicate runs do not enqueue already-seen jobs.
- Confirm `scrape_runs.jobs_found` and `jobs_new` update.
- Confirm the dashboard shows the job even when score is low.
- Confirm source-specific failures are logged without breaking other sources.

## Operational Guardrails

- Keep request timeouts short: 10 to 20 seconds.
- Use a realistic user agent.
- Prefer public APIs/endpoints over brittle HTML parsing.
- Respect robots/terms and avoid bypassing authentication or anti-bot protections.
- Add per-source failure isolation so one broken scraper does not stop the whole scrape.
- Use conservative concurrency for HTML sources.
- Avoid LinkedIn/Indeed aggressive scraping unless a stable, compliant path is found.

## Future Data Model Improvements

The current `jobs` table can support the next phase, but these additions would make fetching better:

- `raw_payload JSONB` for source-specific fields.
- `source_query TEXT` to know which query found the job.
- `source_rank INT` for ranking position in the original board.
- `is_remote BOOLEAN`.
- `seniority TEXT`.
- `salary_min`, `salary_max`, `salary_currency`.
- `score_reasons JSONB` for transparent scoring explanations.
- `last_seen_at TIMESTAMPTZ` to track jobs that remain active over time.

## Definition of Done

The fetching expansion is successful when:

- At least 7 reliable sources run without blocking each other.
- A normal scrape returns a broad set of jobs, not just one visible result.
- Low-score jobs remain visible with score breakdowns.
- Search queries reflect the actual CV/profile stack, including PHP, Node.js, TypeScript, Python, or whatever appears in the profile.
- Source run health is visible enough to diagnose when a site changes markup or blocks requests.
