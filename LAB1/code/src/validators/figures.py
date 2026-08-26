"""Validacao automatica das figuras e das metricas da Sprint 3."""

from __future__ import annotations

import struct
from pathlib import Path


MIN_WIDTH = 800
MIN_HEIGHT = 450
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "validacao-figuras.md"

FIGURE_DEFINITIONS = {
    "RQ01": {
        "title": "RQ01 - Distribuicao da idade dos repositorios",
        "xlabel": "Idade do repositorio (dias)",
        "ylabel": "Quantidade de repositorios",
    },
    "RQ02": {
        "title": "RQ02 - Distribuicao de Pull Requests aceitas",
        "xlabel": "Pull Requests aceitas (escala symlog)",
        "ylabel": "",
    },
    "RQ03": {
        "title": "RQ03 - Distribuicao do total de releases",
        "xlabel": "Total de releases",
        "ylabel": "Quantidade de repositorios",
    },
    "RQ04": {
        "title": "RQ04 - Comparacao updatedAt vs pushedAt",
        "xlabel": "",
        "ylabel": "Dias",
    },
    "RQ05": {
        "title": "RQ05 - Ranking das linguagens primarias",
        "xlabel": "Quantidade de repositorios",
        "ylabel": "Linguagem",
    },
    "RQ06": {
        "title": "RQ06 - Distribuicao do percentual de issues fechadas",
        "xlabel": "Issues fechadas (%)",
        "ylabel": "Quantidade de repositorios",
    },
    "RQ07": {
        "title": "RQ07 - Medianas de PRs e releases por linguagem",
        "xlabel": "Mediana de PRs aceitas (escala simetrica log)",
        "ylabel": "Mediana de releases (escala simetrica log)",
    },
}

# Valores publicados na validacao da Sprint 2 para a base consolidada.
EXPECTED_METRICS = {
    "repositories": 1000,
    "age_median_days": 2829,
    "merged_prs_median": 768,
    "merged_prs_outliers": 124,
    "releases_median": 39,
    "updated_median_days": 0,
    "top_language": ("Python", 228),
    "closed_issues_median_percent": 87.61,
}


def validate_figure_definition(rq: str, figure) -> None:
    """Falha se o script nao definiu titulo, eixos ou unidades esperados."""
    definition = FIGURE_DEFINITIONS[rq]
    axes = figure.axes
    titles = [axis.get_title() for axis in axes]
    if figure._suptitle is not None:
        titles.append(figure._suptitle.get_text())
    xlabels = [axis.get_xlabel() for axis in axes]
    ylabels = [axis.get_ylabel() for axis in axes]
    if not any(definition["title"] in title for title in titles):
        raise ValueError(f"{rq}: titulo ausente ou incorreto: {titles!r}")
    if definition["xlabel"] and not any(definition["xlabel"] == label for label in xlabels):
        raise ValueError(f"{rq}: eixo X ausente ou sem unidade: {xlabels!r}")
    if definition["ylabel"] and not any(definition["ylabel"] == label for label in ylabels):
        raise ValueError(f"{rq}: eixo Y ausente ou sem unidade: {ylabels!r}")


def _validate_png(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise ValueError(f"figura ausente: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"figura vazia: {path}")
    with path.open("rb") as image_file:
        if image_file.read(8) != PNG_SIGNATURE:
            raise ValueError(f"formato invalido (esperado PNG): {path}")
        header = image_file.read(24)
    if len(header) != 24 or header[4:8] != b"IHDR":
        raise ValueError(f"PNG invalido: {path}")
    width, height = struct.unpack(">II", header[8:16])
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise ValueError(
            f"resolucao insuficiente em {path}: {width}x{height}; "
            f"minimo {MIN_WIDTH}x{MIN_HEIGHT}"
        )
    return width, height


def _metric_matches(name: str, actual, expected) -> bool:
    if isinstance(expected, float):
        return abs(actual - expected) <= 0.01
    return actual == expected


def validate_artifacts(paths: dict[str, Path], metrics: dict, repository_count: int) -> dict:
    """Valida arquivos, definicoes e metricas da execucao completa."""
    if repository_count != EXPECTED_METRICS["repositories"]:
        raise ValueError(
            f"base invalida para as figuras: esperados 1000 repositorios, "
            f"recebidos {repository_count}"
        )

    dimensions = {}
    for rq, path in paths.items():
        if rq not in FIGURE_DEFINITIONS:
            raise ValueError(f"RQ sem definicao de figura: {rq}")
        dimensions[rq] = _validate_png(Path(path))

    mismatches = []
    for name, expected in EXPECTED_METRICS.items():
        if name == "repositories":
            continue
        if not _metric_matches(name, metrics[name], expected):
            mismatches.append(f"{name}: esperado {expected!r}, obtido {metrics[name]!r}")
    if mismatches:
        raise ValueError("metricas divergentes da Sprint 2: " + "; ".join(mismatches))

    return {"figures": len(paths), "dimensions": dimensions, "metrics": len(EXPECTED_METRICS) - 1}


def write_validation_report(validation: dict, metrics: dict, repository_count: int) -> None:
    """Escreve o resumo verificavel dos artefatos gerados."""
    lines = [
        "# Validacao automatica das figuras - Lab01S03",
        "",
        f"- Base analisada: **{repository_count} repositorios**",
        f"- Figuras validas: **{validation['figures']} de 7**",
        f"- Metricas comparadas com a Sprint 2: **{validation['metrics']}**",
        "",
        "## Artefatos",
        "",
    ]
    for rq, (width, height) in validation["dimensions"].items():
        lines.append(f"- **{rq}:** PNG nao vazio, {width}x{height}px, titulo/eixos validados")
    lines.extend(
        [
            "",
            "## Metricas-chave",
            "",
            f"- RQ01: mediana de idade = {metrics['age_median_days']} dias",
            f"- RQ02: mediana de PRs = {metrics['merged_prs_median']}; outliers IQR = {metrics['merged_prs_outliers']}",
            f"- RQ03: mediana de releases = {metrics['releases_median']}",
            f"- RQ04: mediana desde updatedAt = {metrics['updated_median_days']} dias",
            f"- RQ05: linguagem mais frequente = {metrics['top_language'][0]} ({metrics['top_language'][1]})",
            f"- RQ06: mediana de issues fechadas = {metrics['closed_issues_median_percent']:.2f}%",
            "",
            "Resultado: todos os artefatos e valores-chave foram validados com sucesso.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")