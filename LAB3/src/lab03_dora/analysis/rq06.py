"""RQ06: metricas DORA entre subgrupos de repositorios.

Fatores: linguagem principal, quartis de estrelas, quartis de contribuidores e
quartis de idade. Cada fator x metrica passa por Kruskal-Wallis (ou
Mann-Whitney com dois grupos). Os p-valores sao corrigidos por Holm na familia
inteira de testes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_METRICS = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_metrics.csv"
DEFAULT_METADATA = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_repository_metadata.csv"
DEFAULT_OUTPUT = LAB3_ROOT / "reports" / "rq06"
ALPHA = 0.05
MIN_LANGUAGE_GROUP = 20
OTHER_LANGUAGE = "Outras"
QUARTILE_LABELS = ("Q1", "Q2", "Q3", "Q4")

METRICS = (
    ("deployment_frequency_per_week", "RQ01 deployment frequency", "releases/semana"),
    ("lead_time_by_release_days", "RQ02 lead time por release", "dias"),
    ("lead_time_by_commit_days", "RQ02 lead time por commit", "dias"),
    ("cfr_ci", "RQ03 CFR(a)", "proporcao"),
    ("cfr_b", "RQ03 CFR(b)", "proporcao"),
    ("recovery_median_hours", "RQ04 tempo de recuperacao", "horas"),
)
FACTORS = (
    ("language", "Linguagem principal"),
    ("stars_quartile", "Popularidade (quartis de estrelas)"),
    ("contributors_quartile", "Contribuidores (quartis)"),
    ("age_quartile", "Idade do repositorio (quartis)"),
)
HYPOTHESES = {
    "language": "A distribuicao de cada metrica difere entre linguagens. Ecossistemas tem cadencias de release e praticas de CI diferentes.",
    "stars_quartile": "Repositorios mais populares publicam com mais frequencia e falham menos no CI, porque tem mais revisao e automacao.",
    "contributors_quartile": "Mais contribuidores aumentam a frequencia de deploy e tambem as falhas de CI, por haver mais mudancas concorrentes.",
    "age_quartile": "Repositorios mais antigos sao mais estaveis: CFR menor e recuperacao mais rapida, mas lead time maior.",
}


@dataclass(frozen=True)
class TestResult:
    factor: str
    metric: str
    test: str
    groups: int
    n: int
    n_missing: int
    statistic: float | None
    p_value: float | None
    p_holm: float | None
    significant_holm: bool | None
    effect_size: str
    effect_value: float | None
    effect_magnitude: str
    extreme_cliffs_delta: float | None
    extreme_cliffs_magnitude: str
    note: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "repository" not in rows[0]:
        raise ValueError(f"CSV invalido ou vazio: {path}")
    return rows


def merge_metadata(metrics: Sequence[dict[str, Any]], metadata: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_repository = {row["repository"]: row for row in metadata}
    merged = []
    for row in metrics:
        extra = by_repository.get(row["repository"], {})
        merged.append({**row, **{key: value for key, value in extra.items() if key != "repository"}})
    return merged


def quartile_groups(values: Sequence[float | None]) -> tuple[list[str], list[float]]:
    """Q1 a Q4 pelos cortes 25/50/75. Ausente fica sem grupo."""

    present = [value for value in values if value is not None]
    if not present:
        return ["" for _ in values], []
    cuts = [float(cut) for cut in np.percentile(present, [25, 50, 75])]
    labels = []
    for value in values:
        if value is None:
            labels.append("")
        elif value <= cuts[0]:
            labels.append("Q1")
        elif value <= cuts[1]:
            labels.append("Q2")
        elif value <= cuts[2]:
            labels.append("Q3")
        else:
            labels.append("Q4")
    return labels, cuts


def language_groups(languages: Sequence[str], minimum: int = MIN_LANGUAGE_GROUP) -> list[str]:
    """Linguagens com menos de `minimum` repositorios, ou vazias, viram 'Outras'."""

    counts = Counter(language for language in languages if language)
    return [language if language and counts[language] >= minimum else OTHER_LANGUAGE for language in languages]


def assign_factors(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    enriched = [dict(row) for row in rows]
    for row, label in zip(enriched, language_groups([str(row.get("language") or "") for row in enriched])):
        row["language_group"] = label
    cuts = {}
    for source, factor in (("stars", "stars_quartile"), ("contributors", "contributors_quartile"), ("age_years", "age_quartile")):
        labels, factor_cuts = quartile_groups([_as_number(row.get(source)) for row in enriched])
        cuts[factor] = factor_cuts
        for row, label in zip(enriched, labels):
            row[factor] = label
    for row in enriched:
        row["language"] = row["language_group"]
    return enriched, cuts


def epsilon_squared(h_statistic: float, n: int) -> float:
    """Tamanho de efeito do Kruskal-Wallis: H / (n - 1)."""

    return h_statistic / (n - 1)


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """delta = 2 * U1 / (n1 * n2) - 1, com U1 de mannwhitneyu(x, y)."""

    u1 = stats.mannwhitneyu(x, y, alternative="two-sided").statistic
    return 2 * float(u1) / (len(x) * len(y)) - 1


def cliffs_magnitude(delta: float | None) -> str:
    """Romano et al. (2006): < 0,147 desprezivel; < 0,33 pequeno; < 0,474 medio."""

    if delta is None:
        return ""
    size = abs(delta)
    if size < 0.147:
        return "desprezivel"
    if size < 0.33:
        return "pequeno"
    if size < 0.474:
        return "medio"
    return "grande"


def epsilon_magnitude(value: float | None) -> str:
    """Faixas de Tomczak e Tomczak (2014) para epsilon^2: 0,01; 0,08; 0,26."""

    if value is None:
        return ""
    if value < 0.01:
        return "desprezivel"
    if value < 0.08:
        return "pequeno"
    if value < 0.26:
        return "medio"
    return "grande"


def compare_groups(rows: Sequence[dict[str, Any]], factor: str, metric: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups: dict[str, list[float]] = {}
    missing = 0
    for row in rows:
        label = str(row.get(factor) or "")
        value = _as_number(row.get(metric))
        if not label or value is None:
            missing += 1
            continue
        groups.setdefault(label, []).append(value)
    ordered = sorted(groups, key=_group_order)
    samples = [groups[label] for label in ordered if len(groups[label]) >= 2]
    n = sum(len(sample) for sample in samples)
    descriptive = [_describe(factor, metric, label, groups[label]) for label in ordered]
    base = {"factor": factor, "metric": metric, "groups": len(samples), "n": n, "n_missing": missing}
    if len(samples) < 2:
        return {**base, "test": "", "statistic": None, "p_value": None, "effect_size": "", "effect_value": None, "note": "menos de dois grupos com dados"}, descriptive
    if len({value for sample in samples for value in sample}) < 2:
        return {**base, "test": "", "statistic": None, "p_value": None, "effect_size": "", "effect_value": None, "note": "metrica constante"}, descriptive
    if len(samples) == 2:
        result = stats.mannwhitneyu(samples[0], samples[1], alternative="two-sided")
        delta = cliffs_delta(samples[0], samples[1])
        return {**base, "test": "Mann-Whitney", "statistic": float(result.statistic), "p_value": float(result.pvalue), "effect_size": "cliffs_delta", "effect_value": delta, "note": ""}, descriptive
    result = stats.kruskal(*samples)
    statistic = float(result.statistic)
    return {**base, "test": "Kruskal-Wallis", "statistic": statistic, "p_value": float(result.pvalue), "effect_size": "epsilon_squared", "effect_value": epsilon_squared(statistic, n), "note": ""}, descriptive


def holm(p_values: Sequence[float | None]) -> list[float | None]:
    valid = [(index, value) for index, value in enumerate(p_values) if value is not None]
    adjusted: list[float | None] = [None] * len(p_values)
    if not valid:
        return adjusted
    corrected = multipletests([value for _, value in valid], alpha=ALPHA, method="holm")[1]
    for (index, _), value in zip(valid, corrected):
        adjusted[index] = float(value)
    return adjusted


def analyze(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    enriched, cuts = assign_factors(rows)
    raw_results = []
    descriptive = []
    for factor, _label in FACTORS:
        for metric, _metric_label, _unit in METRICS:
            result, groups = compare_groups(enriched, factor, metric)
            raw_results.append(result)
            descriptive.extend(groups)
    adjusted = holm([item["p_value"] for item in raw_results])
    tests = []
    for item, p_holm in zip(raw_results, adjusted):
        extreme = _extreme_delta(enriched, item["factor"], item["metric"])
        magnitude = cliffs_magnitude(item["effect_value"]) if item["effect_size"] == "cliffs_delta" else epsilon_magnitude(item["effect_value"])
        tests.append(
            asdict(
                TestResult(
                    factor=item["factor"],
                    metric=item["metric"],
                    test=item["test"],
                    groups=item["groups"],
                    n=item["n"],
                    n_missing=item["n_missing"],
                    statistic=item["statistic"],
                    p_value=item["p_value"],
                    p_holm=p_holm,
                    significant_holm=None if p_holm is None else p_holm < ALPHA,
                    effect_size=item["effect_size"],
                    effect_value=item["effect_value"],
                    effect_magnitude=magnitude,
                    extreme_cliffs_delta=extreme,
                    extreme_cliffs_magnitude=cliffs_magnitude(extreme),
                    note=item["note"],
                )
            )
        )
    group_sizes = [
        {"factor": factor, "group": label, "repositories": count}
        for factor, _ in FACTORS
        for label, count in sorted(Counter(str(row.get(factor) or "ausente") for row in enriched).items(), key=lambda pair: _group_order(pair[0]))
    ]
    return {
        "issue": 121,
        "repository_count": len(rows),
        "factors": [{"factor": factor, "label": label, "hypothesis": HYPOTHESES[factor]} for factor, label in FACTORS],
        "metrics": [{"metric": metric, "label": label, "unit": unit} for metric, label, unit in METRICS],
        "quartile_cuts": cuts,
        "language_rule": f"linguagens com pelo menos {MIN_LANGUAGE_GROUP} repositorios; demais e vazias em '{OTHER_LANGUAGE}'",
        "method": {
            "test": "Kruskal-Wallis com 3+ grupos; Mann-Whitney com 2 grupos; bicaudal",
            "correction": f"Holm (statsmodels multipletests) sobre os {len(tests)} testes, alfa {ALPHA}",
            "effect_size": "epsilon^2 = H / (n - 1) no Kruskal-Wallis; Cliff's delta no Mann-Whitney",
            "extreme_cliffs_delta": "Cliff's delta entre Q4 e Q1 nos fatores por quartil; positivo indica valores maiores em Q4",
            "missing": "repositorio sem valor da metrica ou sem grupo sai daquele teste; ausente nao vira zero",
        },
        "group_sizes": group_sizes,
        "tests": tests,
        "groups": descriptive,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rq06-summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(output_dir / "rq06-tests.csv", result["tests"])
    _write_csv(output_dir / "rq06-groups.csv", result["groups"])
    _write_csv(output_dir / "rq06-group-sizes.csv", result["group_sizes"])
    _write_markdown(result, output_dir / "rq06-summary.md")
    _write_heatmap(result, output_dir / "rq06-effect-sizes.svg")
    for factor, label in FACTORS:
        _write_factor_figure(result, factor, label, output_dir / f"rq06-{factor.replace('_', '-')}.svg")


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    metric_labels = {item["metric"]: item["label"] for item in result["metrics"]}
    factor_labels = {item["factor"]: item["label"] for item in result["factors"]}
    lines = [
        "# RQ06 - Métricas DORA por subgrupo",
        "",
        f"Repositórios: **{result['repository_count']}**. Fatores: {', '.join(factor_labels.values())}.",
        f"Testes: {len(result['tests'])} (4 fatores x 6 métricas). Correção de Holm sobre a família inteira.",
        "",
        "## Hipóteses",
        "",
        "H0 de cada teste: a distribuição da métrica é igual em todos os grupos do fator. H1: ao menos um grupo difere.",
        "",
    ]
    lines.extend(f"- **{item['label']}:** {item['hypothesis']}" for item in result["factors"])
    lines.extend(["", "## Grupos", ""])
    lines.append(f"- Linguagem: {result['language_rule']}.")
    for factor, cuts in result["quartile_cuts"].items():
        if cuts:
            lines.append(f"- {factor_labels[factor]}: cortes em {', '.join(f'{cut:.2f}' for cut in cuts)}.")
    lines.extend(["", "| Fator | Grupo | Repositórios |", "|---|---|---:|"])
    lines.extend(f"| {factor_labels[item['factor']]} | {item['group']} | {item['repositories']} |" for item in result["group_sizes"])
    lines.extend(
        [
            "",
            "## Resultados",
            "",
            "| Fator | Métrica | Teste | n | H/U | p | p Holm | Efeito | δ Q4 x Q1 |",
            "|---|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for item in result["tests"]:
        effect = "" if item["effect_value"] is None else f"{item['effect_value']:.3f} ({item['effect_magnitude']})"
        extreme = "" if item["extreme_cliffs_delta"] is None else f"{item['extreme_cliffs_delta']:.3f} ({item['extreme_cliffs_magnitude']})"
        mark = " *" if item["significant_holm"] else ""
        lines.append(
            f"| {factor_labels[item['factor']]} | {metric_labels[item['metric']]} | {item['test']} | {item['n']} | {_format(item['statistic'], 2)} | {_format_p(item['p_value'])} | {_format_p(item['p_holm'])}{mark} | {effect} | {extreme} |"
        )
    significant = [item for item in result["tests"] if item["significant_holm"]]
    lines.extend(["", f"\\* significativo após Holm (alfa {ALPHA}). Testes significativos: **{len(significant)}** de {len(result['tests'])}.", ""])
    lines.extend(
        [
            "## Escolha estatística",
            "",
            "- As métricas são assimétricas e limitadas (CFR entre 0 e 1). Por isso os testes são não paramétricos: Kruskal-Wallis para três ou mais grupos e Mann-Whitney para dois.",
            "- O tamanho de efeito do Kruskal-Wallis é ε² = H / (n − 1). Faixas de Tomczak e Tomczak (2014): < 0,01 desprezível; < 0,08 pequeno; < 0,26 médio; ≥ 0,26 grande.",
            "- Nos fatores por quartil, o Cliff's delta entre Q4 e Q1 mostra a direção. δ positivo indica valores maiores no Q4. Faixas de Romano et al. (2006).",
            "- Holm controla o erro de família nos 24 testes. Ausente não vira zero; o repositório só sai do teste daquela métrica.",
            "",
            "## Limitações",
            "",
            "- Estrelas e contribuidores foram lidos na data da coleta (`collected_at`), não no fim de 2025. A idade usa `created_at` até 2025-12-31.",
            "- Contribuidores vêm do endpoint com `anon=true`. Ele conta e-mails anônimos e pode contar a mesma pessoa duas vezes.",
            "- O tipo de projeto (biblioteca, aplicação, CLI) não entrou, porque exige rotulação manual dos 300 repositórios.",
            "- A amostra só tem repositórios com pelo menos 5 releases e 50 workflow runs em 2025, então os grupos não representam todo o GitHub.",
            "- A coleta percorreu as faixas de estrelas a partir de 1000, então a popularidade varia pouco na amostra. Os quartis de estrelas separam faixas estreitas e o teste tem pouco poder para esse fator.",
            "- Os fatores estão correlacionados entre si, por exemplo estrelas e contribuidores. Cada teste olha um fator por vez e não isola o efeito de cada um.",
            "- Associação não implica causa.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_heatmap(result: dict[str, Any], path: Path) -> None:
    metric_labels = [label.split(" ", 1)[1] for label in (item["label"] for item in result["metrics"])]
    factor_labels = [item["label"] for item in result["factors"]]
    by_key = {(item["factor"], item["metric"]): item for item in result["tests"]}
    cell_w, cell_h, left, top = 150, 48, 290, 90
    width, height = left + cell_w * len(metric_labels) + 30, top + cell_h * len(factor_labels) + 80
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif">',
        '<rect width="100%" height="100%" fill="#f7f4ef"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="18">RQ06 - tamanho de efeito por fator e métrica</text>',
    ]
    for column, label in enumerate(metric_labels):
        x = left + column * cell_w + cell_w / 2 - 2
        head, _, tail = label.partition(" por ")
        parts.append(f'<text x="{x}" y="{top - 26}" text-anchor="middle" font-size="12">{_escape(head)}</text>')
        if tail:
            parts.append(f'<text x="{x}" y="{top - 10}" text-anchor="middle" font-size="12">por {_escape(tail)}</text>')
    for row_index, (factor, _label) in enumerate(FACTORS):
        y = top + row_index * cell_h
        parts.append(f'<text x="{left - 10}" y="{y + cell_h / 2 + 4}" text-anchor="end" font-size="12">{_escape(factor_labels[row_index])}</text>')
        for column, (metric, _metric_label, _unit) in enumerate(METRICS):
            item = by_key[(factor, metric)]
            value = item["effect_value"] if item["effect_size"] == "epsilon_squared" else (abs(item["effect_value"]) if item["effect_value"] is not None else None)
            shade = 0.0 if value is None else min(1.0, value / 0.26)
            color = f"rgb({int(247 - 200 * shade)},{int(244 - 140 * shade)},{int(239 - 100 * shade)})"
            x = left + column * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" fill="{color}" stroke="#24313a" stroke-width="0.5"/>')
            text = "" if value is None else f"{value:.3f}{' *' if item['significant_holm'] else ''}"
            parts.append(f'<text x="{x + cell_w / 2 - 2}" y="{y + cell_h / 2 + 4}" text-anchor="middle" font-size="13">{text}</text>')
    parts.append(f'<text x="{left}" y="{height - 30}" font-size="12">Valores: ε² do Kruskal-Wallis. * = significativo após Holm (alfa {ALPHA}).</text>')
    parts.append("</svg>")
    path.write_text("".join(parts) + "\n", encoding="utf-8")


def _write_factor_figure(result: dict[str, Any], factor: str, factor_label: str, path: Path) -> None:
    groups = [item for item in result["groups"] if item["factor"] == factor]
    labels = sorted({item["group"] for item in groups}, key=_group_order)
    panel_w, panel_h, columns = 300, 220, 3
    width, height = panel_w * columns + 40, 70 + panel_h * 2 + 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif">',
        '<rect width="100%" height="100%" fill="#f7f4ef"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="18">RQ06 - mediana e IQR por grupo: {_escape(factor_label)}</text>',
    ]
    for index, (metric, metric_label, unit) in enumerate(METRICS):
        origin_x = 20 + (index % columns) * panel_w
        origin_y = 60 + (index // columns) * panel_h
        stats_by_group = {item["group"]: item for item in groups if item["metric"] == metric}
        top_value = max((item["q3"] for item in stats_by_group.values() if item["q3"] is not None), default=1.0) or 1.0
        plot_left, plot_top, plot_w, plot_h = origin_x + 45, origin_y + 30, panel_w - 70, panel_h - 80
        parts.append(f'<text x="{origin_x + panel_w / 2}" y="{origin_y + 15}" text-anchor="middle" font-size="12">{_escape(metric_label)} ({unit})</text>')
        parts.append(f'<line x1="{plot_left}" y1="{plot_top + plot_h}" x2="{plot_left + plot_w}" y2="{plot_top + plot_h}" stroke="#24313a"/>')
        parts.append(f'<text x="{plot_left - 5}" y="{plot_top + 4}" text-anchor="end" font-size="10">{top_value:.3g}</text>')
        parts.append(f'<text x="{plot_left - 5}" y="{plot_top + plot_h}" text-anchor="end" font-size="10">0</text>')
        step = plot_w / max(1, len(labels))
        for position, label in enumerate(labels):
            item = stats_by_group.get(label)
            x = plot_left + step * (position + 0.5)
            parts.append(f'<text x="{x:.1f}" y="{plot_top + plot_h + 14}" text-anchor="middle" font-size="10">{_escape(label)}</text>')
            if not item or item["median"] is None:
                continue

            def scale(value: float) -> float:
                return plot_top + plot_h - min(value, top_value) / top_value * plot_h

            parts.append(f'<line x1="{x:.1f}" y1="{scale(item["q1"]):.1f}" x2="{x:.1f}" y2="{scale(item["q3"]):.1f}" stroke="#176b87" stroke-width="3"/>')
            parts.append(f'<circle cx="{x:.1f}" cy="{scale(item["median"]):.1f}" r="5" fill="#c94c4c"/>')
    parts.append(f'<text x="20" y="{height - 8}" font-size="11">Ponto: mediana. Barra: Q1 a Q3. Cada painel tem escala própria.</text>')
    parts.append("</svg>")
    path.write_text("".join(parts) + "\n", encoding="utf-8")


def _describe(factor: str, metric: str, group: str, values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    q1, median, q3 = (float(value) for value in np.percentile(ordered, [25, 50, 75])) if ordered else (None, None, None)
    return {"factor": factor, "metric": metric, "group": group, "n": len(ordered), "median": median, "q1": q1, "q3": q3}


def _extreme_delta(rows: Sequence[dict[str, Any]], factor: str, metric: str) -> float | None:
    if not factor.endswith("_quartile"):
        return None
    high = [value for row in rows if row.get(factor) == "Q4" and (value := _as_number(row.get(metric))) is not None]
    low = [value for row in rows if row.get(factor) == "Q1" and (value := _as_number(row.get(metric))) is not None]
    if not high or not low:
        return None
    return cliffs_delta(high, low)


def _group_order(label: str) -> tuple[int, str]:
    if label in QUARTILE_LABELS:
        return (0, label)
    if label in (OTHER_LANGUAGE, "ausente", ""):
        return (2, label)
    return (1, label)


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _as_number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _format(value: float | None, digits: int = 4) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def _format_p(value: float | None) -> str:
    if value is None:
        return ""
    return "< 0.0001" if value < 0.0001 else f"{value:.4f}"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RQ06: compara metricas DORA entre subgrupos de repositorios.")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = merge_metadata(read_csv(args.metrics), read_csv(args.metadata))
    result = analyze(rows)
    write_outputs(result, args.output)
    significant = sum(1 for item in result["tests"] if item["significant_holm"])
    print(f"RQ06: {result['repository_count']} repositorios, {len(result['tests'])} testes, {significant} significativos apos Holm")
    print(f"Saidas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
