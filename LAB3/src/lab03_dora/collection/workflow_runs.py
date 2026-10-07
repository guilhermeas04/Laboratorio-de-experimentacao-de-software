"""Coleta mensal de workflow runs do GitHub Actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from lab03_dora.api.github import GitHubClient

VALID_CONCLUSIONS = frozenset({"success", "failure", "timed_out", "startup_failure"})
DEFAULT_PER_PAGE = 100


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("datas da janela devem conter fuso horário")
    return parsed.astimezone(UTC)


def month_windows(start: datetime | str, end: datetime | str) -> list[tuple[datetime, datetime]]:
    """Divide [start, end) em janelas mensais para contornar o limite da API."""
    first = _parse_datetime(start)
    finish = _parse_datetime(end)
    if first >= finish:
        raise ValueError("início da janela deve ser anterior ao fim")

    windows = []
    cursor = first
    while cursor < finish:
        if cursor.month == 12:
            next_month = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month = datetime(cursor.year, cursor.month + 1, 1, tzinfo=UTC)
        window_end = min(next_month, finish)
        windows.append((cursor, window_end))
        cursor = window_end
    return windows


def classify_conclusion(conclusion: str | None) -> str | None:
    """Retorna a conclusão utilizável ou None para runs não elegíveis."""
    normalized = conclusion.lower().strip() if conclusion else None
    return normalized if normalized in VALID_CONCLUSIONS else None


def normalize_workflow_run(
    raw: dict,
    *,
    repository: str,
    observation_month: str,
    default_branch: str | None = None,
) -> dict | None:
    if raw.get("event") != "push":
        return None
    if default_branch is not None and raw.get("head_branch") != default_branch:
        return None
    conclusion = classify_conclusion(raw.get("conclusion"))
    if conclusion is None or raw.get("status") != "completed":
        return None
    return {
        "id": raw["id"],
        "repository": repository,
        "name": raw.get("name", ""),
        "event": raw.get("event", ""),
        "head_branch": raw.get("head_branch", ""),
        "status": "completed",
        "conclusion": conclusion,
        "run_started_at": raw.get("run_started_at"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "url": raw.get("html_url", ""),
        "observation_month": observation_month,
    }


class WorkflowRunClient(GitHubClient):
    """Cliente mínimo da API REST, mantendo autenticação fora do coletor."""

    def __init__(
        self,
        token: str,
        *,
        api_url: str = "https://api.github.com",
        cache_dir: Path | None = None,
    ) -> None:
        super().__init__(token=token, api_root=api_url, cache_dir=cache_dir)

    def list_runs(self, repository: str, params: dict[str, str | int]) -> dict:
        response = self.get(f"/repos/{repository}/actions/runs", params)
        return response.payload if isinstance(response.payload, dict) else {}


@dataclass(frozen=True)
class CollectionResult:
    runs: list[dict]
    windows_at_limit: list[str]

    @property
    def total_count(self) -> int:
        return len(self.runs)


def collect_workflow_runs_for_repositories(
    repositories: list[tuple[str, str]],
    start: datetime | str,
    end: datetime | str,
    client: WorkflowRunClient,
    *,
    cache_dir: Path | None = None,
) -> dict[str, CollectionResult]:
    """Executa a coleta para a amostra S01 inteira, sem interromper por repo."""
    results: dict[str, CollectionResult] = {}
    for repository, default_branch in repositories:
        try:
            results[repository] = collect_workflow_runs(
                repository,
                default_branch,
                start,
                end,
                client,
                cache_dir=cache_dir,
            )
        except Exception as error:
            results[repository] = CollectionResult(
                runs=[],
                windows_at_limit=[f"error:{type(error).__name__}"],
            )
    return results


def _default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "raw" / "workflow_runs"


def collect_workflow_runs(
    repository: str,
    default_branch: str,
    start: datetime | str,
    end: datetime | str,
    client: WorkflowRunClient,
    *,
    cache_dir: Path | None = None,
    per_page: int = DEFAULT_PER_PAGE,
) -> CollectionResult:
    """Coleta runs push do branch padrão, particionando e cacheando cada mês."""
    if not 1 <= per_page <= 100:
        raise ValueError("per_page deve estar entre 1 e 100")
    cache_root = cache_dir or _default_cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    collected: list[dict] = []
    windows_at_limit: list[str] = []

    for window_start, window_end in month_windows(start, end):
        month = window_start.strftime("%Y-%m")
        page = 1
        total_count = 0
        while True:
            cache_path = cache_root / f"{repository.replace('/', '__')}_{month}_p{page}.json"
            if cache_path.exists():
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
            else:
                payload = client.list_runs(
                    repository,
                    {
                        "event": "push",
                        "branch": default_branch,
                    "created": f"{window_start.isoformat()}..{window_end.isoformat()}",
                        "per_page": per_page,
                        "page": page,
                    },
                )
                cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            total_count = int(payload.get("total_count", 0))
            if total_count >= 1000 and month not in windows_at_limit:
                windows_at_limit.append(month)
            for raw_run in payload.get("workflow_runs", []):
                normalized = normalize_workflow_run(
                    raw_run,
                    repository=repository,
                    observation_month=month,
                    default_branch=default_branch,
                )
                if normalized is not None:
                    collected.append(normalized)

            runs_in_page = payload.get("workflow_runs", [])
            if (
                page * per_page >= min(total_count, 1000)
                or not runs_in_page
                or len(runs_in_page) < per_page
            ):
                break
            page += 1

    return CollectionResult(runs=collected, windows_at_limit=windows_at_limit)
