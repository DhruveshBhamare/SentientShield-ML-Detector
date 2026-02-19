import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("uvicorn_watchdog")
    logger.setLevel(logging.INFO)

    # Rotating file handler ~5MB per file, keep 5 backups
    file_handler = RotatingFileHandler(log_dir / "uvicorn.log", maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    # Console handler for immediate visibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    return logger


def run_once(host: str, port: int, workers: int, logger: logging.Logger) -> int:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--workers",
        str(workers),
    ]

    logger.info(f"Starting Uvicorn: host={host} port={port} workers={workers}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(Path(__file__).resolve().parent.parent),
    )

    try:
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, b""):
            if not line:
                break
            logger.info(line.decode(errors="replace").rstrip())
    except KeyboardInterrupt:
        logger.info("Watchdog interrupted; terminating Uvicorn...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        return_code = proc.wait()
        logger.info(f"Uvicorn exited with code {return_code}")
        return return_code


def main():
    parser = argparse.ArgumentParser(description="Uvicorn watchdog with log rotation")
    # Default to loopback-only to avoid exposing ports publicly
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--backoff", type=float, default=2.0, help="seconds to wait before restart on crash")
    parser.add_argument("--max_backoff", type=float, default=30.0, help="max seconds to wait before restart")

    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    log_dir = root / "logs"
    logger = setup_logger(log_dir)

    backoff = args.backoff
    while True:
        code = run_once(args.host, args.port, args.workers, logger)
        # Exit 0 means graceful stop; do not restart
        if code == 0:
            logger.info("Uvicorn stopped gracefully; watchdog will not restart.")
            break
        logger.warning(f"Uvicorn crashed (code {code}); restarting after {backoff} seconds...")
        time.sleep(backoff)
        backoff = min(args.max_backoff, backoff * 2)


if __name__ == "__main__":
    main()