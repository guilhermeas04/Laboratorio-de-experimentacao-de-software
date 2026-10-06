"""RQ01: deployment frequency em releases por semana."""

from __future__ import annotations

from datetime import date


def observation_weeks(start: date, end: date) -> float:
    """Numero de semanas da janela, contando o dia inicial e o final."""

    if end < start:
        raise ValueError("janela invalida")
    return ((end - start).days + 1) / 7


def deployment_frequency(published_releases: int, start: date, end: date) -> float:
    """Releases publicadas na janela divididas pelas semanas da janela.

    O chamador deve passar so releases da definicao principal: publicadas,
    nao draft e nao pre-release. Zero releases e uma frequencia zero, nao um erro.
    """

    if published_releases < 0:
        raise ValueError("contagem de releases negativa")
    return published_releases / observation_weeks(start, end)
