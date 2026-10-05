"""Minimal GitHub REST client for LAB3.

The assignment forbids ready-made GitHub API libraries, so this module uses
only the Python standard library. It centralizes authentication, pagination and
basic error handling for the collection modules.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 30


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API cannot be queried successfully."""


@dataclass(frozen=True)
class GitHubResponse:
    """Decoded GitHub response with selected headers."""

    payload: Any
    headers: dict[str, str]


class GitHubClient:
    """Small REST client with token auth, pagination and rate-limit awareness."""

    def __init__(
        self,
        *,
        token: str | None = None,
        api_root: str = API_ROOT,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 3,
    ) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.api_root = api_root.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @classmethod
    def from_environment(cls) -> "GitHubClient":
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise GitHubApiError(
                "GITHUB_TOKEN nao configurado. Defina a variavel de ambiente antes da coleta."
            )
        return cls(token=token)

    def get(self, path: str, params: dict[str, Any] | None = None) -> GitHubResponse:
        """Run one GET request and return the decoded JSON payload."""

        url = self._build_url(path, params)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._request_json(url)
            except HTTPError as error:
                if error.code == 403 and self._is_rate_limited(error.headers):
                    self._wait_for_rate_limit(error.headers)
                    last_error = error
                    continue
                if 500 <= error.code < 600 and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    last_error = error
                    continue
                raise GitHubApiError(f"GitHub API retornou HTTP {error.code} para {url}") from error
            except URLError as error:
                last_error = error
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise GitHubApiError(f"Falha de rede ao consultar {url}: {error}") from error
        raise GitHubApiError(f"Falha ao consultar {url}: {last_error}")

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterable[Any]:
        """Yield every item from a paginated endpoint that returns a list."""

        next_url = self._build_url(path, params)
        while next_url:
            response = self._request_json(next_url)
            if not isinstance(response.payload, list):
                raise GitHubApiError(f"Endpoint paginado nao retornou lista: {next_url}")
            yield from response.payload
            next_url = _next_link(response.headers.get("link", ""))

    def search_repositories(
        self,
        *,
        stars: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 100,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Search repositories by star range.

        GitHub caps Search API access to the first 1,000 results. The caller is
        expected to slice by star ranges or another dimension when it needs more
        candidates.
        """

        repositories: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            response = self.get(
                "/search/repositories",
                {
                    "q": f"stars:{stars} archived:false",
                    "sort": sort,
                    "order": order,
                    "per_page": per_page,
                    "page": page,
                },
            )
            payload = response.payload
            items = payload.get("items", []) if isinstance(payload, dict) else []
            repositories.extend(items)
            if len(items) < per_page:
                break
        return repositories

    def repository_workflows(self, full_name: str) -> dict[str, Any]:
        return self.get(f"/repos/{full_name}/actions/workflows", {"per_page": 1}).payload

    def _build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        if path.startswith("https://"):
            url = path
        else:
            url = f"{self.api_root}/{path.lstrip('/')}"
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        return url

    def _request_json(self, url: str) -> GitHubResponse:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lab03-dora-pipeline",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return GitHubResponse(payload=payload, headers={key.lower(): value for key, value in response.headers.items()})

    @staticmethod
    def _is_rate_limited(headers: Any) -> bool:
        return str(headers.get("X-RateLimit-Remaining", "")).strip() == "0"

    @staticmethod
    def _wait_for_rate_limit(headers: Any) -> None:
        reset = headers.get("X-RateLimit-Reset")
        if reset and str(reset).isdigit():
            wait_seconds = max(0, int(reset) - int(time.time())) + 1
            time.sleep(wait_seconds)


def _next_link(link_header: str) -> str | None:
    """Extract the URL for rel=next from a GitHub Link header."""

    for chunk in link_header.split(","):
        url_part, _, rel_part = chunk.strip().partition(";")
        if 'rel="next"' in rel_part and url_part.startswith("<") and url_part.endswith(">"):
            return url_part[1:-1]
    return None


def parse_github_datetime(value: str | None) -> str:
    """Normalize a GitHub timestamp to ISO-8601 seconds, preserving UTC offset."""

    if not value:
        return ""
    return parsedate_to_datetime(value.replace("Z", "+0000")).isoformat()
