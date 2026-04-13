import asyncio
import os
import logging
import time
import random
from collections import deque
from typing import Optional, Callable, Deque

from ...services.threat_ingestor import fetch_threat_messages, ingest_message

logger = logging.getLogger(__name__)


async def threat_ingest_loop(interval: Optional[int] = None, logger_fn: Optional[Callable[[str], None]] = None):
    if interval is None:
        interval = int(os.getenv("THREAT_INGEST_INTERVAL_SECONDS", "30"))
    if logger_fn is None:
        logger_fn = lambda s: logger.info(s)

    min_delay = float(os.getenv("THREAT_INGEST_MIN_DELAY_SECONDS", "12"))
    max_delay = float(os.getenv("THREAT_INGEST_MAX_DELAY_SECONDS", "15"))
    max_queue = int(os.getenv("THREAT_INGEST_MAX_QUEUE", "500"))
    fetch_limit = int(os.getenv("THREAT_INGEST_FETCH_LIMIT", "50"))

    q: Deque[str] = deque()
    next_fetch_at = 0.0

    # Initial delay to allow the app to fully start and pass health checks
    initial_delay = 45 # 45 seconds
    logger_fn(f"[ThreatIngest] Waiting {initial_delay}s before starting loop...")
    await asyncio.sleep(initial_delay)

    while True:
        try:
            now = time.monotonic()
            if now >= next_fetch_at:
                fetched = await asyncio.to_thread(fetch_threat_messages, fetch_limit)
                msgs = fetched.get("messages") or []
                for m in msgs:
                    if len(q) >= max_queue:
                        break
                    q.append(m)
                logger_fn(f"[ThreatIngest] fetched={len(msgs)} queued={len(q)} sources={fetched.get('sources') or []}")
                next_fetch_at = now + max(1, interval)

            if q:
                msg = q.popleft()
                result = await asyncio.to_thread(ingest_message, msg)
                logger_fn(f"[ThreatIngest] ingested={result}")
                await asyncio.sleep(random.uniform(min_delay, max_delay))
            else:
                await asyncio.sleep(1)
        except Exception as e:
            logger_fn(f"[ThreatIngest] failed: {e}")


def start_threat_ingest_task(interval: Optional[int] = None, logger_fn: Optional[Callable[[str], None]] = None) -> asyncio.Task:
    return asyncio.create_task(threat_ingest_loop(interval=interval, logger_fn=logger_fn))
