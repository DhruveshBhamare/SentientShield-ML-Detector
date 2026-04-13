import os
import time
import logging
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from .log_service import (
    DistilBERTLogClassifier,
    MiniLMEmbedder,
    InMemoryVectorIndex,
    FaissVectorIndex,
    ZeroShotThreatClassifier,
    MITREAttckMapper,
    SOCReportGenerator,
    TrendStore,
    PGTrendStore,
    RiskScoringEngine,
    PipelineEngine,
    NVIDIAQwenChatbot,
)

logger = logging.getLogger(__name__)

_ctx = None
_seen = set()


def _enabled() -> bool:
    v = os.getenv("THREAT_INGEST_ENABLED", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("ABUSEIPDB_API_KEY") or os.getenv("OTX_API_KEY") or os.getenv("THREAT_INGEST_PUBLIC_FALLBACK", "true").strip().lower() in ("1", "true", "yes", "on"))


def _get_ctx():
    global _ctx
    if _ctx is not None:
        return _ctx

    clf = DistilBERTLogClassifier()
    embedder = MiniLMEmbedder()
    bot = NVIDIAQwenChatbot()
    if embedder.available:
        try:
            index = FaissVectorIndex(embedder)
            if index.index is None:
                index = InMemoryVectorIndex(embedder)
        except Exception:
            index = InMemoryVectorIndex(embedder)
    else:
        index = InMemoryVectorIndex(embedder)

    zs = ZeroShotThreatClassifier()
    attck = MITREAttckMapper(zs, embedder)
    soc = SOCReportGenerator(clf, attck, llm_client=bot)
    trend = PGTrendStore(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else TrendStore(attck.db_path)
    risk = RiskScoringEngine(clf, trend, embedder)
    pipe = PipelineEngine(clf, embedder, index, attck, risk, soc)

    _ctx = {"attck": attck, "trend": trend, "pipe": pipe}
    return _ctx


def _mark_seen(key: str, ttl_seconds: int = 6 * 60 * 60) -> bool:
    global _seen
    now = int(time.time())
    k = f"{key}|{now // ttl_seconds}"
    if k in _seen:
        return False
    if len(_seen) > 100000:
        _seen = set(list(_seen)[-50000:])
    _seen.add(k)
    return True


def _build_message(source: str, ip: str, category: str, description: str, ts: str) -> str:
    ip = (ip or "").strip()
    category = (category or "unknown").strip()
    description = (description or "").strip()
    ts = (ts or "").strip()
    return f"Malicious IP detected {ip} category {category} source {source} description {description} timestamp {ts}"


def _fetch_abuseipdb() -> Iterable[Tuple[str, str, str, str]]:
    api_key = os.getenv("ABUSEIPDB_API_KEY")
    if not api_key:
        return []
    url = "https://api.abuseipdb.com/api/v2/blacklist"
    params = {
        "confidenceMinimum": os.getenv("ABUSEIPDB_CONFIDENCE_MIN", "75"),
        "limit": os.getenv("ABUSEIPDB_LIMIT", "50"),
        "plaintext": "false",
    }
    headers = {"Key": api_key, "Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json() or {}
    items = (data.get("data") or {}).get("data") or data.get("data") or []
    out = []
    for it in items:
        ip = it.get("ipAddress") or it.get("ip") or ""
        score = it.get("abuseConfidenceScore")
        category = f"abuse_score_{score}" if score is not None else "abuseipdb"
        desc = it.get("domain") or it.get("isp") or it.get("usageType") or "abuseipdb blacklist"
        ts = it.get("lastReportedAt") or it.get("reportedAt") or ""
        if ip:
            out.append((ip, category, desc, ts))
    return out


def _fetch_otx() -> Iterable[Tuple[str, str, str, str]]:
    api_key = os.getenv("OTX_API_KEY")
    if not api_key:
        return []
    url = "https://otx.alienvault.com/api/v1/indicators/export"
    params = {
        "type": os.getenv("OTX_TYPE", "IPv4"),
        "format": os.getenv("OTX_FORMAT", "json"),
        "limit": os.getenv("OTX_LIMIT", "50"),
    }
    headers = {"X-OTX-API-KEY": api_key}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    out = []
    if "json" in ctype:
        payload = r.json()
        items = payload.get("results") or payload.get("data") or payload.get("indicators") or payload or []
        if isinstance(items, dict):
            items = items.get("results") or items.get("data") or []
        for it in items:
            ip = it.get("indicator") or it.get("ip") or it.get("value") or ""
            category = it.get("type") or it.get("indicator_type") or "otx"
            desc = it.get("description") or it.get("title") or "otx indicator"
            ts = it.get("created") or it.get("timestamp") or it.get("date") or ""
            if ip:
                out.append((ip, category, desc, ts))
    else:
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append((line, "otx", "otx indicator", ""))
    return out


def _fetch_public_fallback() -> Iterable[Tuple[str, str, str, str]]:
    allow = os.getenv("THREAT_INGEST_PUBLIC_FALLBACK", "true").strip().lower() in ("1", "true", "yes", "on")
    if not allow:
        return []
    url = os.getenv("THREAT_INGEST_FALLBACK_URL", "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    out = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        ip = parts[0] if parts else ""
        if not ip or ip.startswith("#"):
            continue
        category = "public_feed"
        desc = "ipsum"
        ts = ""
        out.append((ip, category, desc, ts))
        if len(out) >= 50:
            break
    return out


def ingest_once(max_events: int = 50) -> Dict[str, Any]:
    if not _enabled():
        return {"enabled": False, "ingested": 0, "sources": []}

    fetched = fetch_threat_messages(limit=max_events)
    messages = fetched.get("messages") or []
    used_sources = fetched.get("sources") or []
    ingested = 0
    for msg in messages[:max_events]:
        ingest_message(msg)
        ingested += 1
    return {"enabled": True, "ingested": ingested, "sources": used_sources}


def fetch_threat_messages(limit: int = 50) -> Dict[str, Any]:
    if not _enabled():
        return {"enabled": False, "messages": [], "sources": []}

    limit = max(1, min(int(limit or 50), 500))
    sources: List[Tuple[str, Iterable[Tuple[str, str, str, str]]]] = []
    try:
        sources.append(("abuseipdb", _fetch_abuseipdb()))
    except Exception as e:
        logger.warning(f"AbuseIPDB fetch failed: {e}")
    try:
        sources.append(("otx", _fetch_otx()))
    except Exception as e:
        logger.warning(f"OTX fetch failed: {e}")
    if not any(items for _, items in sources):
        try:
            sources.append(("public", _fetch_public_fallback()))
        except Exception as e:
            logger.warning(f"Public fallback fetch failed: {e}")

    messages: List[str] = []
    used_sources: List[str] = []
    for source_name, items in sources:
        if not items:
            continue
        used_sources.append(source_name)
        for ip, category, desc, ts in items:
            if len(messages) >= limit:
                break
            key = f"{source_name}:{ip}:{category}"
            if not _mark_seen(key):
                continue
            msg = _build_message(source_name, ip, category, desc, ts)
            messages.append(msg)

    random.shuffle(messages)
    return {"enabled": True, "messages": messages[:limit], "sources": used_sources}


def ingest_message(message: str) -> Dict[str, Any]:
    ctx = _get_ctx()
    pipe: PipelineEngine = ctx["pipe"]
    trend = ctx["trend"]
    attck = ctx["attck"]

    res = pipe.run(message, ingest=True, soc_report=False, title=None)
    sev = (res.get("severity") or {}).get("label") or ""
    thr = (res.get("threat_type") or {}).get("label") or ""
    risk_obj = res.get("risk") or {}
    risk_score = float(risk_obj.get("risk_score") or risk_obj.get("risk_score_base") or 0.0)
    trend.record_event(message, sev, thr, risk_score)
    attck.map(message)
    return {"severity": sev, "threat_type": thr, "risk": risk_score}
