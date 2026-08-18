"""Analise de consistencia e relatorio das RQ05, RQ06 e RQ07."""

from pathlib import Path
from statistics import mean, median, quantiles

from validators.rq05_rq06 import POPULAR_LANGUAGES_SOURCE


SMALL_GROUP_THRESHOLD = 5
METRICS = (
    "merged_pull_requests",
    "releases_count",
    "days_since_last_update",
)
METRIC_LABELS = {
    "merged_pull_requests": "PRs aceitas",
    "releases_count": "releases",
    "days_since_last_update": "dias desde a atualizacao",
}


def describe(values: list[int | float]) -> dict:
    """Calcula medidas descritivas e limites de outliers pelo metodo IQR."""
    if not values:
        return {
            "count": 0,
            "min": None,
            "q1": None,
            "median": None,
            "mean": None,
            "q3": None,
            "max": None,
            "lower_bound": None,
            "upper_bound": None,
        }

    ordered = sorted(values)
    if len(ordered) >= 2:
        quartiles = quantiles(ordered, n=4, method="inclusive")
        q1, q3 = quartiles[0], quartiles[2]
    else:
        q1 = q3 = ordered[0]
    iqr = q3 - q1
    return {
        "count": len(ordered),
        "min": ordered[0],
        "q1": q1,
        "median": median(ordered),
        "mean": mean(ordered),
        "q3": q3,
        "max": ordered[-1],
        "lower_bound": q1 - 1.5 * iqr,
        "upper_bound": q3 + 1.5 * iqr,
    }


def find_outliers(
    repositories: list[dict], field: str, summary: dict
) -> list[dict]:
    """Lista registros fora dos limites IQR calculados para uma metrica."""
    if summary["count"] == 0:
        return []
    return [
        {
            "name_with_owner": repository["name_with_owner"],
            "value": repository[field],
        }
        for repository in repositories
        if repository[field] < summary["lower_bound"]
        or repository[field] > summary["upper_bound"]
    ]


