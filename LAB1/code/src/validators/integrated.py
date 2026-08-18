"""Validacao rapida da consulta GraphQL unica."""

from validators import rq01_rq02, rq03_rq04, rq05_rq06, rq07


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida uma amostra usando as checagens de RQ01 a RQ07."""
    rq01_rq02.validate_sample(repositories, sample_size=sample_size)
    rq03_rq04.validate_sample(repositories, sample_size=sample_size)
    rq05_rq06.validate_sample(repositories, sample_size=sample_size)
    rq07.validate_sample(repositories, sample_size=sample_size)
    print(f"Validacao da consulta unica concluida para ate {sample_size} repositorios.")


def validate_rq05_rq07_dataset(
    repositories: list[dict], expected_count: int = 1000
) -> tuple[dict, dict[str, list[dict]]]:
    """Valida todos os registros que sustentam RQ05, RQ06 e RQ07."""
    rq05_rq06_summary = rq05_rq06.validate_dataset(
        repositories, expected_count=expected_count
    )
    rq07_groups = rq07.validate_dataset(repositories, expected_count=expected_count)
    print(
        "Validacao completa RQ05/RQ06/RQ07 concluida para "
        f"{expected_count} repositorios."
    )
    return rq05_rq06_summary, rq07_groups


def validate_rq01_rq02_dataset(
    repositories: list[dict], expected_count: int = 1000
) -> dict:
    """Valida todos os registros que sustentam RQ01 e RQ02."""
    summary = rq01_rq02.validate_dataset(
        repositories, expected_count=expected_count
    )
    print(
        "Validacao completa RQ01/RQ02 concluida para "
        f"{expected_count} repositorios."
    )
    return summary
