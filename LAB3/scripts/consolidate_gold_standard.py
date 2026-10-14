"""Alinha rótulos independentes e calcula concordância de Fleiss."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "data" / "interim" / "manual_validation"
OUT = ROOT / "data" / "processed" / "gold_standard"
FILES = {
    "guilherme": VALIDATION / "guilherme_labels.csv",
    "amanda": VALIDATION / "amanda_labels.csv",
    "pedro": VALIDATION / "pedro_labels.csv",
}


def read_labels(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {(row["repository"], row.get("release_id", "")): row for row in csv.DictReader(handle)}


def fleiss_kappa(labels: list[list[str]]) -> dict[str, float | int | list[str]]:
    if not labels or len({len(row) for row in labels}) != 1 or len(labels[0]) < 2:
        raise ValueError("sao necessarios itens com o mesmo numero de avaliadores")
    categories = sorted({label for row in labels for label in row})
    n = len(labels[0])
    proportions = []
    for row in labels:
        counts = Counter(row)
        proportions.append(sum(counts[c] * (counts[c] - 1) for c in categories) / (n * (n - 1)))
    p_bar = sum(proportions) / len(proportions)
    p_categories = {
        category: sum(row.count(category) for row in labels) / (len(labels) * n)
        for category in categories
    }
    p_e = sum(value * value for value in p_categories.values())
    kappa = (p_bar - p_e) / (1 - p_e) if p_e < 1 else 1.0
    return {"n_items": len(labels), "n_raters": n, "categories": categories,
            "agreement_mean": p_bar, "chance_agreement": p_e, "fleiss_kappa": kappa}


def main() -> None:
    data = {reviewer: read_labels(path) for reviewer, path in FILES.items()}
    keys = set(data["guilherme"])
    if any(set(rows) != keys for rows in data.values()):
        raise RuntimeError("os arquivos nao possuem a mesma amostra/repositorio-release")
    reviewers = tuple(data)
    rows = []
    for key in sorted(keys):
        labels = [data[reviewer][key].get("label", "").strip() for reviewer in reviewers]
        counts = Counter(labels)
        top = counts.most_common()
        consensus = top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else "sem_consenso"
        rows.append({"repository": key[0], "release_id": key[1],
                     "tag_name": data[reviewers[0]][key].get("tag_name", ""),
                     **{f"label_{reviewer}": data[reviewer][key].get("label", "") for reviewer in reviewers},
                     "consensus_label": consensus, "agreement_count": top[0][1],
                     "consensus_status": "unanimous" if len(counts) == 1 else ("majority" if consensus != "sem_consenso" else "divergent")})

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (OUT / "gold_standard_consensus.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    disagreements = [row for row in rows if row["consensus_status"] != "unanimous"]
    with (OUT / "gold_standard_disagreements.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(disagreements)

    all_stats = fleiss_kappa([[row[f"label_{reviewer}"] for reviewer in reviewers] for row in rows])
    evaluable = [row for row in rows if row["label_guilherme"] != "sem_release" and row["label_amanda"] != "sem_release" and row["label_pedro"] != "sem_release"]
    evaluable_stats = fleiss_kappa([[row[f"label_{reviewer}"] for reviewer in reviewers] for row in evaluable]) if evaluable else None
    report = {"reviewers": list(reviewers), "sample_size": len(rows),
              "unanimous_items": sum(row["consensus_status"] == "unanimous" for row in rows),
              "majority_items": sum(row["consensus_status"] == "majority" for row in rows),
              "without_consensus": sum(row["consensus_status"] == "divergent" for row in rows), "all_items": all_stats,
              "evaluable_without_sem_release": evaluable_stats,
              "excluded_label": "sem_release"}
    (OUT / "fleiss_kappa.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"itens={len(rows)}; unanimidade={report['unanimous_items']}; divergencias={len(disagreements)}; kappa={all_stats['fleiss_kappa']:.4f}")


if __name__ == "__main__":
    main()
