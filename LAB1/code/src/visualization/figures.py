"""Diretorio e convencao de nomes das figuras das RQ01 a RQ07."""

from __future__ import annotations

from pathlib import Path


FIGURES_DIR = Path(__file__).resolve().parents[3] / "reports" / "figures"

# Convencao: rqXX_<slug>.png
# Exemplos:
#   rq01_idade.png
#   rq02_pull_requests.png
#   rq03_releases.png
#   rq04_atualizacao.png
#   rq05_linguagens.png
#   rq06_issues.png
#   rq07_linguagem_metricas.png
VALID_RQS = tuple(f"rq{index:02d}" for index in range(1, 8))


def figure_path(rq: str, slug: str) -> Path:
    """Retorna o caminho PNG associado a uma RQ.

    Parametros
    ----------
    rq:
        Identificador da questao, ex.: ``rq03`` ou ``RQ03``.
    slug:
        Sufixo descritivo em snake_case, ex.: ``releases``.
    """
    rq_key = rq.strip().lower()
    if rq_key not in VALID_RQS:
        raise ValueError(f"RQ invalida: {rq!r}. Use uma de {VALID_RQS}.")

    clean_slug = slug.strip().lower().replace(" ", "_").replace("-", "_")
    if not clean_slug:
        raise ValueError("slug da figura nao pode ser vazio")

    return FIGURES_DIR / f"{rq_key}_{clean_slug}.png"
