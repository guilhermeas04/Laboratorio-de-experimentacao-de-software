"""Gera histogramas numericos diretamente do dataset S02."""
from __future__ import annotations
import csv, math
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/datasets/s02_metrics.csv"
OUT = ROOT / "reports/numerical"

def values(rows, column):
    result = []
    for row in rows:
        try:
            value = float(row.get(column, ""))
            if math.isfinite(value):
                result.append(value)
        except (TypeError, ValueError):
            pass
    return result

def quantile(xs, p):
    xs = sorted(xs)
    position = (len(xs) - 1) * p
    lower, upper = math.floor(position), math.ceil(position)
    return xs[lower] if lower == upper else xs[lower] + (xs[upper] - xs[lower]) * (position - lower)

def histogram(path, title, xlabel, xs, bins=12):
    width, height = 800, 480
    lo, hi = min(xs), max(xs)
    if lo == hi:
        hi = lo + 1
    step = (hi - lo) / bins
    counts = [0] * bins
    for value in xs:
        counts[min(bins - 1, int((value - lo) / step))] += 1
    maximum = max(counts) or 1
    axis_max = 125 if title.startswith("RQ01") else maximum
    left, bottom, plot_w, plot_h = 70, 385, 680, 290
    bars = []
    for index, count in enumerate(counts):
        x = left + index * plot_w / bins + 2
        bar_width = plot_w / bins - 4
        bar_height = plot_h * count / axis_max
        bars.append(f'<rect x="{x:.1f}" y="{bottom-bar_height:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#4f9d69"/>')
    q1, median, q3 = quantile(xs, 0.25), quantile(xs, 0.5), quantile(xs, 0.75)
    q1_x = left + plot_w * (q1 - lo) / (hi - lo)
    median_x = left + plot_w * (median - lo) / (hi - lo)
    q3_x = left + plot_w * (q3 - lo) / (hi - lo)
    ticks = []
    tick_step = 25 if title.startswith("RQ01") else max(1, math.ceil(maximum / 5))
    tick_limit = 125 if title.startswith("RQ01") else maximum
    for tick in range(0, tick_limit + 1, tick_step):
        y = bottom - plot_h * tick / axis_max
        ticks.append(f'<line x1="{left-5}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#24313a"/><text x="{left-10}" y="{y+4:.1f}" text-anchor="end">{tick}</text>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif">'
        f'<rect width="100%" height="100%" fill="#f7f4ef"/>'
        f'<text x="400" y="32" text-anchor="middle" font-size="20">{title}</text>'
        f'<text x="400" y="460" text-anchor="middle">{xlabel}</text>'
        f'<text x="18" y="245" transform="rotate(-90 18 245)" text-anchor="middle">Quantidade de repositorios</text>'
        f'<line x1="{left}" y1="{bottom}" x2="{left+plot_w}" y2="{bottom}" stroke="#24313a"/>'
        + "".join(ticks)
        + "".join(bars)
        + f'<rect x="{q1_x:.1f}" y="85" width="{q3_x-q1_x:.1f}" height="{bottom-85}" fill="#4f9d69" opacity="0.10"/>'
        + f'<line x1="{q1_x:.1f}" y1="85" x2="{q1_x:.1f}" y2="{bottom}" stroke="#176b87" stroke-dasharray="6,4" stroke-width="2"/>'
        + f'<line x1="{median_x:.1f}" y1="85" x2="{median_x:.1f}" y2="{bottom}" stroke="#c94c4c" stroke-width="3"/>'
        + f'<line x1="{q3_x:.1f}" y1="85" x2="{q3_x:.1f}" y2="{bottom}" stroke="#176b87" stroke-dasharray="6,4" stroke-width="2"/>'
        + f'<text x="{q1_x+5:.1f}" y="62" fill="#176b87">Q1={q1:.4g}</text><text x="{median_x+5:.1f}" y="78" fill="#c94c4c">mediana={median:.4g}</text><text x="{q3_x+5:.1f}" y="94" fill="#176b87">Q3={q3:.4g}</text>'
        + f'<text x="{left}" y="410" text-anchor="middle">{lo:.2g}</text><text x="{left+plot_w}" y="410" text-anchor="middle">{hi:.2g}</text></svg>\n'
    )
    path.write_text(svg, encoding="utf-8")

