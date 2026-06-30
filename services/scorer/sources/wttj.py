import httpx
from datetime import datetime
from typing import AsyncGenerator
from sources.base import BaseScraper, RawJob

class WelcomeToTheJungleScraper(BaseScraper):
    source = "wttj"
    base_url = "https://www.welcometothejungle.com/api/v1/jobs"

    def _normalize_contract(self, wttj_contract: str | None) -> str | None:
        """Map Welcome to the Jungle contract tags to our internal keys."""
        if not wttj_contract:
            return None
        contract = wttj_contract.lower()
        if contract in ["apprenticeship", "alternance"]:
            return "alternance"
        elif contract in ["full-time", "cdi"]:
            return "cdi"
        elif contract in ["temporary", "cdd"]:
            return "cdd"
        elif contract in ["internship", "stage"]:
            return "stage"
        return contract

    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        """Fetch matching job postings from the WTTJ API endpoint."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            page = 1
            max_pages = 2  # Keep execution fast, fetch first two pages per query
            
            while page <= max_pages:
                # WTTJ API parameters
                params = {
                    "query": query,
                    "aroundQuery": "Paris, France",
                    "page": page,
                    "contract_types[]": ["alternance", "full_time"]
                }
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                response = await client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    break

                data = response.json()
                jobs = data.get("jobs", [])
                if not jobs:
                    break

                for job in jobs:
                    # Parse dates
                    published_at_str = job.get("published_at")
                    posted_at = None
                    if published_at_str:
                        try:
                            # Parse ISO string
                            posted_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # Extract location
                    office = job.get("office") or {}
                    location = office.get("city") or office.get("district")

                    # Extract company name
                    company_data = job.get("company") or {}
                    company_name = company_data.get("name") or "Unknown"

                    # Build URL
                    slug = job.get("slug")
                    url = f"https://www.welcometothejungle.com/fr/companies/{company_data.get('slug')}/jobs/{slug}" if slug else ""

                    # Contract normalization
                    contract_info = job.get("contract_type")
                    contract_type = self._normalize_contract(contract_info)

                    # Extract tech tags
                    tech_stack = []
                    tags = job.get("profile", {}).get("tags", [])
                    for tag in tags:
                        if isinstance(tag, dict) and tag.get("name"):
                            tech_stack.append(tag.get("name").lower())

                    # Compose full description from sections if available
                    description = job.get("description") or ""
                    profile_reqs = job.get("profile") or ""
                    full_desc = f"{description}\n\nProfil:\n{profile_reqs}" if profile_reqs else description

                    yield RawJob(
                        external_id=str(job.get("id")),
                        source=self.source,
                        url=url,
                        title=job.get("title", "Unknown Title"),
                        company=company_name,
                        location=location,
                        contract_type=contract_type,
                        description=full_desc,
                        posted_at=posted_at,
                        tech_stack=tech_stack
                    )
                
                page += 1
