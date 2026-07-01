"""
Direct scraper smoke test - runs each scraper against live sites and prints results.
Usage: python test_scrapers.py
"""
import asyncio
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from sources.wttj import WelcomeToTheJungleScraper
from sources.hellowork import HelloWorkScraper
from sources.france_travail import FranceTravailScraper
from sources.remotive import RemotiveScraper
from sources.lesjeudis import LesJeudiscraper

TEST_QUERIES_FR = ["développeur backend paris", "alternance développeur paris"]
TEST_QUERIES_EN = ["backend developer", "fullstack developer"]


async def test_scraper(scraper, queries):
    scraper.search_queries = queries
    try:
        jobs = await scraper.run()
        print(f"\n  [OK] {scraper.source}: {len(jobs)} unique jobs")
        for j in jobs[:3]:
            company = j.company or "???"
            print(f"       - {j.title[:60]} @ {company[:30]} ({j.contract_type}) [{j.location}]")
        return len(jobs)
    except Exception as e:
        print(f"\n  [FAIL] {scraper.source}: {e}")
        return 0


async def main():
    scrapers = [
        (WelcomeToTheJungleScraper(), TEST_QUERIES_FR),
        (HelloWorkScraper(), TEST_QUERIES_FR),
        (FranceTravailScraper(), TEST_QUERIES_FR),
        (LesJeudiscraper(), TEST_QUERIES_EN),
        (RemotiveScraper(), TEST_QUERIES_EN),
    ]

    print("=== Scraper Live Test ===")
    total = 0
    for scraper, queries in scrapers:
        n = await test_scraper(scraper, queries)
        total += n

    print(f"\n{'='*40}")
    print(f"Total unique jobs fetched across all sources: {total}")

if __name__ == "__main__":
    asyncio.run(main())
