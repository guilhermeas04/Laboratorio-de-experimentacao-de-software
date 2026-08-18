"""Ponto de entrada da coleta da Lab01S02."""

from pathlib import Path

from collectors.repositories import collect_top_repositories
from config import load_settings
from exporters.csv_exporter import export_repositories_csv, validate_exported_csv
from github_client import GitHubGraphQLClient
from validators.integrated import validate_sample


OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "processed" / "top_repositories.csv"
)


def main():
    """Coleta 1000 repositorios com paginacao e exporta o CSV consolidado."""
    settings = load_settings()
    client = GitHubGraphQLClient(settings.github_token, settings.github_graphql_url)

    repositories = collect_top_repositories(client, settings.top_repositories_limit)
    validate_sample(repositories, sample_size=10)
    export_repositories_csv(repositories, str(OUTPUT_PATH))
    validate_exported_csv(str(OUTPUT_PATH), expected_count=settings.top_repositories_limit)

    print(f"Consulta concluida: {len(repositories)} repositorios unicos coletados.")
    print(f"Arquivo gerado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
