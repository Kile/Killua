"""Top.gg v1 project API helpers (metrics + announcements)."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

TOPGG_METRICS_URL = "https://top.gg/api/v1/projects/@me/metrics"
TOPGG_ANNOUNCEMENTS_URL = "https://top.gg/api/v1/projects/@me/announcements"


def _normalize_token(raw: str) -> str:
    token = raw.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        token = token[1:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _token() -> Optional[str]:
    value = os.getenv("TOPGG_TOKEN")
    if not value:
        return None
    token = _normalize_token(value)
    return token or None


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _log_auth_failure(method: str, url: str, status: int, body: str) -> None:
    token = _token()
    token_hint = f"length={len(token)}" if token else "unset"
    logger.error(
        "Top.gg %s %s failed (%s): %s (%s)",
        method,
        url,
        status,
        body or "(empty body)",
        token_hint,
    )


async def _request(session, method: str, url: str, *, json: Optional[dict] = None) -> bool:
    token = _token()
    if not token:
        logger.warning("TOPGG_TOKEN is not set; skipping Top.gg %s %s", method, url)
        return False

    try:
        async with session.request(
            method, url, headers=_auth_headers(token), json=json
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                _log_auth_failure(method, url, resp.status, body)
                return False
            return True
    except Exception as exc:
        logger.error("Top.gg %s %s error: %s", method, url, exc)
        return False


async def post_metrics(
    session,
    *,
    server_count: int,
    shard_count: Optional[int] = None,
) -> bool:
    """Push guild/shard counts to Top.gg (v1 projects metrics)."""
    payload: dict[str, int] = {"server_count": server_count}
    if shard_count is not None:
        payload["shard_count"] = shard_count
    logger.info(
        "Posting Top.gg metrics: server_count=%s shard_count=%s",
        server_count,
        shard_count,
    )
    return await _request(session, "PATCH", TOPGG_METRICS_URL, json=payload)


async def post_announcement(session, *, title: str, content: str) -> bool:
    """Create a Top.gg project announcement."""
    if len(title) < 3 or len(title) > 100:
        logger.warning(
            "Top.gg announcement title length %d is outside 3–100; skipping",
            len(title),
        )
        return False
    if len(content) < 10 or len(content) > 2000:
        logger.warning(
            "Top.gg announcement content length %d is outside 10–2000; skipping",
            len(content),
        )
        return False
    return await _request(
        session,
        "POST",
        TOPGG_ANNOUNCEMENTS_URL,
        json={"title": title, "content": content},
    )
