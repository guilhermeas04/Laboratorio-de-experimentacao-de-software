"""Gera o dashboard final autocontido do LAB04S02."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .hypothesis_tests import run_both_tests
from .pipeline import run_pipeline
from .s02_report import run_s02_report

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "dashboard" / "index.html"
REPO_URL = "https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software"
PROJECT_URL = "https://github.com/users/guilhermeas04/projects/3"


def real_test_rows(real_data: Path, alpha: float = 0.05) -> list[dict[str, Any]]:
    frame = pd.read_csv(real_data)
    bot = frame.loc[frame["group"] == "bot", "duration_hours"].to_numpy()
    human = frame.loc[frame["group"] == "human", "duration_hours"].to_numpy()
    rows = []
    for result in run_both_tests(bot, human, alternative="two-sided", alpha=alpha):
        rows.append({**result.to_dict(), "conclusion": "rejeita H0" if result.reject_null else "nao rejeita H0"})
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_dashboard(output: Path, *, real_data: Path, processed: Path, figures: Path, tables: Path) -> Path:
    config = load_json(ROOT / "config" / "simulation.json")
    interpretation = load_json(tables / "g3_g4_interpretation.json")
    example = list(csv.DictReader((tables / "example_tests.csv").open(encoding="utf-8", newline="")))
    real_rows = real_test_rows(real_data, float(config["alpha"]))
    q1 = list(csv.DictReader((processed / "q1_results.csv").open(encoding="utf-8", newline="")))
    q2 = list(csv.DictReader((processed / "q2_results.csv").open(encoding="utf-8", newline="")))
    q3 = list(csv.DictReader((processed / "q3_power_results.csv").open(encoding="utf-8", newline="")))
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(_test_row(row) for row in real_rows)
    q1_rows = "\n".join(f"<tr><td>{html.escape(row['test_name'])}</td><td>{float(row['rejection_rate']):.2%}</td><td>{row['replications']}</td></tr>" for row in q1)
    q2_rows = "\n".join(f"<tr><td>{html.escape(row['test_name'])}</td><td>{float(row['effect_hours']):.2f}</td><td>{float(row['power']):.2%}</td></tr>" for row in q2 if row["test_name"] == "mann_whitney")
    q3_rows = "\n".join(f"<tr><td>{html.escape(row['situation'])}</td><td>{html.escape(row['test_name'])}</td><td>{float(row['power']):.2%}</td></tr>" for row in q3 if row["effect_hours"] == "2.0")
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LAB04 — Dashboard final</title>
<style>
:root {{ --ink:#23313b; --paper:#f7f4ef; --blue:#176b87; --green:#4f9d69; --orange:#e0a458; --red:#c94c4c; }}
* {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); background:var(--paper); font:16px/1.6 Georgia,serif; }} main {{ max-width:1100px; margin:auto; padding:2rem 1.25rem 5rem; }}
h1,h2,h3,th {{ font-family:Arial,sans-serif; }} h1 {{ font-size:clamp(2rem,5vw,4rem); line-height:1.05; margin:.4rem 0 1rem; }} h2 {{ margin-top:3rem; border-top:4px solid var(--blue); padding-top:1rem; }}
.eyebrow {{ color:var(--blue); font:700 .8rem Arial,sans-serif; letter-spacing:.12em; text-transform:uppercase; }} .links {{ display:flex; flex-wrap:wrap; gap:.7rem; margin:1.2rem 0 2rem; }} .links a {{ color:white; background:var(--blue); padding:.45rem .75rem; text-decoration:none; border-radius:4px; font-family:Arial,sans-serif; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; }} .fact {{ background:white; border-left:5px solid var(--orange); padding:1rem; }} figure {{ margin:1.25rem 0; background:white; padding:1rem; }} figure img {{ display:block; width:100%; max-height:650px; object-fit:contain; }} figcaption {{ margin-top:.8rem; }} table {{ border-collapse:collapse; width:100%; background:white; margin:1rem 0 1.5rem; font-family:Arial,sans-serif; font-size:.9rem; }} th,td {{ border-bottom:1px solid #d5dadd; padding:.55rem; text-align:left; }} th {{ background:#dfecef; }} .note {{ border-left:4px solid var(--green); padding:.2rem 1rem; background:#edf5ee; }} code {{ background:#e9e5dd; padding:.1rem .25rem; }}
@media(max-width:600px) {{ main {{ padding:.9rem; }} table {{ font-size:.76rem; }} th,td {{ padding:.35rem; }} }}
</style></head><body><main>
<div class="eyebrow">Laboratório de Experimentação de Software</div><h1>LAB04 — Testes de hipótese por dentro</h1>
<p>Dashboard final: comparação entre t de Welch e Mann-Whitney para o tempo até o merge de pull requests.</p>
<div class="links"><a href="{REPO_URL}/tree/main/LAB4">Repositório</a><a href="{PROJECT_URL}">GitHub Projects</a><a href="{REPO_URL}/blob/main/LAB4/dashboard/index.html">Dashboard no GitHub</a></div>
<div class="grid"><div class="fact"><b>Equipe</b><br>Amanda Bicalho Silva<br>Guilherme de Almeida Santos<br>Pedro Rodrigues Duarte</div><div class="fact"><b>Amostra</b><br>30 bots + 30 humanos<br>Unidade: horas</div><div class="fact"><b>Reprodução</b><br>Semente 42<br>10.000 repetições</div></div>
<h2>1. Cenário</h2><p><b>Pergunta:</b> o tempo de merge difere entre PRs de autoria automatizada e PRs de autoria humana?</p><p><b>H₀:</b> as distribuições são iguais. <b>H₁:</b> elas diferem. A análise é bicaudal. Os dados reais vêm da API REST pública do GitHub e foram filtrados para PRs mesclados com timestamps válidos. Os testes são t de Welch e Mann-Whitney.</p>
<h2>2. Os dados — G1</h2><p>Os dados reais têm 30 observações em cada grupo e foram modelados por distribuições lognormais calibradas com as medianas e a dispersão logarítmica observadas. A assimetria e as caudas longas representam tempos de merge muito prolongados; por isso, o cenário simulado preserva outliers em vez de substituí-los por médias. O parâmetro de efeito é deslocado em horas para avaliar a capacidade de detecção.</p>
<figure><img src="../reports/figures/g1_histograms.png" alt="G1 histogramas dos dados reais e simulados"><figcaption>G1 — Histogramas dos tempos de merge, em horas.</figcaption></figure>
<h2>3. Como os testes funcionam — G2</h2><p>Welch compara médias permitindo variâncias diferentes; Mann-Whitney compara a posição relativa dos postos e é menos sensível a valores extremos. A região de rejeição contém resultados pouco compatíveis com H₀ para α=0,05. O p-valor mede a compatibilidade dos dados com H₀; ele não é a probabilidade de H₀ ser verdadeira nem mede o tamanho ou a importância prática do efeito.</p>
<figure><img src="../reports/figures/g2_null_distribution.png" alt="G2 distribuição nula da estatística"><figcaption>G2 — Distribuição nula da estatística de Welch, região crítica e exemplo.</figcaption></figure>
<h2>4. Erro tipo I — G3</h2><p>{html.escape(interpretation['g3'])}</p><figure><img src="../reports/figures/g3_type_i_error.png" alt="G3 erro tipo I"><figcaption>G3 — Taxas de rejeição quando H₀ é verdadeira; a referência é 5%.</figcaption></figure><table><tr><th>Teste</th><th>Erro tipo I ideal</th><th>Repetições</th></tr>{q1_rows}</table>
<h2>5. Poder — G4</h2><p>{html.escape(interpretation['g4'])}</p><figure><img src="../reports/figures/g4_power.png" alt="G4 curvas de poder"><figcaption>G4 — Poder em função do efeito e sob violações de pressupostos.</figcaption></figure><table><tr><th>Teste</th><th>Efeito (h)</th><th>Poder ideal</th></tr>{q2_rows}</table><p class="note">No efeito de 2 horas sob violações, resultados adicionais: {q3_rows}.</p>
<h2>6. Dados reais</h2><p>Os resultados abaixo foram calculados diretamente sobre as 60 observações brutas, sem usar os resultados simulados.</p><table><tr><th>Teste</th><th>Estatística</th><th>p-valor</th><th>Tamanho do efeito</th><th>Nome do efeito</th><th>Decisão sobre H₀</th><th>Conclusão</th></tr>{rows}</table>
<h2>7. Conclusão</h2><p>Antes da simulação, esperávamos que Mann-Whitney fosse mais robusto para a assimetria e os outliers, enquanto Welch poderia ser competitivo em dados aproximadamente simétricos. Os resultados confirmaram essa expectativa: Mann-Whitney ficou próximo de 5% no erro tipo I e apresentou maior poder nos efeitos avaliados, enquanto Welch foi conservador neste cenário lognormal. Recomendamos Mann-Whitney para este tipo de tempo de merge; a escolha pode mudar quando a pergunta for explicitamente sobre médias e os resíduos forem aproximadamente simétricos. A principal limitação é a amostra de conveniência de PRs públicos e o uso de autoria de bot como proxy de automação.</p>
<h3>Roteiro oral</h3><ol><li><b>Cenário:</b> comparamos tempo de merge de bots e humanos em PRs públicos.</li><li><b>Hipóteses:</b> H₀ diz distribuições iguais; H₁ diz diferença.</li><li><b>Coleta:</b> 30 observações por grupo, usando created_at e merged_at.</li><li><b>Distribuição:</b> tempos são assimétricos e têm caudas longas.</li><li><b>Welch:</b> compara médias sem exigir variâncias iguais.</li><li><b>Mann-Whitney:</b> compara postos e posição relativa.</li><li><b>p-valor:</b> compatibilidade com H₀, não probabilidade de H₀.</li><li><b>Erro tipo I:</b> rejeitar H₀ quando ela é verdadeira.</li><li><b>Erro tipo II:</b> não detectar um efeito que existe.</li><li><b>Poder:</b> probabilidade de detectar um efeito real.</li><li><b>Pressupostos:</b> assimetria prejudica Welch neste cenário.</li><li><b>Efeito:</b> relatamos Cohen d e rank-biserial.</li><li><b>Amostra:</b> 60 PRs, suficiente para demonstração, não para generalização ampla.</li><li><b>Recomendação:</b> Mann-Whitney para caudas longas e outliers.</li><li><b>Limitação:</b> amostra de conveniência e proxy de autoria automatizada.</li></ol>
</main></body></html>"""
    output.write_text(html_content, encoding="utf-8")
    return output


def _test_row(row: dict[str, Any]) -> str:
    return "<tr>" + "".join([
        f"<td>{html.escape(str(row['test_name']))}</td>", f"<td>{float(row['statistic']):.4f}</td>",
        f"<td>{float(row['p_value']):.4f}</td>", f"<td>{float(row['effect_size']):.4f}</td>",
        f"<td>{html.escape(str(row['effect_size_name']))}</td>", f"<td>{row['conclusion']}</td>",
        f"<td>{'Diferença estatisticamente significativa' if row['reject_null'] else 'Não há evidência suficiente de diferença'}</td>",
    ]) + "</tr>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera o dashboard final do LAB04.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-compute", action="store_true", help="usa os artefatos existentes sem recalcular simulacoes")
    args = parser.parse_args(argv)
    if not args.skip_compute:
        run_pipeline(null_replications=2000)
        run_s02_report()
    generate_dashboard(args.output, real_data=ROOT / "data" / "raw" / "pr_merge_time.csv", processed=ROOT / "data" / "processed", figures=ROOT / "reports" / "figures", tables=ROOT / "reports" / "tables")
    print(f"Dashboard gerado em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())