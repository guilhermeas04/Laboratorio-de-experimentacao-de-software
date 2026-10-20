"""RQ07: sensibilidade da classificação DORA às definições operacionais.

Executa apenas com a biblioteca padrão. O dataset S02 ainda não contém uma
variante de tags; por isso o relatório registra essa limitação em vez de
inventar valores. As três combinações executáveis usam as variantes presentes.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from itertools import combinations
from pathlib import Path

ORDER = ("Low", "Medium", "High", "Elite")
SCORE = {name: i + 1 for i, name in enumerate(ORDER)}

VARIANTS = {
    "C1_reference": {"deploy": "release_count", "lead": "lead_time_by_release_days", "cfr": "cfr_ci"},
    "C2_commit_cfr_b": {"deploy": "release_count", "lead": "lead_time_by_commit_days", "cfr": "cfr_b"},
    "C3_release_cfr_b": {"deploy": "release_count", "lead": "lead_time_by_release_days", "cfr": "cfr_b"},
}


def _number(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        return None
    try:
        value = float(value)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def classify(value: float | None, thresholds: tuple[float, float, float], *, reverse: bool = False) -> str | None:
    if value is None:
        return None
    if reverse:
        if value < thresholds[0]: return "Elite"
        if value < thresholds[1]: return "High"
        if value < thresholds[2]: return "Medium"
        return "Low"
    if value >= thresholds[2]: return "Elite"
    if value >= thresholds[1]: return "High"
    if value >= thresholds[0]: return "Medium"
    return "Low"


def classify_row(row: dict[str, str], variant: dict[str, str]) -> str | None:
    parts = (
        classify(_number(row, variant["deploy"]), (1 / 4.345, 1.0, 7.0)),
        classify(_number(row, variant["lead"]), (1.0, 7.0, 30.0), reverse=True),
        classify(_number(row, variant["cfr"]), (0.15, 0.30, 0.45), reverse=True),
        classify(_number(row, "recovery_median_hours"), (1.0, 24.0, 168.0), reverse=True),
    )
    if any(part is None for part in parts):
        return None
    ordered = sorted(SCORE[part] for part in parts)
    median_floor = ordered[1] if len(ordered) == 4 else ordered[len(ordered) // 2]
    return ORDER[median_floor - 1]


def weighted_kappa(left: list[str], right: list[str]) -> float | None:
    pairs = [(SCORE[a], SCORE[b]) for a, b in zip(left, right) if a and b]
    if not pairs:
        return None
    n = len(pairs)
    k = len(ORDER)
    observed = sum(1 - abs(a - b) / (k - 1) for a, b in pairs) / n
    left_counts = [sum(a == i for a, _ in pairs) for i in range(1, k + 1)]
    right_counts = [sum(b == i for _, b in pairs) for i in range(1, k + 1)]
    expected = sum((left_counts[i] * right_counts[j] / n**2) * (1 - abs(i + 1 - (j + 1)) / (k - 1)) for i in range(k) for j in range(k))
    return None if expected == 1 else (observed - expected) / (1 - expected)


def analyze(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    labels = {name: [classify_row(row, spec) for row in rows] for name, spec in VARIANTS.items()}
    summary = []
    for name, values in labels.items():
        summary.append({"variant": name, "n_total": str(len(rows)), "n_classified": str(sum(value is not None for value in values)), "n_missing": str(sum(value is None for value in values))})
    comparisons = []
    for left, right in combinations(VARIANTS, 2):
        pairs = [(a, b) for a, b in zip(labels[left], labels[right]) if a and b]
        changed = sum(a != b for a, b in pairs)
        comparisons.append({"left": left, "right": right, "n_compared": str(len(pairs)), "n_changed": str(changed), "changed_pct": "" if not pairs else f"{100 * changed / len(pairs):.4f}", "weighted_cohen_kappa": "" if not pairs else f"{weighted_kappa([a for a, _ in pairs], [b for _, b in pairs]):.6f}"})
    return summary, comparisons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/processed/datasets/s02_metrics.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/rq07"))
    args = parser.parse_args()
    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary, comparisons = analyze(rows)
    for filename, data in (("variant_summary.csv", summary), ("pairwise_comparisons.csv", comparisons)):
        with (args.output_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader(); writer.writerows(data)
    report = {"variants": VARIANTS, "summary": summary, "comparisons": comparisons, "limitation": "S02 does not contain tag-based metric columns; release-versus-tag sensitivity requires a separate tag collection."}
    (args.output_dir / "rq07_sensitivity.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output_dir / "README.md").write_text("# RQ07\n\nA análise foi executada sobre os 300 repositórios do dataset S02. Foram comparadas três combinações reproduzíveis com releases, lead time por release ou commit e CFR(a) ou CFR(b). A variante baseada em tags não está presente no dataset coletado; nenhum valor de tag foi inferido. Essa ausência deve ser reportada como limitação da coleta, e não como dado negativo ou zero.\n", encoding="utf-8")
    (args.output_dir / "rq07_report.md").write_text("""# RQ07 — análise de sensibilidade\n\n## Escopo\n\nA análise foi executada sobre os 300 repositórios elegíveis da amostra final da Sprint 2.\n\n## Variantes observadas\n\n| Variante | Unidade de deploy | Lead time | CFR |\n|---|---|---|---|\n| C1 | release | por release | CFR(a) |\n| C2 | release | por commit | CFR(b) |\n| C3 | release | por release | CFR(b) |\n\nPara cada repositório, a categoria geral é a mediana, arredondada para baixo, das quatro categorias métricas: frequência, lead time, CFR e recuperação. Casos sem alguma métrica necessária permanecem sem classificação e são excluídos somente do par correspondente.\n\n## Resultados\n\nOs valores completos estão em `pairwise_comparisons.csv` e `variant_summary.csv`. A matriz de transição e o percentual de mudança devem ser interpretados junto com `n_compared`, que informa quantos repositórios tinham classificação disponível nas duas variantes.\n\n## Limitação\n\nA coleta da variante baseada em tags não foi concluída para os 300 repositórios. O dataset S02 não contém contagem ou métricas derivadas de tags; portanto, não é possível afirmar uma comparação release versus tag. Nenhum valor foi simulado ou inferido.\n""", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
