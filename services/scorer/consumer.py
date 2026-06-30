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

    async def process_next_job(self, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
        """Pop a job from the Redis queue, score it, save it, and alert if high match."""
        # 1. Fetch next job from Upstash Redis Queue
        job_data = await self.queue.dequeue(client)
        if not job_data:
            return None

        content_hash = job_data.get("content_hash")
        if not content_hash:
            return None

        # Double check seen list (dedup fallback)
        if await self.queue.is_seen(client, content_hash):
            logger.info(f"Deduplication fallback: Job {job_data.get('title')} already processed. Skipping.")
            return None

        # 2. Fetch the target profile configuration from Postgres
        profile = await self.db.get_profile()
        if not profile:
            logger.warning("No target profile configured in database. Skipping scoring.")
            return None

        profile_text = profile.get("profile_text", "")
        keywords = profile.get("keywords", [])
        excluded = profile.get("excluded", [])
        min_score = profile.get("min_score", 0.65)

        # Pre-embed profile text using Gemini Embedding
        # In a real environment, we'd cache this in memory or in DB to save tokens.
        # Let's fetch the embedding for target profile text:
        profile_embedding = await self.embedder.get_embedding(profile_text)

        # 3. Parse posted_at date
        posted_at_str = job_data.get("posted_at")
        posted_at = None
        if posted_at_str:
            try:
                posted_at = datetime.fromisoformat(posted_at_str)
            except ValueError:
                pass

        # 4. Calculate Scores
        score_details = await self.scorer.score_job(
            description=job_data.get("description", ""),
            posted_at=posted_at,
            profile_text=profile_text,
            profile_embedding=profile_embedding,
            keywords=keywords,
            excluded=excluded
        )

        # 5. Insert job details into Neon database
        job_id = await self.db.insert_job(job_data)
        
        # 6. Apply matching scores back to database row
        await self.db.update_job_scores(job_id, score_details)

        # 7. Check alert criteria
        composite_score = score_details.get("composite", 0.0)
        email_sent = False
        
        if composite_score >= min_score:
            # Send Resend email notification
            email_sent = await self.alerter.send_job_alert(client, job_data, score_details)
            
            # Update alerted flag in DB
            if email_sent:
                async with self.db.pool.acquire() as conn:
                    await conn.execute("UPDATE jobs SET alerted = TRUE WHERE id = $1", job_id)

        # 8. Mark as seen in Upstash Redis Set
        await self.queue.mark_seen(client, content_hash)

        return {
            "job_id": job_id,
            "title": job_data.get("title"),
            "company": job_data.get("company"),
            "score": composite_score,
            "alerted": email_sent
        }

    async def consume_all(self, client: httpx.AsyncClient) -> int:
        """Process all currently queued jobs in sequence."""
        processed_count = 0
        while True:
            try:
                result = await self.process_next_job(client)
                if not result:
                    break
                processed_count += 1
                logger.info(f"Processed job: {result['title']} at {result['company']} - Score: {result['score']}")
            except Exception as e:
                logger.error(f"Error processing job from queue: {e}", exc_info=True)
                break
        return processed_count
