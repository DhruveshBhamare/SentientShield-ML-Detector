import asyncio
import json
from typing import Optional, Callable

from ...configs.config import RETRAIN_INTERVAL_SECONDS


async def daily_retrain_loop(interval: Optional[int] = None, logger: Optional[Callable[[str], None]] = None):
    """Background loop that triggers daily retraining using scripts.retrain.daily_retrain."""
    # Assuming scripts is available in PYTHONPATH
    try:
        from scripts.retrain import daily_retrain
    except ImportError:
        # Fallback for different deployment structures
        import sys
        import os
        sys.path.append(os.path.join(os.getcwd(), "scripts"))
        from retrain import daily_retrain

    if interval is None:
        interval = RETRAIN_INTERVAL_SECONDS
    if logger is None:
        logger = print

    # Initial delay to allow the app to fully start and pass health checks
    initial_delay = 60 # 60 seconds
    logger(f"[Scheduler] Waiting {initial_delay}s before first retrain cycle...")
    await asyncio.sleep(initial_delay)

    while True:
        try:
            logger("[Scheduler] Starting background retrain cycle...")
            # Run blocking daily_retrain in a separate thread to avoid freezing the event loop
            result = await asyncio.to_thread(daily_retrain)
            logger(f"[Scheduler] Retrain completed: {json.dumps(result)}")
        except Exception as e:
            logger(f"[Scheduler] Retrain failed: {e}")
        await asyncio.sleep(interval)


def start_daily_retrain_task(interval: Optional[int] = None, logger: Optional[Callable[[str], None]] = None) -> asyncio.Task:
    """Start the daily retrain loop as an asyncio Task."""
    return asyncio.create_task(daily_retrain_loop(interval=interval, logger=logger))