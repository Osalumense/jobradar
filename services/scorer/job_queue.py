import httpx
import json
import os
from typing import Dict, Any

class JobQueue:
    def __init__(self):
        self.url = os.environ.get("UPSTASH_REDIS_REST_URL")
        self.token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        self.queue_key = "jobradar:queue"
        self.seen_key = "jobradar:seen"

        if not self.url or not self.token:
            raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be configured in env")

        # Strip surrounding quotes if present in env
        self.url = self.url.strip('"').strip("'")
        self.token = self.token.strip('"').strip("'")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def is_seen(self, client: httpx.AsyncClient, content_hash: str) -> bool:
        """O(1) look up to check if a job hash has been processed already."""
        endpoint = f"{self.url}/sismember/{self.seen_key}/{content_hash}"
        response = await client.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get("result") == 1

    async def mark_seen(self, client: httpx.AsyncClient, content_hash: str) -> None:
        """Mark a job hash as seen in the Redis Set."""
        endpoint = f"{self.url}/sadd/{self.seen_key}/{content_hash}"
        response = await client.get(endpoint, headers=self.headers)
        response.raise_for_status()

    async def enqueue(self, client: httpx.AsyncClient, job_data: Dict[str, Any]) -> None:
        """Push raw job payload to the Redis queue list."""
        payload = json.dumps(job_data)
        endpoint = f"{self.url}/rpush/{self.queue_key}"
        # Upstash REST API expects POST for RPUSH payload
        response = await client.post(endpoint, headers=self.headers, content=payload)
        response.raise_for_status()

    async def dequeue(self, client: httpx.AsyncClient) -> Dict[str, Any] | None:
        """Pop a job from the queue (Left-pop/LPOP) for processing."""
        endpoint = f"{self.url}/lpop/{self.queue_key}"
        response = await client.get(endpoint, headers=self.headers)
        response.raise_for_status()
        result = response.json().get("result")
        if result:
            return json.loads(result)
        return None
