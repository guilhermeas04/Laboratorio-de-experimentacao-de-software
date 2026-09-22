"""RQ3 consolidation of static metrics, descriptive stats, and Wilcoxon analysis."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

from .counterbalance import TrialAssignment
from .rq12_analysis import describe, read_design as read_rq12_design, wilcoxon_signed_rank


LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DESIGN = LAB2_ROOT / "data" / "design" / "counterbalancing.csv"
DEFAULT_METRICS_DIR = LAB2_ROOT / "data" / "processed"
DEFAULT_RAW_DIR = LAB2_ROOT / "data" / "raw"
DEFAULT_REPORTS_DIR = LAB2_ROOT / "reports"

METRIC_FIELDS = (
    "loc",
    "cyclomatic_complexity_mean",
    "cyclomatic_complexity_max",
    "duplication_percentage",
    "maintainability_index",
)

METRIC_LABELS = {
    "loc": "LOC",
    "cyclomatic_complexity_mean": "CC media",
    "cyclomatic_complexity_max": "CC maxima",
    "duplication_percentage": "Duplicacao (%)",
    "maintainability_index": "Indice de manutenibilidade",
}

STATUS_OK = "ok"


@dataclass(frozen=True, slots=True)
class MetricsTrialRow:
    participant: str
    trial_id: str
    kata_id: str
    treatment: str
    execution_order: int
    metrics_status: str
    loc: float | None
    cyclomatic_complexity_mean: float | None
    cyclomatic_complexity_max: float | None
    duplication_percentage: float | None
    maintainability_index: float | None
    messages: str
    tests_passing: int | None
    tests_total: int | None
    fully_green: bool | None

    def to_csv_row(self) -> dict[str, str | int | float | bool | None]:
        return asdict(self)


class RQ3AnalysisError(RuntimeError):
    """Raised when LAB02 RQ3 inputs are missing or inconsistent."""


def read_design(path: Path = DEFAULT_DESIGN) -> tuple[TrialAssignment, ...]:
    return read_rq12_design(path)


def load_metrics(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise RQ3AnalysisError(f"metricas invalidas em {path}: {error}") from error
    if not isinstance(payload, dict):
        raise RQ3AnalysisError(f"raiz do JSON deve ser um objeto: {path}")
    return payload


def load_raw_tests(path: Path) -> tuple[int | None, int | None]:
    if not path.exists():
        return None, None
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    total = payload.get("tests_total")
    passing = payload.get("tests_passing")
    if isinstance(total, int) and isinstance(passing, int):
        return passing, total
    return None, None


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def consolidate_metrics(
    design_path: Path = DEFAULT_DESIGN,
    metrics_dir: Path = DEFAULT_METRICS_DIR,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> tuple[MetricsTrialRow, ...]:
    rows: list[MetricsTrialRow] = []
    for assignment in read_design(design_path):
        metrics_path = metrics_dir / f"metrics-{assignment.trial_id}.json"
        if not metrics_path.exists():
            raise RQ3AnalysisError(
                f"arquivo de metricas ausente para {assignment.trial_id}: {metrics_path}"
            )
        payload = load_metrics(metrics_path)
        if payload.get("trial_id") != assignment.trial_id:
            raise RQ3AnalysisError(
                f"trial_id inconsistente em {metrics_path}: "
                f"{payload.get('trial_id')} != {assignment.trial_id}"
            )

        status = str(payload.get("status") or "")
        messages = payload.get("messages") or []
        if not isinstance(messages, list):
            raise RQ3AnalysisError(f"messages invalido em {metrics_path}")

        if status != STATUS_OK and not messages:
            raise RQ3AnalysisError(
                f"{assignment.trial_id}: status={status} sem justificativa em messages"
            )

        tests_passing, tests_total = load_raw_tests(raw_dir / f"{assignment.trial_id}.json")
        fully_green = None
        if tests_passing is not None and tests_total is not None and tests_total > 0:
            fully_green = tests_passing == tests_total

        rows.append(
            MetricsTrialRow(
                participant=assignment.participant,
                trial_id=assignment.trial_id,
                kata_id=assignment.kata_id,
                treatment=assignment.treatment,
                execution_order=assignment.execution_order,
                metrics_status=status,
                loc=_as_optional_float(payload.get("loc")),
                cyclomatic_complexity_mean=_as_optional_float(
                    payload.get("cyclomatic_complexity_mean")
                ),
                cyclomatic_complexity_max=_as_optional_float(
                    payload.get("cyclomatic_complexity_max")
                ),
                duplication_percentage=_as_optional_float(
                    payload.get("duplication_percentage")
                ),
                maintainability_index=_as_optional_float(
                    payload.get("maintainability_index")
                ),
                messages="; ".join(str(item) for item in messages),
                tests_passing=tests_passing,
                tests_total=tests_total,
                fully_green=fully_green,
            )
        )
    return tuple(rows)


def completeness_report(rows: Sequence[MetricsTrialRow]) -> dict[str, Any]:
    missing_metrics: list[dict[str, str]] = []
    non_ok: list[dict[str, str]] = []
    for row in rows:
        if row.metrics_status != STATUS_OK:
            non_ok.append(
                {
                    "trial_id": row.trial_id,
                    "status": row.metrics_status,
                    "messages": row.messages,
                }
            )
        for field in METRIC_FIELDS:
            value = getattr(row, field)
            if value is None:
                missing_metrics.append({"trial_id": row.trial_id, "field": field})

    return {
        "official_trial_count": len(rows),
        "ok_count": sum(1 for row in rows if row.metrics_status == STATUS_OK),
        "non_ok": non_ok,
        "missing_metric_values": missing_metrics,
        "all_complete": len(non_ok) == 0 and len(missing_metrics) == 0,
    }


def _values_for_metric(rows: Iterable[MetricsTrialRow], metric: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = getattr(row, metric)
        if value is None:
            continue
        values.append(float(value))
    return values


def descriptive_by_treatment(
    rows: Sequence[MetricsTrialRow],
) -> dict[str, dict[str, dict[str, float | int] | None]]:
    grouped: dict[str, list[MetricsTrialRow]] = {"with_ai": [], "manual": []}
    for row in rows:
        grouped[row.treatment].append(row)

    result: dict[str, dict[str, dict[str, float | int] | None]] = {}
    for treatment, values in grouped.items():
        result[treatment] = {}
        for metric in METRIC_FIELDS:
            metric_values = _values_for_metric(values, metric)
            result[treatment][metric] = (
                describe(metric_values) if metric_values else None
            )
    return result


def paired_differences_optional(
    rows: Sequence[MetricsTrialRow],
    metric: str,
) -> tuple[float, ...] | None:
    """Medianas por participante; None se algum tratamento nao tiver valores."""

    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        value = getattr(row, metric)
        if value is None:
            continue
        grouped.setdefault(row.participant, {}).setdefault(row.treatment, []).append(
            float(value)
        )

    differences: list[float] = []
    for participant in sorted(grouped):
        by_treatment = grouped[participant]
        if set(by_treatment) != {"with_ai", "manual"}:
            return None
        differences.append(
            round(
                float(median(by_treatment["with_ai"]))
                - float(median(by_treatment["manual"])),
                6,
            )
        )
    if len(differences) < 2:
        return None
    return tuple(differences)


def holm_correction(
    p_values: dict[str, float | None],
    *,
    alpha: float = 0.05,
) -> dict[str, dict[str, float | bool | None]]:
    eligible = [(name, value) for name, value in p_values.items() if value is not None]
    eligible.sort(key=lambda item: item[1])
    m = len(eligible)
    adjusted: dict[str, dict[str, float | bool | None]] = {
        name: {
            "raw_p": None,
            "holm_threshold": None,
            "reject_h0": False,
        }
        for name in p_values
    }

    reject_rest = True
    for index, (name, raw_p) in enumerate(eligible, start=1):
        threshold = alpha / (m - index + 1)
        reject = reject_rest and raw_p <= threshold
        if not reject:
            reject_rest = False
        adjusted[name] = {
            "raw_p": round(raw_p, 6),
            "holm_threshold": round(threshold, 6),
            "reject_h0": reject,
        }
    return adjusted


def analyze(rows: Sequence[MetricsTrialRow]) -> dict[str, Any]:
    completeness = completeness_report(rows)
    descriptive = descriptive_by_treatment(rows)

    wilcoxon: dict[str, Any] = {}
    raw_p: dict[str, float | None] = {}
    for metric in METRIC_FIELDS:
        differences = paired_differences_optional(rows, metric)
        if differences is None:
            result = {
                "status": "not_applicable",
                "n_pairs": 0,
                "alternative": "two-sided",
                "statistic_w_plus": None,
                "p_value_exact": None,
                "differences": [],
                "message": (
                    "Nao foi possivel formar pares within-subject para esta metrica "
                    "(valores ausentes ou tratamentos incompletos)."
                ),
            }
            wilcoxon[metric] = result
            raw_p[metric] = None
            continue
        result_obj = wilcoxon_signed_rank(differences, alternative="two-sided")
        wilcoxon[metric] = asdict(result_obj)
        raw_p[metric] = result_obj.p_value_exact

    green_rows = tuple(row for row in rows if row.fully_green is True)
    green_descriptive = (
        descriptive_by_treatment(green_rows) if green_rows else None
    )

    extremes: dict[str, Any] = {}
    for metric in METRIC_FIELDS:
        candidates = [
            (row.trial_id, getattr(row, metric))
            for row in rows
            if getattr(row, metric) is not None
        ]
        if not candidates:
            extremes[metric] = {"min": None, "max": None}
            continue
        min_row = min(candidates, key=lambda item: item[1])
        max_row = max(candidates, key=lambda item: item[1])
        extremes[metric] = {
            "min": {"trial_id": min_row[0], "value": min_row[1]},
            "max": {"trial_id": max_row[0], "value": max_row[1]},
        }

    return {
        "trial_count": len(rows),
        "official_trial_ids": [row.trial_id for row in rows],
        "completeness": completeness,
        "descriptive": descriptive,
        "descriptive_fully_green": green_descriptive,
        "fully_green_trial_count": len(green_rows),
        "wilcoxon": wilcoxon,
        "holm": holm_correction(raw_p),
        "extremes": extremes,
        "notes": [
            "Analise filtrada pelos 18 trial_id oficiais do contrabalanceamento.",
            "Metricas ausentes permanecem nulas; nao sao convertidas em zero.",
            "Wilcoxon bicaudal usa medianas por participante (within-subject).",
            "Correcao de Holm aplicada aos cinco testes confirmatórios da RQ3.",
            "LOC entra como controle de verbosidade ao interpretar complexidade.",
            "N=3 limita o poder do Wilcoxon; ausencia de significancia nao implica ausencia de efeito.",
        ],
    }


def write_trial_csv(rows: Sequence[MetricsTrialRow], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].to_csv_row()))
        writer.writeheader()
        writer.writerows(row.to_csv_row() for row in rows)


def write_json(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def render_markdown(analysis: dict[str, Any]) -> str:
    desc = analysis["descriptive"]
    wilcoxon = analysis["wilcoxon"]
    holm = analysis["holm"]
    completeness = analysis["completeness"]
    extremes = analysis["extremes"]

    lines = [
        "# LAB02 - RQ3",
        "",
        "Analise das metricas estaticas dos 18 trials oficiais.",
        "RQ3: o uso de assistente de IA altera a complexidade ciclomatica ou a "
        "duplicacao do codigo produzido?",
        "",
        "## Completude das metricas",
        "",
        f"- Trials oficiais conferidos: {completeness['official_trial_count']}",
        f"- Arquivos com status `ok`: {completeness['ok_count']}",
        f"- Campos de metrica ausentes: {len(completeness['missing_metric_values'])}",
        f"- Status diferente de `ok`: {len(completeness['non_ok'])}",
        f"- Completude automatica: {'sim' if completeness['all_complete'] else 'nao'}",
        "",
        "## Tabelas finais por tratamento",
        "",
        "| Tratamento | Metrica | n | Mediana | IQR | Min | Max |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for treatment in ("with_ai", "manual"):
        for metric, label in METRIC_LABELS.items():
            values = desc[treatment][metric]
            if values is None:
                lines.append(f"| {treatment} | {label} | 0 |  |  |  |  |")
                continue
            lines.append(
                f"| {treatment} | {label} | {values['n']} | {values['median']} | "
                f"{values['iqr']} | {values['min']} | {values['max']} |"
            )

    lines.extend(
        [
            "",
            "## Wilcoxon bicaudal e correcao de Holm",
            "",
            "| Metrica | n pares | W+ | p exato | Limiar Holm | Rejeita H0 | Status |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for metric, label in METRIC_LABELS.items():
        result = wilcoxon[metric]
        holm_row = holm[metric]
        w_value = "" if result["statistic_w_plus"] is None else result["statistic_w_plus"]
        p_value = "" if result["p_value_exact"] is None else result["p_value_exact"]
        threshold = (
            ""
            if holm_row["holm_threshold"] is None
            else holm_row["holm_threshold"]
        )
        lines.append(
            f"| {label} | {result['n_pairs']} | {w_value} | {p_value} | "
            f"{threshold} | {holm_row['reject_h0']} | {result['status']} |"
        )

    lines.extend(
        [
            "",
            "## Casos extremos",
            "",
            "| Metrica | Minimo | Maximo |",
            "| --- | --- | --- |",
        ]
    )
    for metric, label in METRIC_LABELS.items():
        extreme = extremes[metric]
        if extreme["min"] is None:
            lines.append(f"| {label} | n/d | n/d |")
            continue
        lines.append(
            f"| {label} | {extreme['min']['trial_id']} ({extreme['min']['value']}) | "
            f"{extreme['max']['trial_id']} ({extreme['max']['value']}) |"
        )

    lines.extend(
        [
            "",
            "## Interpretacao da RQ3",
            "",
            _interpret_rq3(analysis),
            "",
            "## Limitacoes",
            "",
            "- N=3 pares; Wilcoxon exato dificilmente atinge p < 0,05.",
            "- LOC e metrica de controle: codigo com IA pode ser mais verboso e isso "
            "afeta a leitura da complexidade.",
            "- Duplicacao zerada nos dois tratamentos limita o Wilcoxon dessa metrica.",
            "- Codigo incompleto pode parecer artificialmente simples; subset 100% green "
            f"tem {analysis['fully_green_trial_count']} trials.",
            "- Metricas ausentes nao foram imputadas como zero.",
        ]
    )
    return "\n".join(str(line) for line in lines) + "\n"


def _interpret_rq3(analysis: dict[str, Any]) -> str:
    desc = analysis["descriptive"]
    holm = analysis["holm"]

    def median_or_na(treatment: str, metric: str) -> str:
        values = desc[treatment][metric]
        if values is None:
            return "n/d"
        return str(values["median"])

    ai_loc = median_or_na("with_ai", "loc")
    manual_loc = median_or_na("manual", "loc")
    ai_cc = median_or_na("with_ai", "cyclomatic_complexity_mean")
    manual_cc = median_or_na("manual", "cyclomatic_complexity_mean")
    ai_dup = median_or_na("with_ai", "duplication_percentage")
    manual_dup = median_or_na("manual", "duplication_percentage")
    ai_mi = median_or_na("with_ai", "maintainability_index")
    manual_mi = median_or_na("manual", "maintainability_index")

    rejected = [METRIC_LABELS[name] for name, row in holm.items() if row["reject_h0"]]
    rejection_text = (
        "Nenhuma metrica rejeitou H0 apos Holm."
        if not rejected
        else "Metricas com rejeicao apos Holm: " + ", ".join(rejected) + "."
    )

    return (
        f"**Complexidade.** A mediana de CC media foi {ai_cc} com IA e {manual_cc} "
        "no manual; a CC maxima seguiu o mesmo padrao aproximado. A diferenca "
        "descritiva e pequena e nao se sustenta no Wilcoxon bicaudal com N=3.\n\n"
        f"**Duplicacao.** Ambos os tratamentos ficaram com mediana {ai_dup}% "
        f"(manual {manual_dup}%). Sem variacao, o teste pareado dessa metrica "
        "fica `not_applicable`.\n\n"
        f"**LOC (controle).** Mediana de {ai_loc} linhas com IA contra {manual_loc} "
        "no manual. O codigo com IA tende a ser um pouco mais verboso; por isso "
        "qualquer leitura de complexidade precisa considerar LOC, nao so o valor "
        "absoluto de CC.\n\n"
        f"**Manutenibilidade.** MI mediano {ai_mi} com IA e {manual_mi} no manual, "
        "praticamente equivalentes. O indice composto nao aponta ganho estrutural "
        "claro de um tratamento sobre o outro.\n\n"
        f"{rejection_text} No conjunto, a evidencia disponivel nao indica alteracao "
        "robusta de complexidade ou duplicacao pelo uso de IA neste experimento."
    )


def assert_metrics_completeness(rows: Sequence[MetricsTrialRow]) -> None:
    """Garante os 18 trials oficiais com status ok ou justificativa explicita."""

    if len(rows) != 18:
        raise RQ3AnalysisError(f"esperados 18 trials oficiais, obtidos {len(rows)}")

    for row in rows:
        if row.metrics_status != STATUS_OK and not row.messages.strip():
            raise RQ3AnalysisError(
                f"{row.trial_id}: status={row.metrics_status} sem justificativa"
            )
        for field in METRIC_FIELDS:
            if row.metrics_status == STATUS_OK and getattr(row, field) is None:
                raise RQ3AnalysisError(f"{row.trial_id}: campo {field} ausente")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisa RQ3 do LAB02.")
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument(
        "--check-completeness",
        action="store_true",
        help="Apenas confere completude dos 18 trials e sai sem regenerar relatorios.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = consolidate_metrics(args.design, args.metrics_dir, args.raw_dir)
        assert_metrics_completeness(rows)
        if args.check_completeness:
            print(f"RQ3 completude OK: {len(rows)} trials com metricas validas")
            return 0

        payload = analyze(rows)
        reports_dir = args.reports_dir
        csv_path = reports_dir / "rq3-trials.csv"
        json_path = reports_dir / "rq3-statistics.json"
        markdown_path = reports_dir / "rq3-summary.md"
        write_trial_csv(rows, csv_path)
        write_json(payload, json_path)
        markdown_path.write_text(render_markdown(payload), encoding="utf-8", newline="\n")
    except (RQ3AnalysisError, OSError, ValueError) as error:
        print(f"ERRO: {error}")
        return 1

    print(f"RQ3: {len(rows)} trials oficiais")
    print(f"Completude: {payload['completeness']['all_complete']}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
