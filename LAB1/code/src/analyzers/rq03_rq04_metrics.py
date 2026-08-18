"""Analise e validacao das metricas de RQ03 e RQ04."""

import csv
import sys
from pathlib import Path
from statistics import mean, median, quantiles

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validators.rq03_rq04 import validate_dataset


DEFAULT_INPUT_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "top_repositories.csv"
)
DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "rq03-rq04.md"
DEFAULT_VALIDATION_PATH = (
    Path(__file__).resolve().parents[3] / "reports" / "validacao-rq03-rq04.md"
)


def load_repositories(input_path: Path) -> list[dict]:
    """Carrega o CSV consolidado da coleta."""
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


def format_number(value: float) -> str:
    """Formata numeros para leitura no relatorio."""
    if isinstance(value, int) or value.is_integer():
        return str(int(value))

    return f"{value:.2f}".replace(".", ",")


def build_validation_report(summary: dict) -> str:
    """Monta o resumo da validacao dos 1000 registros."""
    top_release_outliers = "\n".join(
        f"- {name}: {count} releases" for name, count in summary["release_outliers"][:10]
    ) or "- nenhum"
    top_push_outliers = "\n".join(
        f"- {name}: {days} dias desde o ultimo push"
        for name, days in summary["push_outliers"][:10]
    ) or "- nenhum"

    missing_fields = {}
    for item in summary["missing"]:
        missing_fields[item["field"]] = missing_fields.get(item["field"], 0) + 1

    missing_lines = (
        "\n".join(f"- `{field}`: {count}" for field, count in missing_fields.items())
        or "- nenhum campo ausente"
    )
    invalid_lines = (
        "\n".join(
            f"- {item['name']}: {item['reason']}" for item in summary["invalid"][:20]
        )
        or "- nenhum valor invalido"
    )

    return f"""# Validacao RQ03 e RQ04

Base: {summary["analyzed"]} repositorios do CSV consolidado.

## Quantidade

- Registros analisados: {summary["analyzed"]}
- Valores ausentes: {len(summary["missing"])}
- Valores invalidos: {len(summary["invalid"])}

## Ausentes

{missing_lines}

## Invalidos

{invalid_lines}

## Outliers (IQR)

- Releases: {len(summary["release_outliers"])}
- Dias desde `updatedAt`: {len(summary["update_outliers"])}
- Dias desde `pushedAt`: {len(summary["push_outliers"])}

Maiores outliers de releases:

{top_release_outliers}

Maiores outliers de `pushedAt`:

{top_push_outliers}

## Limitacao de `updatedAt`

- Mediana de dias desde `updatedAt`: {summary["median_update"]}
- Repositorios com `updatedAt` no dia da coleta: {summary["updated_at_zero"]}
- Mediana de dias desde `pushedAt`: {summary["median_push"]}
- Repositorios com `pushedAt` no dia da coleta: {summary["pushed_at_zero"]}

`updatedAt` muda com atividade do repositorio (issues, PRs, wiki) e quase nao
varia entre projetos populares. `pushedAt` foi incluido para medir a ultima
atualizacao do conteudo.
"""


