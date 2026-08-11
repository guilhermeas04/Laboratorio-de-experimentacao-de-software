"""Ponto de entrada da coleta da Lab01S01."""

from pathlib import Path

from collectors.repositories import collect_top_repositories
from config import load_settings
from exporters.csv_exporter import export_repositories_csv
from github_client import GitHubGraphQLClient
from validators.rq01_rq02 import validate_sample


OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "rq01_rq02.csv"


def main():
    """Executa a coleta e validacao das metricas de RQ01 e RQ02."""
    settings = load_settings()
    client = GitHubGraphQLClient(settings.github_token, settings.github_graphql_url)

    repositories = collect_top_repositories(client, settings.top_repositories_limit)
    validate_sample(repositories)
    export_repositories_csv(repositories, str(OUTPUT_PATH))

    print(f"Arquivo gerado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
