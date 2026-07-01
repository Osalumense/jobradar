import httpx
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

logger = logging.getLogger("jobradar.scraper.wttj")

TECH_KEYWORDS = [
    "python", "fastapi", "node", "nodejs", "typescript", "javascript",
    "nestjs", "express", "postgres", "postgresql", "redis", "docker",
    "kubernetes", "django", "flask", "aws", "gcp", "azure", "sql",
    "mongodb", "graphql", "php", "laravel", "symfony", "vue", "react",
    "nuxt", "terraform", "gitlab", "github"
]

STOPWORDS = {
    "alternance", "cdi", "stage", "cdd", "paris", "france", "de", "d'",
    "développeur", "developpeur", "ingénieur", "ingenieur", "developer",
    "engineer", "lead", "senior", "junior", "intern", "apprentissage"
}


class WelcomeToTheJungleScraper(BaseScraper):
    source = "wttj"
    base_url = "https://csekhvms53-dsn.algolia.net/1/indexes/*/queries"

    def _normalize_contract(self, wttj_contract: str | None) -> str | None:
        if not wttj_contract:
            return None
        contract = wttj_contract.lower().strip()
        if contract in ["apprenticeship", "alternance"]:
            return "alternance"
        elif contract in ["full_time", "full-time", "cdi"]:
            return "cdi"
        elif contract in ["temporary", "cdd"]:
            return "cdd"
        elif contract in ["internship", "stage"]:
            return "stage"
        return contract

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        clean_words = [w for w in query.split() if w.lower().strip() not in STOPWORDS]
        keyword_param = " ".join(clean_words) if clean_words else "backend"

        headers = {
            "x-algolia-application-id": "CSEKHVMS53",
            "x-algolia-api-key": "4bd8f6215d0cc52b26430765769e65a0",
            "Content-Type": "application/json",
            "Referer": "https://www.welcometothejungle.com/fr/jobs",
            "Origin": "https://www.welcometothejungle.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        location_filter = 'office.city:Paris' if "paris" in query.lower() else ''
        params_str = f"query={keyword_param}"
        if location_filter:
            params_str += f"&facetFilters=[[\"{location_filter}\"]]"

        payload = {
            "requests": [
                {
                    "indexName": "wk_cms_jobs_production",
                    "params": params_str
                }
            ]
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"WTTJ returned HTTP {response.status_code} for query '{query}'")
                    return

                data = response.json()
                results = data.get("results", [])
                if not results:
                    logger.warning(f"WTTJ returned no results array for query '{query}'")
                    return

                hits = results[0].get("hits", [])
                logger.info(f"WTTJ query '{query}': {len(hits)} hits")

                for hit in hits:
                    slug = hit.get("slug")
                    org_slug = hit.get("organization", {}).get("slug")
                    if not slug or not org_slug:
                        continue

                    url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}"
                    contract_type = self._normalize_contract(hit.get("contract_type"))
                    office_city = hit.get("office", {}).get("city") or "Paris"

                    published_at_str = hit.get("published_at")
                    posted_at = datetime.now(timezone.utc)
                    if published_at_str:
                        try:
                            posted_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    sectors = hit.get("sectors_name", {}).get("fr", [])
                    sector_list = []
                    for sect in sectors:
                        if isinstance(sect, dict):
                            sector_list.extend(sect.values())
                    sector_str = ", ".join(sector_list) if sector_list else "Technologie"

                    company_desc = hit.get("organization", {}).get("descriptions", {}).get("fr", "")
                    title = hit.get("name", "Unknown Title")
                    company = hit.get("organization", {}).get("name", "Unknown Company")

                    full_desc = (
                        f"Poste de {title} chez {company} situé à {office_city}.\n"
                        f"Contrat : {hit.get('contract_type_names', {}).get('fr', hit.get('contract_type', ''))}.\n"
                        f"Secteurs : {sector_str}.\n\n"
                        f"Présentation de l'entreprise :\n{company_desc}"
                    )

                    tech_stack = [t for t in TECH_KEYWORDS if t in full_desc.lower() or t in title.lower()]

                    yield RawJob(
                        external_id=str(hit.get("objectID")),
                        source=self.source,
                        url=url,
                        title=title,
                        company=company,
                        location=office_city,
                        contract_type=contract_type,
                        description=full_desc,
                        posted_at=posted_at,
                        tech_stack=tech_stack
                    )
            except Exception as e:
                logger.error(f"WTTJ scraper error for query '{query}': {e}", exc_info=True)
