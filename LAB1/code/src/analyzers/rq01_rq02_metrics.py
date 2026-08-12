"""Analise das metricas de RQ01 e RQ02."""

import csv
from pathlib import Path
from statistics import mean, median, quantiles


DEFAULT_INPUT_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "rq01_rq02.csv"
)
DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parents[3] / "reports" / "rq01-rq02.md"
)


def load_repositories(input_path: Path) -> list[dict]:
    """Carrega o CSV gerado pela coleta de RQ01 e RQ02."""
    with input_path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def summarize(values: list[int]) -> dict:
    """Calcula medidas descritivas basicas."""
    ordered_values = sorted(values)
    quartiles = quantiles(ordered_values, n=4, method="inclusive")

    return {
        "min": min(values),
        "q1": quartiles[0],
        "median": median(values),
        "mean": mean(values),
        "q3": quartiles[2],
        "max": max(values),
    }


def analyze_repositories(repositories: list[dict]) -> dict:
    """Gera as metricas necessarias para responder RQ01 e RQ02."""
    ages = [int(repository["repository_age_days"]) for repository in repositories]
    merged_prs = [
        int(repository["merged_pull_requests"]) for repository in repositories
    ]

    oldest_repositories = sorted(
        repositories,
        key=lambda repository: int(repository["repository_age_days"]),
        reverse=True,
    )[:5]

    top_pr_repositories = sorted(
        repositories,
        key=lambda repository: int(repository["merged_pull_requests"]),
        reverse=True,
    )[:5]

    return {
        "total_repositories": len(repositories),
        "age_days": summarize(ages),
        "age_years_median": median(ages) / 365,
        "age_years_mean": mean(ages) / 365,
        "merged_prs": summarize(merged_prs),
        "repositories_with_zero_prs": sum(1 for value in merged_prs if value == 0),
        "repositories_with_at_least_100_prs": sum(
            1 for value in merged_prs if value >= 100
        ),
        "repositories_with_at_least_1000_prs": sum(
            1 for value in merged_prs if value >= 1000
        ),
        "oldest_repositories": oldest_repositories,
        "top_pr_repositories": top_pr_repositories,
    }


def format_number(value: float) -> str:
    """Formata numeros para leitura no relatorio."""
    if isinstance(value, int) or value.is_integer():
        return str(int(value))

    return f"{value:.2f}"


def build_markdown_report(metrics: dict) -> str:
    """Monta o texto em Markdown com as respostas de RQ01 e RQ02."""
    age = metrics["age_days"]
    prs = metrics["merged_prs"]

    oldest_rows = "\n".join(
        "| {name} | {age} | {prs} |".format(
            name=repository["name_with_owner"],
            age=repository["repository_age_days"],
            prs=repository["merged_pull_requests"],
        )
        for repository in metrics["oldest_repositories"]
    )

    top_pr_rows = "\n".join(
        "| {name} | {age} | {prs} |".format(
            name=repository["name_with_owner"],
            age=repository["repository_age_days"],
            prs=repository["merged_pull_requests"],
        )
        for repository in metrics["top_pr_repositories"]
    )

    return f"""# RQ01 e RQ02

Base analisada: {metrics["total_repositories"]} repositorios mais populares coletados no GitHub.

## RQ01 - Sistemas populares sao maduros/antigos?

Sim. A idade mediana dos repositorios analisados foi de {format_number(age["median"])} dias, aproximadamente {metrics["age_years_median"]:.2f} anos. A media foi de {format_number(age["mean"])} dias, aproximadamente {metrics["age_years_mean"]:.2f} anos.

Tambem foi observado que o repositorio mais antigo da amostra possui {format_number(age["max"])} dias, enquanto o mais recente possui {format_number(age["min"])} dias. O primeiro quartil foi de {format_number(age["q1"])} dias e o terceiro quartil foi de {format_number(age["q3"])} dias.

Conclusao: os dados indicam que repositorios populares tendem a ser projetos maduros, com varios anos de existencia, embora ainda existam projetos recentes entre os mais estrelados.

| Repositorio | Idade em dias | PRs aceitas |
|---|---:|---:|
{oldest_rows}

## RQ02 - Sistemas populares recebem muita contribuicao externa?

Sim. A mediana de pull requests aceitas foi de {format_number(prs["median"])} por repositorio. A media foi de {format_number(prs["mean"])}, indicando que alguns projetos concentram volumes muito altos de contribuicao.

Dos {metrics["total_repositories"]} repositorios analisados, {metrics["repositories_with_at_least_100_prs"]} possuem pelo menos 100 pull requests aceitas e {metrics["repositories_with_at_least_1000_prs"]} possuem pelo menos 1000 pull requests aceitas. Apenas {metrics["repositories_with_zero_prs"]} repositorios aparecem com 0 pull requests aceitas.

Conclusao: a maioria dos repositorios populares analisados apresenta forte participacao externa, ainda que exista grande variacao entre os projetos.

| Repositorio | Idade em dias | PRs aceitas |
|---|---:|---:|
{top_pr_rows}
"""


def print_metrics(metrics: dict) -> None:
    """Exibe as metricas principais no terminal."""
    age = metrics["age_days"]
    prs = metrics["merged_prs"]

    print(f"Repositorios analisados: {metrics['total_repositories']}")
    print("RQ01 - idade do repositorio em dias")
    print(
        f"min={format_number(age['min'])}; mediana={format_number(age['median'])}; "
        f"media={format_number(age['mean'])}; max={format_number(age['max'])}"
    )
    print(f"mediana em anos={metrics['age_years_median']:.2f}")
    print("RQ02 - pull requests aceitas")
    print(
        f"min={format_number(prs['min'])}; mediana={format_number(prs['median'])}; "
        f"media={format_number(prs['mean'])}; max={format_number(prs['max'])}"
    )
    print(f"repositorios com >=100 PRs: {metrics['repositories_with_at_least_100_prs']}")
    print(
        f"repositorios com >=1000 PRs: "
        f"{metrics['repositories_with_at_least_1000_prs']}"
    )
    print(f"repositorios com 0 PRs: {metrics['repositories_with_zero_prs']}")


def main() -> None:
    repositories = load_repositories(DEFAULT_INPUT_PATH)
    metrics = analyze_repositories(repositories)
    report = build_markdown_report(metrics)

    DEFAULT_REPORT_PATH.write_text(report, encoding="utf-8")
    print_metrics(metrics)
    print(f"Relatorio gerado: {DEFAULT_REPORT_PATH}")


if __name__ == "__main__":
    main()