def rq07_heatmap(path):
    source = ROOT / "reports/rq07/rq07_sensitivity.json"
    if not source.exists():
        return
    comparisons = json.loads(source.read_text(encoding="utf-8")).get("comparisons", [])
    variants = ["C1", "C2", "C3"]
    values_by_pair = {(item["left"].split("_")[0], item["right"].split("_")[0]): float(item["changed_pct"]) for item in comparisons}
    cell = 130
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="540" font-family="sans-serif"><rect width="100%" height="100%" fill="#f7f4ef"/><text x="350" y="32" text-anchor="middle" font-size="20">RQ07 — taxa de mudança entre variantes</text><text x="350" y="505" text-anchor="middle">Variante de destino</text><text x="18" y="245" transform="rotate(-90 18 245)" text-anchor="middle">Variante de origem</text>']
    for index, variant in enumerate(variants):
        parts.append(f'<text x="{185+index*cell}" y="75" text-anchor="middle">{variant}</text><text x="65" y="{125+index*cell}" text-anchor="middle">{variant}</text>')
    for row, left in enumerate(variants):
        for col, right in enumerate(variants):
            value = 0 if left == right else values_by_pair.get((left, right), values_by_pair.get((right, left), 0))
            shade = max(0, min(255, int(230 - value * 2)))
            x, y = 120 + col * cell, 90 + row * cell
            parts.append(f'<rect x="{x}" y="{y}" width="100" height="100" fill="rgb({shade},{min(255,shade+25)},{min(255,shade+45)})"/><text x="{x+50}" y="{y+57}" text-anchor="middle">{value:.1f}%</text>')
    parts.append('<text x="530" y="110" font-size="12">Legenda: taxa de mudança</text><rect x="530" y="125" width="24" height="24" fill="rgb(230,255,255)"/><text x="562" y="142" font-size="11">menor mudança</text><rect x="530" y="160" width="24" height="24" fill="rgb(137,162,182)"/><text x="562" y="177" font-size="11">maior mudança</text><text x="530" y="210" font-size="11">Cor mais escura = maior</text><text x="530" y="226" font-size="11">percentual de classificações</text><text x="530" y="242" font-size="11">DORA alteradas.</text></svg>\n')
    path.write_text("".join(parts), encoding="utf-8")

def rq02_boxplot(path, release_values, commit_values):
    series = [("Por release", release_values, "#176b87"), ("Por commit", commit_values, "#c94c4c")]
    width, height = 760, 500
    left, bottom, plot_w, plot_h = 95, 400, 520, 310
    all_values = release_values + commit_values
    y_min, y_max = 0.5, max(all_values)
    log_min, log_max = math.log10(y_min), math.log10(y_max)
    def y(value):
        return bottom - plot_h * (math.log10(max(value, y_min)) - log_min) / (log_max - log_min)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif"><rect width="100%" height="100%" fill="#f7f4ef"/><text x="380" y="32" text-anchor="middle" font-size="20">RQ02 — lead time por variante</text><text x="380" y="480" text-anchor="middle">variante de cálculo</text><text x="18" y="245" transform="rotate(-90 18 245)" text-anchor="middle">Lead time (dias, escala log)</text><line x1="{left}" y1="{bottom}" x2="{left+plot_w}" y2="{bottom}" stroke="#24313a"/>']
    for tick in (1, 3, 7, 14, 30, 60, 120, 240):
        if tick <= y_max:
            yy = y(tick)
            parts.append(f'<line x1="{left-5}" y1="{yy:.1f}" x2="{left}" y2="{yy:.1f}" stroke="#24313a"/><text x="{left-10}" y="{yy+4:.1f}" text-anchor="end">{tick}</text>')
    for index, (label, values, color) in enumerate(series):
        q1, med, q3 = quantile(values, .25), quantile(values, .5), quantile(values, .75)
        ordered = sorted(values)
        low = min(value for value in ordered if value >= q1 - 1.5 * (q3-q1))
        high = max(value for value in ordered if value <= q3 + 1.5 * (q3-q1))
        x = left + plot_w * (0.25 + index * 0.5)
        parts.append(f'<line x1="{x}" y1="{y(low):.1f}" x2="{x}" y2="{y(high):.1f}" stroke="{color}" stroke-width="3"/><line x1="{x-25}" y1="{y(low):.1f}" x2="{x+25}" y2="{y(low):.1f}" stroke="{color}" stroke-width="3"/><line x1="{x-25}" y1="{y(high):.1f}" x2="{x+25}" y2="{y(high):.1f}" stroke="{color}" stroke-width="3"/><rect x="{x-45}" y="{y(q3):.1f}" width="90" height="{y(q1)-y(q3):.1f}" fill="{color}" opacity="0.65"/><line x1="{x-45}" y1="{y(med):.1f}" x2="{x+45}" y2="{y(med):.1f}" stroke="#111" stroke-width="3"/><text x="{x}" y="430" text-anchor="middle">{label}</text><text x="{x+52}" y="{y(med)+4:.1f}" font-size="12">Mediana={med:.2f}</text>')
        for value in ordered:
            if value < low or value > high:
                parts.append(f'<circle cx="{x}" cy="{y(value):.1f}" r="3" fill="{color}"/>')
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")

