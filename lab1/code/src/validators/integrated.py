"""Validacao rapida da consulta GraphQL unica."""

from validators import rq01_rq02, rq03_rq04, rq05_rq06


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida a amostra usando as checagens ja existentes de RQ01 a RQ06."""
    rq01_rq02.validate_sample(repositories, sample_size=sample_size)
    rq03_rq04.validate_sample(repositories, sample_size=sample_size)
    rq05_rq06.validate_sample(repositories, sample_size=sample_size)
    print(f"Validacao da consulta unica concluida para ate {sample_size} repositorios.")
