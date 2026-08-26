"""Ponto de entrada unico para gerar as visualizacoes das RQ01 a RQ07."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzers.rq01_rq02_plots import (
    plot_rq01_age,
    plot_rq02_merged_prs,
    update_report as update_rq01_rq02_report,
)
from analyzers.rq03_rq04_plots import (
    plot_rq03_releases,
    plot_rq04_update_comparison,
    update_report as update_rq03_rq04_report,
)
from analyzers.rq05_rq07_plots import (
    REPORT_PATH as RQ05_RQ07_REPORT_PATH,
    build_report as build_rq05_rq07_report,
    plot_rq05_languages,
    plot_rq06_closed_issues,
    plot_rq07_language_metrics,
)
from validators.rq01_rq02 import validate_dataset as validate_rq01_rq02
from validators.rq03_rq04 import validate_dataset as validate_rq03_rq04
from validators.rq05_rq06 import validate_dataset as validate_rq05_rq06
from validators.rq07 import validate_dataset as validate_rq07
from validators.figures import validate_artifacts, write_validation_report
from visualization.figures import figure_path
from visualization.loader import load_top_repositories
from visualization.style import apply_common_style


def _generate(label: str, generator, *args) -> dict:
    """Executa um gerador e acrescenta contexto a eventuais falhas."""
    try:
        return generator(*args)
    except Exception as error:
        raise RuntimeError(f"falha ao gerar {label}: {error}") from error


def generate_all() -> dict:
    """Valida uma vez a base e gera deterministicamente todas as figuras."""
    try:
        repositories = load_top_repositories()
    except Exception as error:
        raise RuntimeError(f"falha ao carregar o CSV consolidado: {error}") from error

    try:
        validate_rq01_rq02(repositories, expected_count=1000)
        rq03_rq04 = validate_rq03_rq04(repositories, expected_count=1000)
        rq05_rq06 = validate_rq05_rq06(repositories, expected_count=1000)
        validate_rq07(repositories, expected_count=1000)
    except Exception as error:
        raise RuntimeError(f"falha na validacao dos dados: {error}") from error

    if rq03_rq04["missing"] or rq03_rq04["invalid"]:
        raise RuntimeError(
            "falha na validacao dos dados de RQ03/RQ04: "
            f"ausentes={len(rq03_rq04['missing'])}, "
            f"invalidos={len(rq03_rq04['invalid'])}"
        )

    apply_common_style()
    paths = {
        "RQ01": figure_path("rq01", "idade"),
        "RQ02": figure_path("rq02", "pull_requests"),
        "RQ03": figure_path("rq03", "releases"),
        "RQ04": figure_path("rq04", "atualizacao"),
        "RQ05": figure_path("rq05", "linguagens"),
        "RQ06": figure_path("rq06", "issues"),
        "RQ07": figure_path("rq07", "linguagem_metricas"),
    }

    rq01 = _generate(
        "RQ01",
        plot_rq01_age,
        [repository["repository_age_days"] for repository in repositories],
        paths["RQ01"],
    )
    rq02 = _generate("RQ02", plot_rq02_merged_prs, repositories, paths["RQ02"])
    rq03 = _generate(
        "RQ03", plot_rq03_releases, rq03_rq04["releases"], paths["RQ03"]
    )
    rq04 = _generate(
        "RQ04",
        plot_rq04_update_comparison,
        rq03_rq04["days_update"],
        rq03_rq04["days_push"],
        paths["RQ04"],
    )
    rq05 = _generate(
        "RQ05", plot_rq05_languages, rq05_rq06["languages"], paths["RQ05"]
    )
    rq06 = _generate("RQ06", plot_rq06_closed_issues, repositories, paths["RQ06"])
    rq07 = _generate(
        "RQ07", plot_rq07_language_metrics, repositories, paths["RQ07"]
    )

    try:
        update_rq01_rq02_report(rq01, rq02)
        update_rq03_rq04_report(rq03, rq04)
        RQ05_RQ07_REPORT_PATH.write_text(
            build_rq05_rq07_report(rq05, rq06, rq07), encoding="utf-8"
        )
    except Exception as error:
        raise RuntimeError(f"falha ao atualizar os relatorios: {error}") from error

    result = {
        "repositories": len(repositories),
        "paths": paths,
        "metrics": {
            "age_median_days": rq01["median"],
            "merged_prs_median": rq02["median"],
            "merged_prs_outliers": rq02["outlier_count"],
            "releases_median": rq03["median"],
            "updated_median_days": rq04["update_median"],
            "top_language": rq05["top_language"],
            "closed_issues_median_percent": rq06["median"],
            "language_groups": len(rq07["rows"]),
        },
    }
    try:
        validation = validate_artifacts(result["paths"], result["metrics"], result["repositories"])
        write_validation_report(validation, result["metrics"], result["repositories"])
    except Exception as error:
        raise RuntimeError(f"falha na validacao dos artefatos: {error}") from error
    result["validation"] = validation
    return result


def print_summary(result: dict) -> None:
    """Exibe os artefatos e as metricas principais da execucao."""
    metrics = result["metrics"]
    top_language, top_language_count = metrics["top_language"]
    print(f"Visualizacoes geradas com {result['repositories']} repositorios:")
    for rq, path in result["paths"].items():
        print(f"- {rq}: {path}")
    print("Metricas principais:")
    print(f"- RQ01: mediana de idade = {metrics['age_median_days']} dias")
    print(
        "- RQ02: mediana de PRs aceitas = "
        f"{metrics['merged_prs_median']}; outliers IQR = "
        f"{metrics['merged_prs_outliers']}"
    )
    print(f"- RQ03: mediana de releases = {metrics['releases_median']}")
    print(f"- RQ04: mediana desde updatedAt = {metrics['updated_median_days']} dias")
    print(f"- RQ05: linguagem mais frequente = {top_language or 'Sem linguagem'} ({top_language_count})")
    print(
        "- RQ06: mediana de issues fechadas = "
        f"{metrics['closed_issues_median_percent']:.2f}%"
    )
    print(f"- RQ07: grupos de linguagem = {metrics['language_groups']}")


def main() -> None:
    try:
        result = generate_all()
    except Exception as error:
        print(f"ERRO: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print_summary(result)


if __name__ == "__main__":
    main()