def build_markdown_report(metrics: dict) -> str:
    """Monta o texto com hipoteses e resultados de RQ03 e RQ04."""
    releases = metrics["releases"]
    days = metrics["days_push"] if metrics["days_push"]["count"] else metrics["days_update"]

    top_release_rows = "\n".join(
        "| {name} | {releases} | {days} |".format(
            name=repository["name_with_owner"],
            releases=repository["releases_count"],
            days=repository.get("days_since_last_push")
            or repository.get("days_since_last_update"),
        )
        for repository in metrics["top_release_repositories"]
    )

    return f"""# RQ03 e RQ04

Base analisada: {metrics["total_repositories"]} repositorios mais populares coletados no GitHub.

## Hipoteses informais (Lab01S02)

**RQ03.** A expectativa e que repositorios populares lancem releases com
frequencia. Ainda assim, o total acumulado de releases nao mede intervalo entre
versoes: projetos grandes podem ter muitas releases, enquanto listas e
material de estudo podem ter zero. A hipotese de trabalho e mediana baixa,
com cauda longa e muitos zeros.

**RQ04.** A expectativa e que projetos populares sejam atualizados com
frequencia. `updatedAt` nao serve bem para isso, porque qualquer atividade no
GitHub altera o campo. A hipotese de trabalho e que `pushedAt` mostre a
maioria com push recente, mas com mais variacao do que `updatedAt`.

## RQ03 - Sistemas populares lancam releases com frequencia?

Resposta direta: parcialmente.

Metrica usada: total de releases (`releases.totalCount`).

Resultados principais:

- Total de repositorios analisados: {metrics["total_repositories"]}
- Mediana: {format_number(releases["median"])} releases
- Media: {format_number(releases["mean"])} releases
- Primeiro quartil: {format_number(releases["q1"])} releases
- Terceiro quartil: {format_number(releases["q3"])} releases
- Minimo: {format_number(releases["min"])} releases
- Maximo: {format_number(releases["max"])} releases
- Repositorios sem releases: {metrics["repositories_with_zero_releases"]}
- Repositorios com pelo menos 10 releases: {metrics["repositories_with_at_least_10_releases"]}
- Outliers de releases: {metrics["release_outliers"]}

| Repositorio | Releases | Dias desde o ultimo push |
|---|---:|---:|
{top_release_rows}

Discussao: a mediana e bem menor que a media, o que indica concentracao de
releases em poucos projetos. Ter {metrics["repositories_with_zero_releases"]}
repositorios sem release mostra que popularidade no GitHub nao implica uso
formal de versionamento por release.

Conclusao: a hipotese de frequencia alta so se confirma para parte da amostra.
No conjunto dos {metrics["total_repositories"]}, o padrao e heterogeneo.

## RQ04 - Sistemas populares sao atualizados com frequencia?

Resposta direta: sim, com ressalva sobre o campo usado.

Metrica usada: dias desde `pushedAt`, com `updatedAt` so para comparacao.

Resultados principais (`updatedAt`):

- Mediana: {format_number(metrics["days_update"]["median"])} dias
- Media: {format_number(metrics["days_update"]["mean"])} dias
- Atualizados no dia da coleta: {metrics["updated_at_zero"]}

Resultados principais (`pushedAt`):

- Mediana: {format_number(days["median"])} dias
- Media: {format_number(days["mean"])} dias
- Minimo: {format_number(days["min"])} dias
- Maximo: {format_number(days["max"])} dias
- Push nos ultimos 7 dias: {metrics["pushed_in_7_days"]}
- Push nos ultimos 30 dias: {metrics["pushed_in_30_days"]}
- Push nos ultimos 90 dias: {metrics["pushed_in_90_days"]}
- Outliers de `pushedAt`: {metrics["push_outliers"]}

Discussao: `updatedAt` continua pouco discriminante. `pushedAt` separa melhor
projetos ativos de projetos parados e confirma a limitacao ja vista na sprint
anterior.

Conclusao: os repositorios populares tendem a receber push recente, mas a RQ04
so fica confiavel quando a metrica usa `pushedAt`.
"""


def print_metrics(metrics: dict) -> None:
    """Exibe as metricas principais no terminal."""
    releases = metrics["releases"]
    print(f"Repositorios analisados: {metrics['total_repositories']}")
    print("RQ03 - releases")
    print(
        f"min={format_number(releases['min'])}; "
        f"mediana={format_number(releases['median'])}; "
        f"media={format_number(releases['mean'])}; "
        f"max={format_number(releases['max'])}"
    )
    print(f"zeros={metrics['repositories_with_zero_releases']}")
    print("RQ04 - dias desde pushedAt")
    days = metrics["days_push"]
    print(
        f"min={format_number(days['min'])}; "
        f"mediana={format_number(days['median'])}; "
        f"media={format_number(days['mean'])}; "
        f"max={format_number(days['max'])}"
    )


def analyze_repositories(repositories: list[dict], summary: dict) -> dict:
    """Calcula distribuicao, outliers e recortes para o relatorio."""
    releases_summary = summarize(summary["releases"])
    update_summary = summarize(summary["days_update"])
    push_summary = summarize(summary["days_push"]) if summary["days_push"] else {
        "min": 0, "q1": 0, "median": 0, "mean": 0, "q3": 0, "max": 0, "count": 0
    }
    if summary["days_push"]:
        push_summary["count"] = len(summary["days_push"])
    update_summary["count"] = len(summary["days_update"])

    top_release_repositories = sorted(
        repositories,
        key=lambda repository: int(float(repository["releases_count"] or 0)),
        reverse=True,
    )[:5]

    return {
        "total_repositories": len(repositories),
        "releases": releases_summary,
        "days_update": update_summary,
        "days_push": push_summary,
        "repositories_with_zero_releases": sum(
            1 for value in summary["releases"] if value == 0
        ),
        "repositories_with_at_least_10_releases": sum(
            1 for value in summary["releases"] if value >= 10
        ),
        "release_outliers": len(summary["release_outliers"]),
        "push_outliers": len(summary["push_outliers"]),
        "updated_at_zero": summary["updated_at_zero"],
        "pushed_in_7_days": sum(1 for value in summary["days_push"] if value <= 7),
        "pushed_in_30_days": sum(1 for value in summary["days_push"] if value <= 30),
        "pushed_in_90_days": sum(1 for value in summary["days_push"] if value <= 90),
        "top_release_repositories": top_release_repositories,
    }


def main() -> None:
    repositories = load_repositories(DEFAULT_INPUT_PATH)
    summary = validate_dataset(repositories, expected_count=1000)
    metrics = analyze_repositories(repositories, summary)

    DEFAULT_VALIDATION_PATH.write_text(build_validation_report(summary), encoding="utf-8")
    DEFAULT_REPORT_PATH.write_text(build_markdown_report(metrics), encoding="utf-8")

    print_metrics(metrics)
    print(f"Resumo da validacao: {DEFAULT_VALIDATION_PATH}")
    print(f"Relatorio gerado: {DEFAULT_REPORT_PATH}")


if __name__ == "__main__":
    main()
