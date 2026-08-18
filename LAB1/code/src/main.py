"""Ponto de entrada da coleta da Lab01S02."""

from pathlib import Path

from analyzers.rq01_rq02_consistency import (
    analyze_consistency as analyze_rq01_rq02,
    write_report as write_rq01_rq02_report,
)
from analyzers.rq05_rq07_consistency import (
    analyze_consistency as analyze_rq05_rq07,
    write_report as write_rq05_rq07_report,
)
from collectors.repositories import collect_top_repositories
from config import load_settings
from exporters.csv_exporter import export_repositories_csv, validate_exported_csv
from github_client import GitHubGraphQLClient
from validators.integrated import (
    validate_rq01_rq02_dataset,
    validate_rq05_rq07_dataset,
    validate_sample,
)


OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "processed" / "top_repositories.csv"
)
RQ05_RQ07_REPORT_PATH = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "validacao-rq05-rq06-rq07.md"
)
RQ01_RQ02_REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "reports" / "rq01-rq02.md"
)


def main():
    """Coleta 1000 repositorios com paginacao e exporta o CSV consolidado."""
    settings = load_settings()
    client = GitHubGraphQLClient(settings.github_token, settings.github_graphql_url)

    repositories = collect_top_repositories(client, settings.top_repositories_limit)
    export_repositories_csv(repositories, str(OUTPUT_PATH))
    validate_exported_csv(str(OUTPUT_PATH), expected_count=settings.top_repositories_limit)
    validate_sample(repositories, sample_size=10)
    rq01_rq02_validation = validate_rq01_rq02_dataset(
        repositories, expected_count=settings.top_repositories_limit
    )
    rq01_rq02_analysis = analyze_rq01_rq02(
        repositories, rq01_rq02_validation
    )
    write_rq01_rq02_report(rq01_rq02_analysis, RQ01_RQ02_REPORT_PATH)
    rq05_rq06_summary, rq07_groups = validate_rq05_rq07_dataset(
        repositories, expected_count=settings.top_repositories_limit
    )
    consistency = analyze_rq05_rq07(
        repositories, rq05_rq06_summary, rq07_groups
    )
    write_rq05_rq07_report(consistency, RQ05_RQ07_REPORT_PATH)
    print(f"Consulta concluida: {len(repositories)} repositorios unicos coletados.")
    print(f"Arquivo gerado: {OUTPUT_PATH}")
    print(f"Relatorio RQ01/RQ02 gerado: {RQ01_RQ02_REPORT_PATH}")
    print(f"Relatorio de validacao gerado: {RQ05_RQ07_REPORT_PATH}")


if __name__ == "__main__":
    main()
