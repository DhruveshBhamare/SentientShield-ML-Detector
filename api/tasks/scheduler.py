import asyncio
import json
from typing import Optional, Callable

from ..core.config import RETRAIN_INTERVAL_SECONDS


async def daily_retrain_loop(interval: Optional[int] = None, logger: Optional[Callable[[str], None]] = None):
    """Background loop that triggers daily retraining using scripts.retrain.daily_retrain."""
    from scripts.retrain import daily_retrain  # Local import to avoid hard dependency at import time

    if interval is None:
        interval = RETRAIN_INTERVAL_SECONDS
    if logger is None:
        logger = print

    while True:
        try:
            result = daily_retrain()
            logger(f"[Scheduler] Retrain completed: {json.dumps(result)}")
        except Exception as e:
            logger(f"[Scheduler] Retrain failed: {e}")
        await asyncio.sleep(interval)


def start_daily_retrain_task(interval: Optional[int] = None, logger: Optional[Callable[[str], None]] = None) -> asyncio.Task:
    """Start the daily retrain loop as an asyncio Task."""
    return asyncio.create_task(daily_retrain_loop(interval=interval, logger=logger))