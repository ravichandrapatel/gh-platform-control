# FILE_NAME: github_http.py
# DESCRIPTION: Shared GitHub REST helper with 429 / secondary-rate-limit retry.
# VERSION: 0.1.0
# AUTHORS: gh-platform
from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from gh_platform_control.util import fail

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_TIMEOUT_S = 45.0
_USER_AGENT = "gh-platform-control"


def _retry_after_seconds(err: urllib.error.HTTPError, attempt: int) -> float:
    """INTENT: Compute sleep before retry. INPUT: HTTPError + attempt (0-based).
    OUTPUT: Seconds to sleep. ROLE: Pure helper. SIDE_EFFECTS: None.
    """
    raw = err.headers.get("Retry-After") if err.headers else None
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    # Secondary rate limits often omit Retry-After; exponential + jitter.
    base = min(60.0, (2**attempt) + random.uniform(0.0, 1.0))
    return base


def _is_rate_limited(err: urllib.error.HTTPError, body: str) -> bool:
    """INTENT: Detect primary/secondary GitHub rate limits.
    INPUT: HTTPError + body snippet. OUTPUT: bool.
    """
    if err.code == 429:
        return True
    if err.code != 403:
        return False
    lowered = body.lower()
    return (
        "rate limit" in lowered
        or "secondary rate limit" in lowered
        or "abuse detection" in lowered
    )


def gh_request(
    path: str,
    token: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    user_agent: str = _USER_AGENT,
    not_found: Callable[[], Any] | None = None,
) -> Any:
    """INTENT: Call api.github.com with retries on 429 / secondary 403.
    INPUT: path, token, optional JSON body. OUTPUT: parsed JSON or None.
    ROLE: Shared HTTP. SIDE_EFFECTS: Network; sleeps on rate limit.
    """
    if not path.startswith("/"):
        fail(f"GitHub API path must start with / (got {path!r})")
    url = f"https://api.github.com{path}"
    body_bytes = None if data is None else json.dumps(data).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": user_agent,
    }
    if body_bytes is not None:
        headers["Content-Type"] = "application/json"

    last_detail = ""
    for attempt in range(max_attempts):
        req = urllib.request.Request(
            url, data=body_bytes, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            last_detail = detail[:500]
            if e.code == 404 and not_found is not None:
                return not_found()
            if _is_rate_limited(e, detail) and attempt + 1 < max_attempts:
                time.sleep(_retry_after_seconds(e, attempt))
                continue
            if e.code == 404:
                return None
            fail(f"GitHub API {method} {path} failed ({e.code}): {last_detail}")
    fail(
        f"GitHub API {method} {path} failed after {max_attempts} rate-limit retries: "
        f"{last_detail}"
    )