def analyze_consistency(
    repositories: list[dict], rq05_rq06_summary: dict, rq07_groups: dict
) -> dict:
    """Calcula distribuicoes, ausentes, grupos pequenos e outliers."""
    ratio_repositories = [
        repository
        for repository in repositories
        if repository["closed_issues_ratio"] is not None
    ]
    ratio_summary = describe(
        [repository["closed_issues_ratio"] for repository in ratio_repositories]
    )
    ratio_outliers = find_outliers(
        ratio_repositories, "closed_issues_ratio", ratio_summary
    )

    metric_summaries = {
        metric: describe([repository[metric] for repository in repositories])
        for metric in METRICS
    }
    metric_outliers = {
        metric: find_outliers(repositories, metric, metric_summaries[metric])
        for metric in METRICS
    }

    language_metrics = []
    for language, items in sorted(
        rq07_groups.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        language_metrics.append(
            {
                "language": language or "Sem linguagem identificada",
                "count": len(items),
                "small_group": len(items) < SMALL_GROUP_THRESHOLD,
                **{
                    f"{metric}_median": median(item[metric] for item in items)
                    for metric in METRICS
                },
                **{
                    f"{metric}_mean": mean(item[metric] for item in items)
                    for metric in METRICS
                },
            }
        )

    return {
        "analyzed": len(repositories),
        "languages": rq05_rq06_summary["languages"],
        "missing_language_count": rq05_rq06_summary["missing_language_count"],
        "popular_language_count": rq05_rq06_summary["popular_language_count"],
        "repositories_without_issues": len(repositories) - ratio_summary["count"],
        "ratio_summary": ratio_summary,
        "ratio_outliers": ratio_outliers,
        "metric_summaries": metric_summaries,
        "metric_outliers": metric_outliers,
        "language_metrics": language_metrics,
        "small_groups": [
            group for group in language_metrics if group["small_group"]
        ],
    }


def _number(value: int | float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.{decimals}f}"


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def _outlier_rows(outliers: list[dict], percent: bool = False) -> str:
    if not outliers:
        return "Nenhum outlier identificado pelo método IQR."
    ordered = sorted(outliers, key=lambda item: item["value"], reverse=True)
    rows = []
    for item in ordered[:10]:
        value = _percent(item["value"]) if percent else _number(item["value"])
        rows.append(f"- `{item['name_with_owner']}`: {value}")
    suffix = "\n- …" if len(ordered) > 10 else ""
    return "\n".join(rows) + suffix


def build_report(analysis: dict) -> str:
    """Monta o relatorio Markdown de validacao e hipoteses informais."""
    ratio = analysis["ratio_summary"]
    languages = sorted(
        analysis["languages"].items(), key=lambda item: (-item[1], item[0])
    )
    language_rows = "\n".join(
        f"| {language or 'Sem linguagem identificada'} | {count} |"
        for language, count in languages
    )
    group_rows = "\n".join(
        "| {language} | {count} | {prs} | {releases} | {updates} | {small} |".format(
            language=group["language"],
            count=group["count"],
            prs=_number(group["merged_pull_requests_median"]),
            releases=_number(group["releases_count_median"]),
            updates=_number(group["days_since_last_update_median"]),
            small="Sim" if group["small_group"] else "Não",
        )
        for group in analysis["language_metrics"]
    )
    distribution_rows = "\n".join(
        "| {label} | {minimum} | {q1} | {median} | {average} | {q3} | {maximum} | {outliers} |".format(
            label=METRIC_LABELS[metric],
            minimum=_number(summary["min"]),
            q1=_number(summary["q1"]),
            median=_number(summary["median"]),
            average=_number(summary["mean"]),
            q3=_number(summary["q3"]),
            maximum=_number(summary["max"]),
            outliers=len(analysis["metric_outliers"][metric]),
        )
        for metric, summary in analysis["metric_summaries"].items()
    )
    small_groups = ", ".join(
        f"{group['language']} ({group['count']})" for group in analysis["small_groups"]
    ) or "Nenhum"

    return f"""# Validação das RQ05, RQ06 e RQ07 — Lab01S02

Base analisada: **{analysis['analyzed']} repositórios únicos**.

## Hipóteses informais

- **RQ05:** espera-se que a maioria dos repositórios populares utilize linguagens presentes no top 10 do GitHub Octoverse 2024, com concentração em Python, JavaScript e TypeScript.
- **RQ06:** espera-se que repositórios populares apresentem uma proporção elevada de issues fechadas, embora projetos com manutenção ou crescimento intenso possam manter mais issues abertas.
- **RQ07:** espera-se que linguagens populares apresentem maior contribuição externa e mais releases; a frequência de atualização pode variar pouco entre projetos muito populares.

Fonte de linguagens populares: {POPULAR_LANGUAGES_SOURCE}.

## Integridade e valores ausentes

- Registros analisados: {analysis['analyzed']}
- Linguagem primária ausente: {analysis['missing_language_count']}
- Linguagem presente no top 10 adotado: {analysis['popular_language_count']}
- Repositórios sem issues, cuja razão não é calculável: {analysis['repositories_without_issues']}
- Proporções inválidas ou inconsistentes: **0** (a validação interrompe a execução caso encontre alguma)

## RQ05 — Distribuição das linguagens

| Linguagem | Repositórios |
|---|---:|
{language_rows}

## RQ06 — Proporção de issues fechadas

| Registros válidos | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers IQR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| {ratio['count']} | {_percent(ratio['min'])} | {_percent(ratio['q1'])} | {_percent(ratio['median'])} | {_percent(ratio['mean'])} | {_percent(ratio['q3'])} | {_percent(ratio['max'])} | {len(analysis['ratio_outliers'])} |

Outliers de proporção (até 10 exibidos):

{_outlier_rows(analysis['ratio_outliers'], percent=True)}

## RQ07 — Distribuições gerais

Outliers são definidos pelo método IQR: valores abaixo de `Q1 - 1,5 × IQR` ou acima de `Q3 + 1,5 × IQR`.

| Métrica | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers |
|---|---:|---:|---:|---:|---:|---:|---:|
{distribution_rows}

### Métricas agrupadas por linguagem

Grupos com menos de {SMALL_GROUP_THRESHOLD} repositórios são marcados como pequenos e devem ser interpretados com cautela.

| Linguagem | Repositórios | Mediana de PRs aceitas | Mediana de releases | Mediana de dias desde atualização | Grupo pequeno |
|---|---:|---:|---:|---:|---|
{group_rows}

Grupos pequenos identificados: {small_groups}.

### Possíveis outliers por métrica

#### PRs aceitas

{_outlier_rows(analysis['metric_outliers']['merged_pull_requests'])}

#### Releases

{_outlier_rows(analysis['metric_outliers']['releases_count'])}

#### Dias desde a atualização

{_outlier_rows(analysis['metric_outliers']['days_since_last_update'])}

## Resultado da validação

Os {analysis['analyzed']} registros passaram pelas verificações estruturais das RQ05, RQ06 e RQ07. Valores ausentes, distribuições, grupos pequenos e possíveis outliers estão registrados neste documento. As hipóteses são informais e deverão ser confrontadas com análises e visualizações na Sprint 3.
"""


def write_report(analysis: dict, output_path: Path) -> None:
    """Grava o relatorio de validacao em Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report(analysis), encoding="utf-8")
