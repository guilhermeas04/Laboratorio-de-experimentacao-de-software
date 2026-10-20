"""RQ05: correlacao de Spearman entre deployment frequency e CFR (a) e (b)."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from scipy import stats

LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_metrics.csv"
DEFAULT_OUTPUT = LAB3_ROOT / "reports" / "rq05"
FREQUENCY_COLUMN = "deployment_frequency_per_week"
VARIANTS = (
    ("cfr_a", "cfr_ci", "CFR(a) - falhas de CI"),
    ("cfr_b", "cfr_b", "CFR(b) - release corretiva em ate 7 dias"),
)
ALPHA = 0.05
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 120


@dataclass(frozen=True)
class CorrelationResult:
    variant: str
    x_column: str
    y_column: str
    n_total: int
    n_used: int
    n_missing: int
    rho: float | None
    p_value: float | None
    ci95_low: float | None
    ci95_high: float | None
    strength: str
    direction: str
    significant: bool | None
    note: str


def read_dataset(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "repository" not in rows[0]:
        raise ValueError(f"dataset invalido ou vazio: {path}")
    return rows


def paired_values(
    rows: Sequence[dict[str, Any]], x_column: str, y_column: str
) -> tuple[list[float], list[float], list[dict[str, str]]]:
    """Pares completos. Linha com valor ausente sai da conta e e registrada."""

    xs: list[float] = []
    ys: list[float] = []
    missing: list[dict[str, str]] = []
    for row in rows:
        x = _as_number(row.get(x_column))
        y = _as_number(row.get(y_column))
        if x is None or y is None:
            absent = [column for column, value in ((x_column, x), (y_column, y)) if value is None]
            missing.append({"repository": str(row.get("repository") or ""), "missing_columns": ";".join(absent)})
            continue
        xs.append(x)
        ys.append(y)
    return xs, ys, missing


def spearman(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float | None, float | None, float | None, float | None, str]:
    """Retorna rho, p-valor bicaudal e IC 95% por bootstrap percentil."""

    if len(xs) != len(ys):
        raise ValueError("as duas series precisam ter o mesmo tamanho")
    if len(xs) < 3:
        return None, None, None, None, "menos de 3 pares completos"
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, None, None, None, "uma das series e constante"
    result = stats.spearmanr(xs, ys)
    rho, p_value = float(result.statistic), float(result.pvalue)
    x_array, y_array = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    generator = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(resamples):
        index = generator.integers(0, len(x_array), len(x_array))
        sample_x, sample_y = x_array[index], y_array[index]
        if np.unique(sample_x).size < 2 or np.unique(sample_y).size < 2:
            continue
        boot.append(float(stats.spearmanr(sample_x, sample_y).statistic))
    if not boot:
        return rho, p_value, None, None, ""
    low, high = np.percentile(boot, [2.5, 97.5])
    return rho, p_value, float(low), float(high), ""


def strength_label(rho: float | None) -> str:
    """Faixas usuais de |rho|: < 0,1 desprezivel; < 0,3 fraca; < 0,5 moderada."""

    if rho is None:
        return "indefinida"
    magnitude = abs(rho)
    if magnitude < 0.1:
        return "desprezivel"
    if magnitude < 0.3:
        return "fraca"
    if magnitude < 0.5:
        return "moderada"
    return "forte"


def correlate_variant(rows: Sequence[dict[str, Any]], variant: str, y_column: str) -> tuple[CorrelationResult, list[float], list[float], list[dict[str, str]]]:
    xs, ys, missing = paired_values(rows, FREQUENCY_COLUMN, y_column)
    rho, p_value, low, high, note = spearman(xs, ys)
    direction = "indefinida" if rho is None else ("positiva" if rho > 0 else "negativa" if rho < 0 else "nula")
    result = CorrelationResult(
        variant=variant,
        x_column=FREQUENCY_COLUMN,
        y_column=y_column,
        n_total=len(rows),
        n_used=len(xs),
        n_missing=len(missing),
        rho=rho,
        p_value=p_value,
        ci95_low=low,
        ci95_high=high,
        strength=strength_label(rho),
        direction=direction,
        significant=None if p_value is None else p_value < ALPHA,
        note=note,
    )
    return result, xs, ys, missing


def analyze(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    correlations = []
    series = {}
    missing_rows = []
    for variant, column, _title in VARIANTS:
        result, xs, ys, missing = correlate_variant(rows, variant, column)
        correlations.append(asdict(result))
        series[variant] = {"x": xs, "y": ys}
        missing_rows.extend({"variant": variant, **item} for item in missing)
    return {
        "issue": 120,
        "repository_count": len(rows),
        "method": {
            "test": "Spearman (scipy.stats.spearmanr), bicaudal, alfa 0,05",
            "ties": "postos medios; a frequencia tem muitos empates porque e release_count dividido por 365/7",
            "missing": "par incompleto sai da conta; ausente nao vira zero",
            "confidence_interval": f"bootstrap percentil, {BOOTSTRAP_RESAMPLES} reamostras, semente {BOOTSTRAP_SEED}",
            "strength": "|rho| < 0,1 desprezivel; < 0,3 fraca; < 0,5 moderada; >= 0,5 forte",
        },
        "correlations": correlations,
        "series": series,
        "missing": missing_rows,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {key: value for key, value in result.items() if key != "series"}
    (output_dir / "rq05-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(output_dir / "rq05-spearman.csv", result["correlations"])
    _write_csv(output_dir / "rq05-missing.csv", result["missing"], ("variant", "repository", "missing_columns"))
    _write_markdown(result, output_dir / "rq05-summary.md")
    titles = {variant: title for variant, _column, title in VARIANTS}
    by_variant = {item["variant"]: item for item in result["correlations"]}
    for variant, points in result["series"].items():
        _write_scatter(
            output_dir / f"rq05-frequency-vs-{variant.replace('_', '-')}.svg",
            f"RQ05 - deployment frequency x {titles[variant].split(' - ')[0]}",
            titles[variant],
            points["x"],
            points["y"],
            by_variant[variant],
        )


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# RQ05 - Frequência de deploy e taxa de falha",
        "",
        f"Repositórios no dataset: **{result['repository_count']}**. Correlação de Spearman entre `{FREQUENCY_COLUMN}` e cada variante de CFR.",
        "",
        "| Variante | n usado | Ausentes | rho | IC 95% | p-valor | Força | Direção |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ]
    for item in result["correlations"]:
        interval = "" if item["ci95_low"] is None else f"[{item['ci95_low']:.3f}; {item['ci95_high']:.3f}]"
        lines.append(
            f"| {item['variant']} | {item['n_used']} | {item['n_missing']} | {_format(item['rho'], 3)} | {interval} | {_format_p(item['p_value'])} | {item['strength']} | {item['direction']} |"
        )
    lines.extend(
        [
            "",
            "## Escolha estatística",
            "",
            "- Spearman mede associação monotônica pelos postos. Não exige normalidade nem relação linear. As duas métricas são assimétricas e o CFR fica preso entre 0 e 1.",
            "- Empates recebem posto médio. A frequência tem poucos valores distintos, porque é a contagem de releases dividida por 365/7.",
            "- O p-valor é bicaudal, com alfa 0,05. O intervalo de confiança vem de bootstrap percentil com semente fixa.",
            "- Par com valor ausente sai da conta. Ausente não vira zero. A lista está em `rq05-missing.csv`.",
            "",
            "## Limitações",
            "",
            "- Correlação não implica causalidade. Tamanho, domínio e cultura do projeto podem afetar as duas métricas.",
            "- A amostra só tem repositórios com pelo menos 5 releases e 50 workflow runs em 2025. Projetos que publicam pouco ficaram de fora, o que restringe a faixa da frequência.",
            "- CFR(a) mede falha de CI no default branch, não falha em produção. CFR(b) depende da heurística de release corretiva, com F1 0,40 na validação manual.",
            "- CFR(b) não é independente da frequência. Quem publica mais tem intervalos menores entre releases, então a próxima release cai mais vezes na janela de 7 dias. Parte da correlação de CFR(b) pode vir da própria definição, não de mais falhas.",
            "- Repositório com poucas releases gera CFR(b) com poucos valores possíveis, o que cria empates.",
            "- Os gráficos usam eixo X em escala logarítmica.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_scatter(path: Path, title: str, y_label: str, xs: Sequence[float], ys: Sequence[float], result: dict[str, Any]) -> None:
    width, height = 760, 520
    left, right, top, bottom = 80, 30, 60, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    positive = [value for value in xs if value > 0]
    if positive:
        log_min = math.floor(math.log10(min(positive)) * 2) / 2
        log_max = math.ceil(math.log10(max(positive)) * 2) / 2
    else:
        log_min, log_max = -1.0, 1.0
    if log_max <= log_min:
        log_max = log_min + 1
    y_max = max(1.0, max(ys, default=1.0))

    def px(value: float) -> float:
        return left + (math.log10(value) - log_min) / (log_max - log_min) * plot_w

    def py(value: float) -> float:
        return top + plot_h - value / y_max * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif">',
        '<rect width="100%" height="100%" fill="#f7f4ef"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="18">{_escape(title)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#24313a"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#24313a"/>',
    ]
    exponent = log_min
    while exponent <= log_max + 1e-9:
        value = 10**exponent
        x = px(value)
        parts.append(f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" y2="{top + plot_h + 5}" stroke="#24313a"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 20}" text-anchor="middle" font-size="12">{value:.3g}</text>')
        exponent += 0.5
    for step in range(0, 6):
        value = y_max * step / 5
        y = py(value)
        parts.append(f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#24313a"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="12">{value:.1f}</text>')
    for x_value, y_value in zip(xs, ys):
        if x_value <= 0:
            continue
        parts.append(f'<circle cx="{px(x_value):.1f}" cy="{py(y_value):.1f}" r="3.5" fill="#176b87" fill-opacity="0.55"/>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 20}" text-anchor="middle" font-size="13">Deployment frequency (releases/semana, escala log)</text>')
    parts.append(f'<text x="20" y="{top + plot_h / 2}" text-anchor="middle" font-size="13" transform="rotate(-90 20 {top + plot_h / 2})">{_escape(y_label)}</text>')
    p_text = _format_p(result["p_value"])
    p_text = f"p {p_text}" if p_text.startswith("<") else f"p = {p_text}"
    caption = f"rho = {_format(result['rho'], 3)}  {p_text}  n = {result['n_used']}"
    parts.append(f'<text x="{left + plot_w - 5}" y="{top + 15}" text-anchor="end" font-size="13">{_escape(caption)}</text>')
    parts.append("</svg>")
    path.write_text("".join(parts) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    columns = list(fieldnames or ())
    if not columns:
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
    parser = argparse.ArgumentParser(description="RQ05: Spearman entre deployment frequency e CFR(a)/CFR(b).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze(read_dataset(args.input))
    write_outputs(result, args.output)
    for item in result["correlations"]:
        print(f"RQ05 {item['variant']}: rho={_format(item['rho'], 3)} p={_format_p(item['p_value'])} n={item['n_used']}")
    print(f"Saidas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
