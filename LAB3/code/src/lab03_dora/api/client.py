"""Cliente REST com cache local, retry e respeito ao rate limit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


class TemporaryApiError(RuntimeError):
    """Erro temporário após esgotar as tentativas."""


class RateLimitError(RuntimeError):
    """Rate limit sem janela de espera válida."""


def _cache_key(path: str, params: dict[str, str | int]) -> str:
    query = urlencode(sorted(params.items()))
    return hashlib.sha256(f"{path}?{query}".encode("utf-8")).hexdigest()


class GitHubApiClient:
    """Executa GETs JSON sem incluir o token em cache, logs ou exceções."""

    def __init__(
        self,
        token: str,
        *,
        api_url: str = "https://api.github.com",
        cache_dir: Path | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN não configurado")
        if max_retries < 0:
            raise ValueError("max_retries não pode ser negativo")
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.cache_dir = cache_dir
        self.max_retries = max_retries
        self.sleep = sleep
        self.clock = clock
        self.opener = opener
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def get_json(self, path: str, params: dict[str, str | int]) -> dict:
        cache_path = self._cache_path(path, params)
        if cache_path is not None and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        query = urlencode(params)
        request = Request(
            f"{self.api_url}/{path.lstrip('/')}?{query}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lab03-dora",
            },
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with self.opener(request, timeout=60) as response:
                    self._respect_rate_limit(response, attempt)
                    status = int(getattr(response, "status", 200))
                    if status in RETRYABLE_STATUS_CODES:
                        raise TemporaryApiError(f"HTTP {status}")
                    if status >= 400:
                        raise RuntimeError(f"GitHub API HTTP {status}")
                    payload = json.loads(response.read())
            except HTTPError as exc:
                if exc.code not in RETRYABLE_STATUS_CODES:
                    raise RuntimeError(f"GitHub API HTTP {exc.code}") from exc
                last_error = TemporaryApiError(f"HTTP {exc.code}")
                if attempt >= self.max_retries:
                    break
                self.sleep(2**attempt)
                continue
            except TemporaryApiError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self.sleep(2**attempt)
                continue

            if cache_path is not None:
                cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload

        raise TemporaryApiError(f"falha temporária da API após {self.max_retries + 1} tentativas") from last_error

    def _cache_path(self, path: str, params: dict[str, str | int]) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{_cache_key(path, params)}.json"

    def _respect_rate_limit(self, response: object, attempt: int) -> None:
        headers = getattr(response, "headers", {})
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining != "0":
            return
        reset = headers.get("X-RateLimit-Reset")
        if reset is None:
            raise RateLimitError("rate limit atingido sem X-RateLimit-Reset")
        wait_seconds = max(0.0, float(reset) - self.clock())
        if wait_seconds:
            self.sleep(wait_seconds)
