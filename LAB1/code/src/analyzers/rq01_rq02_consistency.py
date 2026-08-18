"""Analise de consistencia e relatorio das RQ01 e RQ02."""

from pathlib import Path
from statistics import mean, median, quantiles


METRICS = ("repository_age_days", "merged_pull_requests")
METRIC_LABELS = {
    "repository_age_days": "Idade do repositório (dias)",
    "merged_pull_requests": "Pull Requests aceitas",
}


def describe(values: list[int]) -> dict:
    """Calcula estatisticas descritivas e limites IQR."""
    ordered = sorted(values)
    quartiles = quantiles(ordered, n=4, method="inclusive")
    q1, q3 = quartiles[0], quartiles[2]
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


def find_outliers(repositories: list[dict], field: str, summary: dict) -> list[dict]:
    """Retorna os registros fora dos limites IQR."""
    return [
        {
            "name_with_owner": repository["name_with_owner"],
            "value": repository[field],
        }
        for repository in repositories
        if repository[field] < summary["lower_bound"]
        or repository[field] > summary["upper_bound"]
    ]


def analyze_consistency(repositories: list[dict], validation: dict) -> dict:
    """Calcula distribuicoes e possiveis outliers de RQ01 e RQ02."""
    summaries = {
        metric: describe([repository[metric] for repository in repositories])
        for metric in METRICS
    }
    outliers = {
        metric: find_outliers(repositories, metric, summaries[metric])
        for metric in METRICS
    }
    return {
        **validation,
        "summaries": summaries,
        "outliers": outliers,
        "zero_merged_prs": sum(
            repository["merged_pull_requests"] == 0 for repository in repositories
        ),
        "at_least_100_prs": sum(
            repository["merged_pull_requests"] >= 100 for repository in repositories
        ),
        "at_least_1000_prs": sum(
            repository["merged_pull_requests"] >= 1000 for repository in repositories
        ),
        "oldest": sorted(
            repositories,
            key=lambda repository: repository["repository_age_days"],
            reverse=True,
        )[:10],
        "top_prs": sorted(
            repositories,
            key=lambda repository: repository["merged_pull_requests"],
            reverse=True,
        )[:10],
    }


def _number(value: int | float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _outlier_list(outliers: list[dict]) -> str:
    if not outliers:
        return "Nenhum outlier identificado pelo método IQR."
    ordered = sorted(outliers, key=lambda item: item["value"], reverse=True)
    rows = [
        f"- `{item['name_with_owner']}`: {_number(item['value'])}"
        for item in ordered[:10]
    ]
    if len(ordered) > 10:
        rows.append(f"- … e mais {len(ordered) - 10} registros")
    return "\n".join(rows)


def _repository_rows(repositories: list[dict]) -> str:
    return "\n".join(
        "| {name} | {age} | {prs} |".format(
            name=repository["name_with_owner"],
            age=repository["repository_age_days"],
            prs=repository["merged_pull_requests"],
        )
        for repository in repositories
    )


def build_report(analysis: dict) -> str:
    """Monta o relatorio atualizado de RQ01 e RQ02."""
    age = analysis["summaries"]["repository_age_days"]
    prs = analysis["summaries"]["merged_pull_requests"]
    distribution_rows = "\n".join(
        "| {label} | {minimum} | {q1} | {median} | {average} | {q3} | {maximum} | {outliers} |".format(
            label=METRIC_LABELS[metric],
            minimum=_number(summary["min"]),
            q1=_number(summary["q1"]),
            median=_number(summary["median"]),
            average=_number(summary["mean"]),
            q3=_number(summary["q3"]),
            maximum=_number(summary["max"]),
            outliers=len(analysis["outliers"][metric]),
        )
        for metric, summary in analysis["summaries"].items()
    )

    return f"""# RQ01 e RQ02 — Lab01S02

Base analisada: **{analysis['analyzed']} repositórios populares únicos** coletados no GitHub.

## Hipóteses informais

- **RQ01:** espera-se que os repositórios mais populares sejam projetos maduros, com idade mediana de vários anos, pois acumular estrelas e comunidade tende a exigir tempo.
- **RQ02:** espera-se que repositórios populares recebam muitas contribuições externas, mas com distribuição assimétrica devido a poucos projetos com volumes extremamente altos de Pull Requests.

## Validação de integridade

- Registros analisados: {analysis['analyzed']}
- Repositórios únicos: {analysis['unique_repositories']}
- Duplicados: {analysis['duplicate_count']}
- `name_with_owner` ausente: {analysis['missing']['name_with_owner']}
- `created_at` ausente: {analysis['missing']['created_at']}
- `repository_age_days` ausente: {analysis['missing']['repository_age_days']}
- `merged_pull_requests` ausente: {analysis['missing']['merged_pull_requests']}
- Valores negativos ou tipos inválidos: **0** (a validação interrompe a execução se encontrar algum)

## Distribuições e outliers

Outliers são definidos pelo método IQR: valores abaixo de `Q1 - 1,5 × IQR` ou acima de `Q3 + 1,5 × IQR`.

| Métrica | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers |
|---|---:|---:|---:|---:|---:|---:|---:|
{distribution_rows}

## RQ01 — Sistemas populares são maduros/antigos?

A idade mediana foi de **{_number(age['median'])} dias** ({age['median'] / 365:.2f} anos), e a média foi de **{_number(age['mean'])} dias** ({age['mean'] / 365:.2f} anos).

### Repositórios mais antigos

| Repositório | Idade em dias | PRs aceitas |
|---|---:|---:|
{_repository_rows(analysis['oldest'])}

### Possíveis outliers de idade

{_outlier_list(analysis['outliers']['repository_age_days'])}

Conclusão preliminar: a hipótese será considerada compatível caso a mediana confirme vários anos de existência. A interpretação definitiva será aprofundada com visualizações na Sprint 3.

## RQ02 — Sistemas populares recebem muita contribuição externa?

- Mediana de PRs aceitas: **{_number(prs['median'])}**
- Média de PRs aceitas: **{_number(prs['mean'])}**
- Repositórios com 0 PRs aceitas: {analysis['zero_merged_prs']}
- Repositórios com pelo menos 100 PRs aceitas: {analysis['at_least_100_prs']}
- Repositórios com pelo menos 1.000 PRs aceitas: {analysis['at_least_1000_prs']}

### Repositórios com mais PRs aceitas

| Repositório | Idade em dias | PRs aceitas |
|---|---:|---:|
{_repository_rows(analysis['top_prs'])}

### Possíveis outliers de PRs aceitas

{_outlier_list(analysis['outliers']['merged_pull_requests'])}

Conclusão preliminar: a diferença entre média e mediana e a quantidade de outliers permitem avaliar a assimetria esperada na hipótese. A conclusão final será confrontada com gráficos na Sprint 3.
"""


def write_report(analysis: dict, output_path: Path) -> None:
    """Substitui o relatorio de RQ01/RQ02 pela versao dos 1.000 registros."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report(analysis), encoding="utf-8")
