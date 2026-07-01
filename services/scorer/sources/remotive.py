import httpx
import logging
from datetime import datetime
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

logger = logging.getLogger("jobradar.scraper.remotive")

# Only English tech/role keywords make sense for Remotive (global English-language API)
RELEVANT_CATEGORIES = {
    "software-dev", "devops-sysadmin", "backend", "frontend", "full-stack",
    "engineering", "data", "mobile"
}


class RemotiveScraper(BaseScraper):
    source = "remotive"
    base_url = "https://remotive.com/api/remote-jobs"

    def _normalize_contract(self, remotive_type: str | None) -> str | None:
        if not remotive_type:
            return "cdi"
        t = remotive_type.lower()
        if "full" in t:
            return "cdi"
        if "contract" in t or "freelance" in t:
            return "cdd"
        if "intern" in t:
            return "stage"
        return "cdi"

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params = {
                "search": query,
                "limit": 15
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            try:
                response = await client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"Remotive returned HTTP {response.status_code} for query '{query}'")
                    return

                data = response.json()
                jobs = data.get("jobs", [])
                logger.info(f"Remotive query '{query}': {len(jobs)} jobs")

                for job in jobs:
                    # Skip clearly non-technical roles
                    category = job.get("category", "").lower().replace(" ", "-")
                    if category and not any(cat in category for cat in RELEVANT_CATEGORIES):
                        logger.debug(f"Remotive: skipping non-tech category '{category}' for '{job.get('title')}'")
                        continue

                    pub_date_str = job.get("publication_date")
                    posted_at = None
                    if pub_date_str:
                        try:
                            posted_at = datetime.fromisoformat(pub_date_str)
                        except ValueError:
                            pass

                    yield RawJob(
                        external_id=str(job.get("id")),
                        source=self.source,
                        url=job.get("url", ""),
                        title=job.get("title", "Unknown Title"),
                        company=job.get("company_name", "Unknown Company"),
                        location=job.get("candidate_required_location", "Remote"),
                        contract_type=self._normalize_contract(job.get("job_type")),
                        description=job.get("description", ""),
                        posted_at=posted_at,
                        tech_stack=job.get("tags", [])
                    )
            except Exception as e:
                logger.error(f"Remotive scraper error for query '{query}': {e}", exc_info=True)