def rq03_boxplot(path, cfr_a, cfr_b):
    series = [("CFR(a)", cfr_a, "#176b87"), ("CFR(b)", cfr_b, "#c94c4c")]
    width, height = 760, 500
    left, bottom, plot_w, plot_h = 95, 400, 520, 310
    def y(value):
        return bottom - plot_h * value
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif"><rect width="100%" height="100%" fill="#f7f4ef"/><text x="380" y="32" text-anchor="middle" font-size="20">RQ03 — change failure rate por variante</text><text x="380" y="480" text-anchor="middle">variante de cálculo</text><text x="18" y="245" transform="rotate(-90 18 245)" text-anchor="middle">Taxa de falha</text><line x1="{left}" y1="{bottom}" x2="{left+plot_w}" y2="{bottom}" stroke="#24313a"/>']
    for tick in (0, .25, .5, .75, 1):
        yy = y(tick)
        parts.append(f'<line x1="{left-5}" y1="{yy:.1f}" x2="{left}" y2="{yy:.1f}" stroke="#24313a"/><text x="{left-10}" y="{yy+4:.1f}" text-anchor="end">{tick:.2f}</text>')
    for index, (label, values, color) in enumerate(series):
        q1, med, q3 = quantile(values, .25), quantile(values, .5), quantile(values, .75)
        ordered = sorted(values)
        low = min(value for value in ordered if value >= q1 - 1.5 * (q3-q1))
        high = max(value for value in ordered if value <= q3 + 1.5 * (q3-q1))
        x = left + plot_w * (0.25 + index * 0.5)
        parts.append(f'<line x1="{x}" y1="{y(low):.1f}" x2="{x}" y2="{y(high):.1f}" stroke="{color}" stroke-width="3"/><line x1="{x-25}" y1="{y(low):.1f}" x2="{x+25}" y2="{y(low):.1f}" stroke="{color}" stroke-width="3"/><line x1="{x-25}" y1="{y(high):.1f}" x2="{x+25}" y2="{y(high):.1f}" stroke="{color}" stroke-width="3"/><rect x="{x-45}" y="{y(q3):.1f}" width="90" height="{y(q1)-y(q3):.1f}" fill="{color}" opacity="0.65"/><line x1="{x-45}" y1="{y(med):.1f}" x2="{x+45}" y2="{y(med):.1f}" stroke="#111" stroke-width="3"/><text x="{x}" y="430" text-anchor="middle">{label}</text><text x="{x+52}" y="{y(med)+4:.1f}" font-size="12">Mediana={med:.4f}</text>')
        for value in ordered:
            if value < low or value > high:
                parts.append(f'<circle cx="{x}" cy="{y(value):.1f}" r="3" fill="{color}"/>')
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")

