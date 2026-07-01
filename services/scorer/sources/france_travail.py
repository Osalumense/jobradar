import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import asyncio
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

logger = logging.getLogger("jobradar.scraper.francetravail")

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


class FranceTravailScraper(BaseScraper):
    source = "francetravail"
    base_url = "https://candidat.francetravail.fr/offres/recherche"

    def _normalize_contract(self, ft_contract: str | None) -> str | None:
        if not ft_contract:
            return None
        contract = ft_contract.lower().strip()
        if "alternance" in contract or "apprentissage" in contract or "contrat pro" in contract:
            return "alternance"
        elif "cdi" in contract:
            return "cdi"
        elif "cdd" in contract:
            return "cdd"
        elif "stage" in contract:
            return "stage"
        return contract

    async def _fetch_detail_page(self, client: httpx.AsyncClient, url: str, headers: dict) -> tuple[str, str]:
        try:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")

                desc_el = (
                    soup.find(attrs={"itemprop": "description"})
                    or soup.find("div", class_="description")
                    or soup.find("div", class_=lambda c: c and "job-detail" in c)
                )
                description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""

                company = "Confidentiel"
                # Try itemprop first
                org_el = soup.find(attrs={"itemprop": "hiringOrganization"})
                if org_el:
                    name_el = org_el.find(attrs={"itemprop": "name"})
                    company = (name_el or org_el).get_text(strip=True) or "Confidentiel"
                else:
                    # Fallback: look for common company selectors on FT detail pages
                    company_el = (
                        soup.find("span", class_=lambda c: c and "entreprise" in c)
                        or soup.find("div", class_=lambda c: c and "entreprise" in c)
                        or soup.find("p", class_=lambda c: c and "subtext" in c)
                    )
                    if company_el:
                        company = company_el.get_text(strip=True) or "Confidentiel"

                return description, company
            else:
                logger.debug(f"France Travail detail page HTTP {res.status_code} for {url}")
        except Exception as e:
            logger.debug(f"France Travail detail fetch failed for {url}: {e}")
        return "", "Confidentiel"

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        query_lower = query.lower()

        location_param = "75D" if "paris" in query_lower else ""

        clean_words = [w for w in query.split() if w.lower().strip() not in STOPWORDS]
        keyword_param = " ".join(clean_words) if clean_words else "backend"

        params = {"motsCles": keyword_param}
        if location_param:
            params["lieux"] = location_param
        if "alternance" in query_lower or "apprentissage" in query_lower:
            params["natureContrat"] = "E2"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://candidat.francetravail.fr/"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"France Travail returned HTTP {response.status_code} for query '{query}'")
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                job_elements = soup.find_all("li", class_="result")

                detail_tasks = []
                jobs_meta = []

                for item in job_elements:
                    offer_id = item.get("data-id-offre")
                    if not offer_id:
                        continue

                    title_el = item.find("span", class_="media-heading-title")
                    title = title_el.get_text(strip=True) if title_el else "Offre d'emploi"

                    loc_el = item.find("p", class_="subtext")
                    location = loc_el.get_text(strip=True) if loc_el else "Paris"
                    # Strip nested span text (sometimes "75 - Paris" has extra structure)
                    location = re.sub(r'\s+', ' ', location).strip()

                    contrat_el = item.find("p", class_="contrat")
                    raw_contrat = contrat_el.get_text(strip=True) if contrat_el else (
                        "Alternance" if "natureContrat" in params else "CDI"
                    )
                    contract_type = self._normalize_contract(raw_contrat)

                    detail_url = f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"

                    posted_at = datetime.now(timezone.utc)
                    date_el = item.find("p", class_="date")
                    if date_el:
                        date_text = date_el.get_text(strip=True).lower()
                        days = re.findall(r'\d+', date_text)
                        if days:
                            posted_at = datetime.fromtimestamp(
                                datetime.now().timestamp() - int(days[0]) * 86400, tz=timezone.utc
                            )

                    jobs_meta.append({
                        "offer_id": offer_id,
                        "title": title,
                        "location": location,
                        "contract_type": contract_type,
                        "url": detail_url,
                        "posted_at": posted_at
                    })
                    detail_tasks.append(self._fetch_detail_page(client, detail_url, headers))

                    if len(jobs_meta) >= 10:
                        break

                logger.info(f"France Travail query '{query}': {len(jobs_meta)} listings found")
                details = await asyncio.gather(*detail_tasks)

                for meta, (full_desc, company) in zip(jobs_meta, details):
                    desc_text = full_desc if full_desc else f"Poste de {meta['title']} à {meta['location']}."

                    tech_stack = [t for t in TECH_KEYWORDS if t in desc_text.lower() or t in meta['title'].lower()]

                    yield RawJob(
                        external_id=str(meta['offer_id']),
                        source=self.source,
                        url=meta['url'],
                        title=meta['title'],
                        company=company,
                        location=meta['location'],
                        contract_type=meta['contract_type'],
                        description=desc_text,
                        posted_at=meta['posted_at'],
                        tech_stack=tech_stack
                    )
            except Exception as e:
                logger.error(f"France Travail scraper error for query '{query}': {e}", exc_info=True)
