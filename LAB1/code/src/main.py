"""Ponto de entrada da coleta da Lab01S02."""

from pathlib import Path

from analyzers.integrated import run_integrated_analysis
from analyzers.rq01_rq02_consistency import (
    write_report as write_rq01_rq02_report,
    write_validation_report as write_rq01_rq02_validation_report,
)
from analyzers.rq05_rq07_consistency import (
    write_report as write_rq05_rq07_report,
)
from collectors.repositories import collect_top_repositories
from config import load_settings
from exporters.csv_exporter import export_repositories_csv, validate_exported_csv
from github_client import GitHubGraphQLClient
from validators.integrated import validate_sample


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
RQ01_RQ02_VALIDATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "validacao-rq01-rq02.md"
)


def main():
    """Coleta 1000 repositorios com paginacao e exporta o CSV consolidado."""
    settings = load_settings()
    client = GitHubGraphQLClient(settings.github_token, settings.github_graphql_url)

    repositories = collect_top_repositories(client, settings.top_repositories_limit)
    export_repositories_csv(repositories, str(OUTPUT_PATH))
    validate_exported_csv(str(OUTPUT_PATH), expected_count=settings.top_repositories_limit)
    validate_sample(repositories, sample_size=10)
    integrated_analysis = run_integrated_analysis(
        repositories, expected_count=settings.top_repositories_limit
    )
    rq01_rq02_analysis = integrated_analysis["rq01_rq02"]["analysis"]
    write_rq01_rq02_report(rq01_rq02_analysis, RQ01_RQ02_REPORT_PATH)
    write_rq01_rq02_validation_report(
        rq01_rq02_analysis, RQ01_RQ02_VALIDATION_PATH
    )
    consistency = integrated_analysis["rq05_rq06_rq07"]["analysis"]
    write_rq05_rq07_report(consistency, RQ05_RQ07_REPORT_PATH)
    print(f"Consulta concluida: {len(repositories)} repositorios unicos coletados.")
    print(f"Arquivo gerado: {OUTPUT_PATH}")
    print(f"Relatorio RQ01/RQ02 gerado: {RQ01_RQ02_REPORT_PATH}")
    print(f"Validacao RQ01/RQ02 gerada: {RQ01_RQ02_VALIDATION_PATH}")
    print(f"Relatorio de validacao gerado: {RQ05_RQ07_REPORT_PATH}")


if __name__ == "__main__":
    main()
