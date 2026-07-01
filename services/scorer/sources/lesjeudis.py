import httpx
import logging
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

logger = logging.getLogger("jobradar.scraper.lesjeudis")

TECH_KEYWORDS = [
    "python", "fastapi", "node", "nodejs", "typescript", "javascript",
    "nestjs", "express", "postgres", "postgresql", "redis", "docker",
    "kubernetes", "django", "flask", "aws", "gcp", "azure", "sql",
    "mongodb", "graphql", "php", "laravel", "symfony", "vue", "react",
    "nuxt", "terraform", "gitlab", "github", "java", "spring", "go",
    "rust", "c++", "c#", ".net", "angular"
]

STOPWORDS = {
    "alternance", "cdi", "stage", "cdd", "paris", "france", "de", "d'",
    "développeur", "developpeur", "ingénieur", "ingenieur", "developer",
    "engineer", "lead", "senior", "junior", "intern", "apprentissage"
}


class LesJeudiscraper(BaseScraper):
    source = "lesjeudis"
    base_url = "https://www.lesjeudis.com/fr/jobs/"

    def _normalize_contract(self, contract_str: str | None) -> str | None:
        if not contract_str:
            return None
        c = contract_str.lower().strip()
        if "alternance" in c or "apprentissage" in c:
            return "alternance"
        elif "cdi" in c or "permanent" in c or "full" in c:
            return "cdi"
        elif "cdd" in c or "temporary" in c or "fixed" in c:
            return "cdd"
        elif "stage" in c or "intern" in c:
            return "stage"
        elif "freelance" in c or "mission" in c:
            return "freelance"
        return contract_str

    def _extract_jobs_from_apollo(self, html_text: str) -> list[dict]:
        """Extract job listings from the __NEXT_DATA__ Apollo State embedded in HTML."""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if not script or not script.string:
                return []

            data = json.loads(script.string)
            apollo_state = (
                data.get("props", {})
                .get("pageProps", {})
                .get("__APOLLO_STATE__", {})
            )

            jobs = []
            for key, obj in apollo_state.items():
                if not key.startswith("Job:"):
                    continue
                jobs.append(obj)
            return jobs
        except Exception as e:
            logger.debug(f"LesJeudis Apollo extraction error: {e}")
            return []

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        query_lower = query.lower()

        clean_words = [w for w in query.split() if w.lower().strip() not in STOPWORDS]
        keyword_param = " ".join(clean_words) if clean_words else "backend"

        # LesJeudis URL params
        params = {"search": keyword_param}
        if "paris" in query_lower:
            params["location"] = "Paris"
        if "alternance" in query_lower:
            params["contract_type"] = "ALTERNANCE"
        elif "stage" in query_lower:
            params["contract_type"] = "INTERNSHIP"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Referer": "https://www.lesjeudis.com/"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"LesJeudis returned HTTP {response.status_code} for query '{query}'")
                    return

                raw_jobs = self._extract_jobs_from_apollo(response.text)
                logger.info(f"LesJeudis query '{query}': {len(raw_jobs)} jobs extracted from Apollo state")

                for job in raw_jobs:
                    job_id = job.get("id")
                    title = job.get("title", "").strip()
                    company = job.get("organization", "").strip()

                    if not job_id or not title:
                        continue

                    url_path = (job.get("urlNoPrefix") or job.get("url", {}).get("path", "") if isinstance(job.get("url"), dict) else "")
                    url = f"https://www.lesjeudis.com{url_path}" if url_path else f"https://www.lesjeudis.com/fr/job/{job_id}"

                    # Location - stored as list
                    address_list = job.get("address", [])
                    location = address_list[0] if address_list else "France"

                    # Contract type — LesJeudis Apollo state doesn't expose this directly;
                    # default to cdi as the site is predominantly permanent IT roles.
                    contract_type = "cdi"

                    # Salary info (bonus context for description)
                    salary_list = job.get("salaryRange", [])
                    salary_str = ""
                    if isinstance(salary_list, list) and salary_list:
                        salary_str = salary_list[0].get("label", "") if isinstance(salary_list[0], dict) else ""

                    # Date
                    posted_at = datetime.now(timezone.utc)
                    pub_str = job.get("published")
                    if pub_str:
                        try:
                            posted_at = datetime.fromisoformat(pub_str)
                        except (ValueError, TypeError):
                            pass

                    # Build description from available metadata
                    description = f"Poste de {title} chez {company}.\nLocalisation : {location}."
                    if salary_str:
                        description += f"\nSalaire : {salary_str}."

                    tech_stack = [t for t in TECH_KEYWORDS if t in title.lower() or t in description.lower()]

                    yield RawJob(
                        external_id=str(job_id),
                        source=self.source,
                        url=url,
                        title=title,
                        company=company or "Confidentiel",
                        location=location,
                        contract_type=contract_type,
                        description=description,
                        posted_at=posted_at,
                        tech_stack=tech_stack
                    )
            except Exception as e:
                logger.error(f"LesJeudis scraper error for query '{query}': {e}", exc_info=True)
