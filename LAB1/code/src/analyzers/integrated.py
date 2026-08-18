"""Integracao das validacoes e analises de RQ01 a RQ07."""

from analyzers.rq01_rq02_consistency import (
    analyze_consistency as analyze_rq01_rq02,
)
from analyzers.rq03_rq04_metrics import analyze_repositories as analyze_rq03_rq04
from analyzers.rq05_rq07_consistency import (
    analyze_consistency as analyze_rq05_rq07,
)
from validators import rq01_rq02, rq03_rq04, rq05_rq06, rq07


def run_integrated_analysis(
    repositories: list[dict], expected_count: int = 1000
) -> dict:
    """Valida a base completa e integra os resultados de todas as RQs."""
    rq01_rq02_validation = rq01_rq02.validate_dataset(
        repositories, expected_count=expected_count
    )
    rq01_rq02_analysis = analyze_rq01_rq02(
        repositories, rq01_rq02_validation
    )

    rq03_rq04_validation = rq03_rq04.validate_dataset(
        repositories, expected_count=expected_count
    )
    if rq03_rq04_validation["invalid"]:
        first = rq03_rq04_validation["invalid"][0]
        raise ValueError(f"{first['name']}: {first['reason']}")
    rq03_rq04_analysis = analyze_rq03_rq04(
        repositories, rq03_rq04_validation
    )

    rq05_rq06_validation = rq05_rq06.validate_dataset(
        repositories, expected_count=expected_count
    )
    rq07_groups = rq07.validate_dataset(
        repositories, expected_count=expected_count
    )
    rq05_rq07_analysis = analyze_rq05_rq07(
        repositories, rq05_rq06_validation, rq07_groups
    )

    result = {
        "total_repositories": len(repositories),
        "rq01_rq02": {
            "validation": rq01_rq02_validation,
            "analysis": rq01_rq02_analysis,
        },
        "rq03_rq04": {
            "validation": rq03_rq04_validation,
            "analysis": rq03_rq04_analysis,
        },
        "rq05_rq06_rq07": {
            "validation": rq05_rq06_validation,
            "groups": rq07_groups,
            "analysis": rq05_rq07_analysis,
        },
    }

    print(
        "Analise integrada RQ01-RQ07 concluida para "
        f"{result['total_repositories']} repositorios."
    )
    return result
