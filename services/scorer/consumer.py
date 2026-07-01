import httpx
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from job_queue import JobQueue
from db import DatabaseClient
from scorer import CompositeScorer
from embedder import GeminiEmbedder
from alert import ResendAlerter

logger = logging.getLogger("jobradar.consumer")

class QueueConsumer:
    def __init__(
        self, 
        queue: JobQueue, 
        db: DatabaseClient, 
        scorer: CompositeScorer,
        embedder: GeminiEmbedder,
        alerter: ResendAlerter
    ):
        self.queue = queue
        self.db = db
        self.scorer = scorer
        self.embedder = embedder
        self.alerter = alerter



    async def consume_all(self, client: httpx.AsyncClient, user_id: Optional[str] = None) -> int:
        """Process all currently queued jobs. Caches profile embedding for the run."""
        profile = await self.db.get_profile(user_id)
        if not profile:
            logger.warning("Consumer: no profile configured, skipping queue.")
            return 0

        profile_text = profile.get("profile_text", "")
        logger.info("Consumer: fetching profile embedding for this run...")
        profile_embedding = await self.embedder.get_embedding(profile_text)

        processed_count = 0
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5

        while True:
            try:
                result = await self._process_next(client, profile, profile_text, profile_embedding, user_id)
                if result is None:
                    break
                processed_count += 1
                consecutive_errors = 0
                logger.info(
                    f"Processed [{processed_count}]: {result['title']} @ {result['company']} "
                    f"— score={result['score']:.2f}"
                )
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Consumer error (attempt {consecutive_errors}): {e}", exc_info=True)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(f"Stopping consumer after {MAX_CONSECUTIVE_ERRORS} consecutive errors")
                    break
                continue

        logger.info(f"Consumer finished. Jobs processed this run: {processed_count}")
        return processed_count

    async def _process_next(
        self, client: httpx.AsyncClient,
        profile: dict, profile_text: str, profile_embedding: list,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Pop one job from queue, score it using the pre-fetched profile embedding, save it."""
        job_data = await self.queue.dequeue(client)
        if not job_data:
            return None

        content_hash = job_data.get("content_hash")
        if not content_hash:
            return None

        if await self.queue.is_seen(client, content_hash):
            logger.info(f"Dedup: '{job_data.get('title')}' already processed, skipping.")
            return None

        posted_at_str = job_data.get("posted_at")
        posted_at = None
        if posted_at_str:
            try:
                posted_at = datetime.fromisoformat(posted_at_str)
            except ValueError:
                pass

        score_details = await self.scorer.score_job(
            description=job_data.get("description", ""),
            posted_at=posted_at,
            profile_text=profile_text,
            profile_embedding=profile_embedding,
            keywords=profile.get("keywords", []),
            excluded=profile.get("excluded", []),
            contract_type=job_data.get("contract_type"),
            location=job_data.get("location"),
            target_contracts=profile.get("target_contracts", []),
            target_locations=profile.get("target_locations", [])
        )

        job_id = await self.db.insert_job(job_data)
        await self.db.update_job_scores(job_id, score_details, user_id)

        composite_score = score_details.get("composite", 0.0)
        email_sent = False
        min_score = profile.get("min_score", 0.65)

        if composite_score >= min_score:
            email_sent = await self.alerter.send_job_alert(client, job_data, score_details)
            if email_sent:
                async with self.db.pool.acquire() as conn:
                    await conn.execute("UPDATE jobs SET alerted = TRUE WHERE id = $1", job_id)

        await self.queue.mark_seen(client, content_hash)

        return {
            "job_id": job_id,
            "title": job_data.get("title"),
            "company": job_data.get("company"),
            "score": composite_score,
            "alerted": email_sent
        }
