from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
import hashlib

@dataclass
class RawJob:
    external_id: str
    source: str
    url: str
    title: str
    company: str
    location: str | None
    contract_type: str | None
    description: str
    posted_at: datetime | None
    tech_stack: list[str] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        """Create a unique identifier based on job core properties."""
        raw = f"{self.title}{self.company}{self.description[:200]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "external_id": self.external_id,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "contract_type": self.contract_type,
            "description": self.description,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "tech_stack": self.tech_stack,
            "content_hash": self.content_hash,
        }

class BaseScraper(ABC):
    source: str
    base_url: str
    
    # Generic developer search queries targeting both Alternance and CDI
    search_queries: list[str] = [
        "alternance développeur backend paris",
        "développeur backend cdi paris",
        "ingénieur logiciel alternance paris",
        "développeur fullstack cdi paris",
        "développeur web alternance paris"
    ]

    @abstractmethod
    async def fetch_listings(self, query: str) -> AsyncGenerator[RawJob, None]:
        """Yield RawJob objects for a given search query."""
        pass

    async def run(self) -> list[RawJob]:
        """Collect all jobs across queries and return deduplicated list of RawJobs."""
        collected_jobs = {}
        for query in self.search_queries:
            try:
                async for job in self.fetch_listings(query):
                    collected_jobs[job.content_hash] = job
            except Exception as e:
                # Log or print error and proceed defensively
                print(f"Error scraping query '{query}' on {self.source}: {e}")
        return list(collected_jobs.values())