def rq04_boxplot(path, recovery_values):
    width, height = 620, 500
    left, bottom, plot_w, plot_h = 95, 400, 360, 310
    y_min, y_max = 0.01, max(recovery_values)
    log_min, log_max = math.log10(y_min), math.log10(y_max)
    def y(value):
        return bottom - plot_h * (math.log10(max(value, y_min)) - log_min) / (log_max - log_min)
    q1, med, q3 = quantile(recovery_values, .25), quantile(recovery_values, .5), quantile(recovery_values, .75)
    spread = q3 - q1
    ordered = sorted(recovery_values)
    low = min(value for value in ordered if value >= q1 - 1.5 * spread)
    high = max(value for value in ordered if value <= q3 + 1.5 * spread)
    x = left + plot_w / 2
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif"><rect width="100%" height="100%" fill="#f7f4ef"/><text x="310" y="32" text-anchor="middle" font-size="20">RQ04 — tempo de recuperação</text><text x="310" y="480" text-anchor="middle">episódios recuperados observáveis</text><text x="18" y="245" transform="rotate(-90 18 245)" text-anchor="middle">Tempo (horas, escala log)</text><line x1="{left}" y1="{bottom}" x2="{left+plot_w}" y2="{bottom}" stroke="#24313a"/>']
    for tick in (.01, .1, 1, 10, 100, 1000, 10000):
        if tick <= y_max:
            yy = y(tick)
            parts.append(f'<line x1="{left-5}" y1="{yy:.1f}" x2="{left}" y2="{yy:.1f}" stroke="#24313a"/><text x="{left-10}" y="{yy+4:.1f}" text-anchor="end">{tick:g}</text>')
    parts.append(f'<line x1="{x}" y1="{y(low):.1f}" x2="{x}" y2="{y(high):.1f}" stroke="#176b87" stroke-width="3"/><line x1="{x-25}" y1="{y(low):.1f}" x2="{x+25}" y2="{y(low):.1f}" stroke="#176b87" stroke-width="3"/><line x1="{x-25}" y1="{y(high):.1f}" x2="{x+25}" y2="{y(high):.1f}" stroke="#176b87" stroke-width="3"/><rect x="{x-50}" y="{y(q3):.1f}" width="100" height="{y(q1)-y(q3):.1f}" fill="#176b87" opacity="0.65"/><line x1="{x-50}" y1="{y(med):.1f}" x2="{x+50}" y2="{y(med):.1f}" stroke="#111" stroke-width="3"/><text x="{x}" y="430" text-anchor="middle">Recuperação observável</text><text x="{x+58}" y="{y(med)+4:.1f}" font-size="12">Mediana={med:.4f} h</text>')
    for value in ordered:
        if value < low or value > high:
            parts.append(f'<circle cx="{x}" cy="{y(value):.1f}" r="3" fill="#176b87"/>')
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")

def main():
    with DATA.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    OUT.mkdir(parents=True, exist_ok=True)
    figures = {
        "rq01-deployment-frequency-histogram.svg": ("RQ01 — deployment frequency", "releases por semana", "deployment_frequency_per_week"),
        "rq02-lead-time-release-histogram.svg": ("RQ02 — lead time por release", "dias", "lead_time_by_release_days"),
        "rq02-lead-time-commit-histogram.svg": ("RQ02 — lead time por commit", "dias", "lead_time_by_commit_days"),
        "rq03-cfr-a-histogram.svg": ("RQ03 — CFR(a)", "taxa de falha", "cfr_ci"),
        "rq03-cfr-b-histogram.svg": ("RQ03 — CFR(b)", "taxa de falha", "cfr_b"),
        "rq04-recovery-histogram.svg": ("RQ04 — tempo de recuperacao", "horas", "recovery_median_hours"),
    }
    for filename, (title, xlabel, column) in figures.items():
        series = values(rows, column)
        if series:
            histogram(OUT / filename, title, xlabel, series)
            print(f"{filename}: n={len(series)}, mediana={quantile(series, 0.5):.6g}")
    rq02_boxplot(OUT / "rq02-lead-time-boxplot.svg", values(rows, "lead_time_by_release_days"), values(rows, "lead_time_by_commit_days"))
    rq03_boxplot(OUT / "rq03-cfr-boxplot.svg", values(rows, "cfr_ci"), values(rows, "cfr_b"))
    rq04_boxplot(OUT / "rq04-recovery-boxplot.svg", values(rows, "recovery_median_hours"))
    rq07_heatmap(OUT / "rq07-sensitivity-heatmap.svg")

if __name__ == "__main__":
    main()
