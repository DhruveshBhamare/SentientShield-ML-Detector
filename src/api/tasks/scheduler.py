import asyncio
import logging
import json
from typing import Optional, Callable
from ...configs.config import RETRAIN_INTERVAL_SECONDS

logger = logging.getLogger(__name__)

async def daily_retrain_loop(interval: int = None):
    # Pre-import to avoid deadlock in background threads
    try:
        from scripts.retrain import daily_retrain
    except ImportError:
        logger.error("[Scheduler] Failed to import daily_retrain")
        return

    if interval is None:
        interval = RETRAIN_INTERVAL_SECONDS

    # Initial delay to allow the app to fully start and pass health checks
    initial_delay = 60 # 60 seconds
    logger.info(f"[Scheduler] Waiting {initial_delay}s before first retrain cycle...")
    await asyncio.sleep(initial_delay)

    while True:
        try:
            logger.info("[Scheduler] Starting background retrain cycle...")
            # Run blocking daily_retrain in a separate thread to avoid freezing the event loop
            result = await asyncio.to_thread(daily_retrain)
            logger.info(f"[Scheduler] Retrain completed: {json.dumps(result)}")
        except Exception as e:
            logger.error(f"[Scheduler] Retrain failed: {e}")
        await asyncio.sleep(interval)

def start_daily_retrain_task(interval: Optional[int] = None, logger_fn: Optional[Callable[[str], None]] = None) -> asyncio.Task:
    """Start the daily retrain loop as an asyncio Task."""
    return asyncio.create_task(daily_retrain_loop(interval=interval))
