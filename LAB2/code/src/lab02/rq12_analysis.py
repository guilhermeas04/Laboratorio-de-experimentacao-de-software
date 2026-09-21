"""RQ1/RQ2 consolidation, descriptive statistics, and Wilcoxon analysis."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

from .counterbalance import TrialAssignment
from .trial_record import MAX_TRIAL_SECONDS, TrialRecord, TrialValidationError


LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DESIGN = LAB2_ROOT / "data" / "design" / "counterbalancing.csv"
DEFAULT_RAW_DIR = LAB2_ROOT / "data" / "raw"
DEFAULT_REPORTS_DIR = LAB2_ROOT / "reports"


@dataclass(frozen=True, slots=True)
class TrialRow:
    participant: str
    record_participant: str
    trial_id: str
    kata_id: str
    treatment: str
    execution_order: int
    elapsed_seconds: float
    censored: bool
    time_to_green_seconds: float | None
    tests_total: int
    tests_passing: int
    tests_failing: int
    success_rate: float

    def to_csv_row(self) -> dict[str, str | int | float | bool | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    status: str
    n_pairs: int
    alternative: str
    statistic_w_plus: float | None
    p_value_exact: float | None
    differences: tuple[float, ...]
    message: str


class RQ12AnalysisError(RuntimeError):
    """Raised when LAB02 RQ1/RQ2 inputs are missing or inconsistent."""


def read_design(path: Path = DEFAULT_DESIGN) -> tuple[TrialAssignment, ...]:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            return tuple(
                TrialAssignment(
                    participant=row["participant"],
                    kata_id=row["kata_id"],
                    treatment=row["treatment"],
                    execution_order=int(row["execution_order"]),
                )
                for row in csv.DictReader(file)
            )
    except (OSError, UnicodeError, csv.Error, KeyError, TypeError, ValueError) as error:
        raise RQ12AnalysisError(f"design invalido: {error}") from error


def load_record(path: Path) -> TrialRecord:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise TrialValidationError("raiz do JSON deve ser um objeto")
        return TrialRecord.from_mapping(payload)
    except (OSError, json.JSONDecodeError, TrialValidationError) as error:
        raise RQ12AnalysisError(f"registro invalido em {path}: {error}") from error


def consolidate_trials(
    design_path: Path = DEFAULT_DESIGN,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> tuple[TrialRow, ...]:
    rows: list[TrialRow] = []
    for assignment in read_design(design_path):
        path = raw_dir / f"{assignment.trial_id}.json"
        record = load_record(path)
        _validate_record_matches_assignment(record, assignment)
        rows.append(
            TrialRow(
                participant=assignment.participant,
                record_participant=record.participant,
                trial_id=assignment.trial_id,
                kata_id=assignment.kata_id,
                treatment=assignment.treatment,
                execution_order=assignment.execution_order,
                elapsed_seconds=record.elapsed_seconds,
                censored=record.censored,
                time_to_green_seconds=record.time_to_green_seconds,
                tests_total=record.tests_total,
                tests_passing=record.tests_passing,
                tests_failing=record.tests_total - record.tests_passing,
                success_rate=record.success_rate,
            )
        )
    return tuple(rows)


def _validate_record_matches_assignment(record: TrialRecord, assignment: TrialAssignment) -> None:
    expected = {
        "trial_id": assignment.trial_id,
        "kata_id": assignment.kata_id,
        "treatment": assignment.treatment,
        "execution_order": assignment.execution_order,
    }
    actual = {
        "trial_id": record.trial_id,
        "kata_id": record.kata_id,
        "treatment": record.treatment,
        "execution_order": record.execution_order,
    }
    if actual != expected:
        raise RQ12AnalysisError(
            f"registro {assignment.trial_id} nao corresponde ao design: {actual} != {expected}"
        )
    if record.elapsed_seconds > MAX_TRIAL_SECONDS:
        raise RQ12AnalysisError(f"{assignment.trial_id} excede o time-box")


def descriptive_by_treatment(rows: Iterable[TrialRow]) -> dict[str, dict[str, dict[str, float | int]]]:
    grouped: dict[str, list[TrialRow]] = {"with_ai": [], "manual": []}
    for row in rows:
        grouped[row.treatment].append(row)

    result: dict[str, dict[str, dict[str, float | int]]] = {}
    for treatment, values in grouped.items():
        result[treatment] = {
            "elapsed_seconds": describe([row.elapsed_seconds for row in values]),
            "success_rate": describe([row.success_rate for row in values]),
            "tests_failing": describe([row.tests_failing for row in values]),
        }
    return result


def describe(values: Sequence[float | int]) -> dict[str, float | int]:
    if not values:
        raise ValueError("valores vazios")
    sorted_values = sorted(float(value) for value in values)
    q1, q3 = quartiles(sorted_values)
    return {
        "n": len(sorted_values),
        "min": round(sorted_values[0], 6),
        "q1": round(q1, 6),
        "median": round(float(median(sorted_values)), 6),
        "q3": round(q3, 6),
        "iqr": round(q3 - q1, 6),
        "max": round(sorted_values[-1], 6),
    }


def quartiles(sorted_values: Sequence[float]) -> tuple[float, float]:
    if not sorted_values:
        raise ValueError("valores vazios")
    if len(sorted_values) == 1:
        return sorted_values[0], sorted_values[0]
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        lower = sorted_values[:midpoint]
        upper = sorted_values[midpoint:]
    else:
        lower = sorted_values[:midpoint]
        upper = sorted_values[midpoint + 1 :]
    return float(median(lower)), float(median(upper))


def participant_medians(rows: Iterable[TrialRow], metric: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        grouped.setdefault(row.participant, {}).setdefault(row.treatment, []).append(
            float(getattr(row, metric))
        )
    medians: dict[str, dict[str, float]] = {}
    for participant, by_treatment in grouped.items():
        if set(by_treatment) != {"with_ai", "manual"}:
            raise RQ12AnalysisError(f"{participant} nao possui ambos os tratamentos")
        medians[participant] = {
            treatment: float(median(values)) for treatment, values in by_treatment.items()
        }
    return medians


def paired_differences(rows: Iterable[TrialRow], metric: str) -> tuple[float, ...]:
    medians = participant_medians(rows, metric)
    return tuple(
        round(values["with_ai"] - values["manual"], 6)
        for _, values in sorted(medians.items())
    )


def wilcoxon_signed_rank(
    differences: Sequence[float],
    *,
    alternative: str = "less",
) -> WilcoxonResult:
    if alternative not in {"less", "greater", "two-sided"}:
        raise ValueError("alternative invalida")
    non_zero = [float(value) for value in differences if value != 0]
    if not non_zero:
        return WilcoxonResult(
            status="not_applicable",
            n_pairs=0,
            alternative=alternative,
            statistic_w_plus=None,
            p_value_exact=None,
            differences=tuple(differences),
            message="Todas as diferencas pareadas sao zero; Wilcoxon nao e informativo.",
        )

    ranks = _average_abs_ranks(non_zero)
    observed_w_plus = sum(rank for value, rank in zip(non_zero, ranks) if value > 0)
    all_w_plus = []
    for signs in itertools.product((-1, 1), repeat=len(non_zero)):
        all_w_plus.append(sum(rank for sign, rank in zip(signs, ranks) if sign > 0))

    if alternative == "less":
        p_value = sum(value <= observed_w_plus for value in all_w_plus) / len(all_w_plus)
    elif alternative == "greater":
        p_value = sum(value >= observed_w_plus for value in all_w_plus) / len(all_w_plus)
    else:
        total_rank = sum(ranks)
        observed_tail = min(observed_w_plus, total_rank - observed_w_plus)
        p_value = min(
            1.0,
            2 * sum(min(value, total_rank - value) <= observed_tail for value in all_w_plus) / len(all_w_plus),
        )

    return WilcoxonResult(
        status="ok",
        n_pairs=len(non_zero),
        alternative=alternative,
        statistic_w_plus=round(observed_w_plus, 6),
        p_value_exact=round(p_value, 6),
        differences=tuple(differences),
        message=(
            "Teste exato sobre medianas por participante. "
            "Com tres pares, o menor p-valor unilateral possivel e 0.125."
        ),
    )


def _average_abs_ranks(values: Sequence[float]) -> tuple[float, ...]:
    indexed = sorted(enumerate(abs(value) for value in values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1
        average_rank = (position + 1 + end) / 2
        for original_index, _ in indexed[position:end]:
            ranks[original_index] = average_rank
        position = end
    return tuple(ranks)


def analyze(rows: Sequence[TrialRow]) -> dict[str, Any]:
    rq1_differences = paired_differences(rows, "elapsed_seconds")
    rq2_success_differences = paired_differences(rows, "success_rate")
    rq2_defect_differences = paired_differences(rows, "tests_failing")
    return {
        "trial_count": len(rows),
        "official_trial_ids": [row.trial_id for row in rows],
        "descriptive": descriptive_by_treatment(rows),
        "paired_medians": {
            "elapsed_seconds": participant_medians(rows, "elapsed_seconds"),
            "success_rate": participant_medians(rows, "success_rate"),
            "tests_failing": participant_medians(rows, "tests_failing"),
        },
        "wilcoxon": {
            "rq1_elapsed_seconds": asdict(
                wilcoxon_signed_rank(rq1_differences, alternative="less")
            ),
            "rq2_success_rate": asdict(
                wilcoxon_signed_rank(rq2_success_differences, alternative="greater")
            ),
            "rq2_tests_failing": asdict(
                wilcoxon_signed_rank(rq2_defect_differences, alternative="less")
            ),
        },
        "notes": [
            "Analise filtrada pelos 18 trial_id oficiais do contrabalanceamento.",
            "Trials censurados sao mantidos com elapsed_seconds registrado no time-box.",
            "Wilcoxon usa medianas por participante, nao pares mesma kata/mesmo participante.",
            "N=3 limita conclusoes inferenciais; interpretar junto com estatisticas descritivas.",
        ],
    }


def write_trial_csv(rows: Sequence[TrialRow], output: Path) -> None:
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
    lines = [
        "# LAB02 - RQ1/RQ2",
        "",
        "Analise gerada a partir dos 18 trials oficiais do contrabalanceamento.",
        "O arquivo `P01-K01-MANUAL.json` nao faz parte do desenho oficial e foi ignorado.",
        "",
        "## Estatisticas descritivas",
        "",
        "| Tratamento | Metrica | n | Mediana | IQR | Min | Max |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "elapsed_seconds": "Tempo (s)",
        "success_rate": "Taxa de sucesso (%)",
        "tests_failing": "Testes falhando",
    }
    for treatment in ("with_ai", "manual"):
        for metric, label in labels.items():
            values = desc[treatment][metric]
            lines.append(
                f"| {treatment} | {label} | {values['n']} | {values['median']} | "
                f"{values['iqr']} | {values['min']} | {values['max']} |"
            )
    lines.extend(
        [
            "",
            "## Testes de Wilcoxon",
            "",
            "| RQ | Metrica pareada | Alternativa | n | W+ | p exato | Status |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    rows = (
        ("RQ1", "Mediana de tempo com IA - manual", "with_ai < manual", "rq1_elapsed_seconds"),
        ("RQ2", "Mediana de taxa de sucesso com IA - manual", "with_ai > manual", "rq2_success_rate"),
        ("RQ2", "Mediana de testes falhando com IA - manual", "with_ai < manual", "rq2_tests_failing"),
    )
    for rq, metric, alternative, key in rows:
        result = wilcoxon[key]
        w_value = "" if result["statistic_w_plus"] is None else result["statistic_w_plus"]
        p_value = "" if result["p_value_exact"] is None else result["p_value_exact"]
        lines.append(
            f"| {rq} | {metric} | {alternative} | {result['n_pairs']} | "
            f"{w_value} | {p_value} | {result['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretacao curta",
            "",
            _interpret_rq1(analysis),
            "",
            _interpret_rq2(analysis),
            "",
            "## Limitacoes",
            "",
            "- O desenho possui apenas tres participantes; resultados inferenciais devem ser tratados como exploratorios.",
            "- Com tres pares, o menor p-valor unilateral possivel no Wilcoxon exato e 0.125.",
            "- A comparacao pareada usa medianas por participante para manter o desenho within-subject.",
        ]
    )
    return "\n".join(str(line) for line in lines) + "\n"


def _interpret_rq1(analysis: dict[str, Any]) -> str:
    desc = analysis["descriptive"]
    ai = desc["with_ai"]["elapsed_seconds"]["median"]
    manual = desc["manual"]["elapsed_seconds"]["median"]
    result = analysis["wilcoxon"]["rq1_elapsed_seconds"]
    direction = "menor" if ai < manual else "maior ou igual"
    return (
        f"**RQ1.** A mediana de tempo com IA foi {ai}s e a manual foi {manual}s; "
        f"descritivamente, o tempo com IA foi {direction}. "
        f"O Wilcoxon exato retornou status `{result['status']}` e p={result['p_value_exact']}; "
        "com N=3, isso nao deve ser apresentado como evidencia conclusiva."
    )


def _interpret_rq2(analysis: dict[str, Any]) -> str:
    desc = analysis["descriptive"]
    ai_success = desc["with_ai"]["success_rate"]["median"]
    manual_success = desc["manual"]["success_rate"]["median"]
    defects = analysis["wilcoxon"]["rq2_tests_failing"]
    return (
        f"**RQ2.** A mediana de taxa de sucesso foi {ai_success}% com IA e "
        f"{manual_success}% no manual. Os testes falhando tiveram status "
        f"`{defects['status']}` no Wilcoxon, indicando que empates ou ausencia de defeitos "
        "limitam a comparacao inferencial."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisa RQ1/RQ2 do LAB02.")
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = consolidate_trials(args.design, args.raw_dir)
        payload = analyze(rows)
        reports_dir = args.reports_dir
        csv_path = reports_dir / "rq12-trials.csv"
        json_path = reports_dir / "rq12-statistics.json"
        markdown_path = reports_dir / "rq12-summary.md"
        write_trial_csv(rows, csv_path)
        write_json(payload, json_path)
        markdown_path.write_text(render_markdown(payload), encoding="utf-8", newline="\n")
    except (RQ12AnalysisError, OSError, ValueError) as error:
        print(f"ERRO: {error}")
        return 1

    print(f"RQ1/RQ2: {len(rows)} trials oficiais")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
