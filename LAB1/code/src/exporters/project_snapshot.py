"""Exportacao dos itens atuais de um GitHub Project para CSV."""

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import load_settings
from github_client import GitHubGraphQLClient


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "project_snapshot.graphql"
FIELDNAMES = [
    "snapshot_at",
    "project_number",
    "project_title",
    "item_id",
    "content_type",
    "issue_number",
    "title",
    "url",
    "repository",
    "assignees",
    "status",
]


def default_snapshot_path(sprint: str = "lab01s03") -> Path:
    """Retorna o caminho timestampado do snapshot da sprint informada."""
    normalized_sprint = sprint.strip().lower()
    if not normalized_sprint or not normalized_sprint.replace("-", "").isalnum():
        raise ValueError(f"identificador de sprint invalido: {sprint!r}")
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "snapshots"
        / f"{normalized_sprint}-project-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    )


def _status_from_field_values(field_values: list[dict]) -> str:
    """Retorna o valor do campo single-select chamado Status."""
    for field_value in field_values:
        field = field_value.get("field") or {}
        if field.get("name") == "Status":
            return field_value.get("name") or ""
    return ""


def _normalize_item(item: dict, snapshot_at: str, project_number: int, project_title: str) -> dict:
    content = item.get("content") or {}
    repository = content.get("repository") or {}
    assignees = content.get("assignees") or {}
    return {
        "snapshot_at": snapshot_at,
        "project_number": project_number,
        "project_title": project_title,
        "item_id": item.get("id", ""),
        "content_type": content.get("__typename", ""),
        "issue_number": content.get("number", ""),
        "title": content.get("title", ""),
        "url": content.get("url", ""),
        "repository": repository.get("nameWithOwner", ""),
        "assignees": ";".join(
            node.get("login", "") for node in assignees.get("nodes", []) if node
        ),
        "status": _status_from_field_values(item.get("fieldValues", {}).get("nodes", [])),
    }


def _collect_project_items(
    client: GitHubGraphQLClient, owner: str, project_number: int
) -> tuple[str, list[dict]]:
    query = QUERY_PATH.read_text(encoding="utf-8")
    items: list[dict] = []
    cursor = None

    while True:
        data = client.execute(
            query,
            {"owner": owner, "number": project_number, "after": cursor},
        )
        project = data["user"]["projectV2"]
        connection = project["items"]
        items.extend(node for node in connection["nodes"] if node)
        page_info = connection["pageInfo"]
        if not page_info["hasNextPage"] or not page_info["endCursor"]:
            return project["title"], items
        cursor = page_info["endCursor"]


def export_project_snapshot(
    output_path: str,
    client: GitHubGraphQLClient | None = None,
    owner: str | None = None,
    project_number: int | None = None,
) -> int:
    """Consulta o Project e exporta seus itens; retorna a quantidade de linhas."""
    settings = load_settings()
    owner = owner or settings.github_project_owner
    project_number = project_number or settings.github_project_number
    client = client or GitHubGraphQLClient(
        settings.github_token, settings.github_graphql_url
    )
    project_title, items = _collect_project_items(client, owner, project_number)
    snapshot_at = datetime.now(UTC).isoformat()
    rows = [
        _normalize_item(item, snapshot_at, project_number, project_title)
        for item in items
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sprint",
        default="lab01s03",
        help="identificador usado no nome do arquivo (padrao: lab01s03)",
    )
    parser.add_argument("--output", help="caminho de saida opcional")
    arguments = parser.parse_args()
    output = Path(arguments.output) if arguments.output else default_snapshot_path(arguments.sprint)
    count = export_project_snapshot(str(output))
    print(f"Snapshot exportado: {output} ({count} itens).")
