import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import json
import asyncio
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

logger = logging.getLogger("jobradar.scraper.hellowork")

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


class HelloWorkScraper(BaseScraper):
    source = "hellowork"
    base_url = "https://www.hellowork.com/fr-fr/emploi/recherche.html"

    def _normalize_contract(self, hw_contract: str | None) -> str | None:
        if not hw_contract:
            return None
        contract = hw_contract.lower().strip()
        if "alternance" in contract or "apprentissage" in contract or "professionnalisation" in contract:
            return "alternance"
        elif "cdi" in contract:
            return "cdi"
        elif "cdd" in contract:
            return "cdd"
        elif "stage" in contract:
            return "stage"
        return contract

    async def _fetch_full_description(self, client: httpx.AsyncClient, url: str, headers: dict) -> str:
        try:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                scripts = soup.find_all("script", type="application/ld+json")
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if data.get("@type") == "JobPosting":
                            description = data.get("description", "")
                            if description:
                                desc_soup = BeautifulSoup(description, "html.parser")
                                return desc_soup.get_text(separator="\n", strip=True)
                    except Exception:
                        pass
            else:
                logger.debug(f"HelloWork detail page HTTP {res.status_code} for {url}")
        except Exception as e:
            logger.debug(f"HelloWork detail fetch failed for {url}: {e}")
        return ""

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        query_lower = query.lower()

        contract_param = ""
        if "alternance" in query_lower:
            contract_param = "Alternance"
        elif "cdi" in query_lower:
            contract_param = "CDI"
        elif "stage" in query_lower:
            contract_param = "Stage"
        elif "cdd" in query_lower:
            contract_param = "CDD"

        location_param = "Paris" if "paris" in query_lower else "France"

        clean_words = [w for w in query.split() if w.lower().strip() not in STOPWORDS]
        keyword_param = " ".join(clean_words) if clean_words else "backend"

        params = {"k": keyword_param, "l": location_param}
        if contract_param:
            params["c"] = contract_param

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.hellowork.com/"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"HelloWork returned HTTP {response.status_code} for query '{query}'")
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                job_elements = soup.find_all("li")

                detail_tasks = []
                jobs_to_process = []

                for item in job_elements:
                    offer_id_el = item.find("input", {"name": "offerId"}) or item.find("input", {"name": "idOffre"})
                    title_el = item.find("input", {"name": "title"})
                    company_el = item.find("input", {"name": "company"})

                    if not offer_id_el or not title_el or not company_el:
                        continue

                    offer_id = offer_id_el.get("value")
                    title = title_el.get("value")
                    company = company_el.get("value")

                    if not offer_id or not title:
                        continue

                    url = f"https://www.hellowork.com/fr-fr/emplois/{offer_id}.html"

                    loc_el = item.find(attrs={"data-cy": "localisationCard"})
                    location = loc_el.get_text(strip=True) if loc_el else "Paris"

                    contract_el = item.find(attrs={"data-cy": "contractCard"}) or item.find(attrs={"data-cy": "contractTag"})
                    raw_contract = contract_el.get_text(strip=True) if contract_el else contract_param
                    contract_type = self._normalize_contract(raw_contract)

                    posted_at = datetime.now(timezone.utc)
                    date_el = item.find("div", class_=lambda x: x and "text-grey-500" in x)
                    if date_el:
                        date_text = date_el.get_text(strip=True).lower()
                        if "jour" in date_text:
                            days = re.findall(r'\d+', date_text)
                            if days:
                                posted_at = datetime.fromtimestamp(
                                    datetime.now().timestamp() - int(days[0]) * 86400, tz=timezone.utc
                                )
                        elif "heure" in date_text:
                            hours = re.findall(r'\d+', date_text)
                            if hours:
                                posted_at = datetime.fromtimestamp(
                                    datetime.now().timestamp() - int(hours[0]) * 3600, tz=timezone.utc
                                )

                    jobs_to_process.append({
                        "offer_id": offer_id,
                        "title": title,
                        "company": company,
                        "url": url,
                        "location": location,
                        "contract_type": contract_type,
                        "posted_at": posted_at
                    })
                    detail_tasks.append(self._fetch_full_description(client, url, headers))

                    if len(jobs_to_process) >= 10:
                        break

                logger.info(f"HelloWork query '{query}': {len(jobs_to_process)} listings found")
                descriptions = await asyncio.gather(*detail_tasks)

                for job_meta, full_desc in zip(jobs_to_process, descriptions):
                    desc_text = full_desc if full_desc else f"Poste de {job_meta['title']} chez {job_meta['company']}."

                    tech_stack = [t for t in TECH_KEYWORDS if t in desc_text.lower() or t in job_meta['title'].lower()]

                    yield RawJob(
                        external_id=str(job_meta['offer_id']),
                        source=self.source,
                        url=job_meta['url'],
                        title=job_meta['title'],
                        company=job_meta['company'],
                        location=job_meta['location'],
                        contract_type=job_meta['contract_type'],
                        description=desc_text,
                        posted_at=job_meta['posted_at'],
                        tech_stack=tech_stack
                    )
            except Exception as e:
                logger.error(f"HelloWork scraper error for query '{query}': {e}", exc_info=True)
