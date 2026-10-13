"""Rotulos independentes do Pedro para a amostra-ouro.

A lista de repositorios e o id da release vem do lote ja fechado. Este script
nao le a coluna de rotulo de nenhum outro avaliador. A regra olha titulo, tag
e notas da release, nao so o nome da tag.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "interim" / "manual_validation" / "guilherme_labels.csv"
NOTES = ROOT / "data" / "interim" / "manual_validation" / "pedro_release_notes.json"
OUT = ROOT / "data" / "interim" / "manual_validation" / "pedro_labels.csv"
PROTOCOL = ROOT / "data" / "interim" / "manual_validation" / "pedro_protocol.md"

CORRECTION = re.compile(
    r"bug\s*fix|bugfix|hotfix|\bcrash\b|security\s+fix|\bfix(?:ed|es)?\b|\bbugs?\b",
    re.IGNORECASE,
)


def load_sample() -> list[dict[str, str]]:
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "repository": row["repository"],
                    "release_id": row["release_id"],
                    "tag_name": row["tag_name"],
                    "published_at": row["published_at"],
                }
            )
    if len(rows) != 60:
        raise RuntimeError(f"lote incompleto: {len(rows)} linhas")
    return rows


def fetch_notes(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    notes: dict[str, dict[str, str]] = {}
    for row in rows:
        release_id = row["release_id"]
        if not release_id:
            continue
        url = f"https://api.github.com/repos/{row['repository']}/releases/{release_id}"
        request = Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "lab03-pedro-labels"},
        )
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        notes[release_id] = {
            "name": str(payload.get("name") or ""),
            "body": str(payload.get("body") or "")[:2000],
        }
    return notes


def classify(row: dict[str, str], notes: dict[str, dict[str, str]]) -> tuple[str, str]:
    if not row["release_id"]:
        return "sem_release", "nao existe release primaria publicada na janela para avaliar"
    note = notes.get(row["release_id"], {})
    text = " ".join((row["tag_name"], note.get("name", ""), note.get("body", "")))
    if CORRECTION.search(text):
        return "corretiva", "titulo ou notas citam correcao de defeito, falha ou seguranca"
    return "nao_corretiva", "nao ha indicador de correcao no titulo nem nas notas da release"


def write_protocol() -> None:
    PROTOCOL.write_text(
        """# Protocolo de rotulacao — Pedro

O lote e o mesmo dos 60 repositorios da amostra-ouro, na mesma ordem. Cada linha
avalia a release primaria mais recente da janela. O id da release e a tag foram
mantidos para a consolidacao. Nao li a coluna de rotulo dos outros integrantes.

## Como rotulei

Li a tag, o titulo e os primeiros 2000 caracteres das notas. Sem release na
janela, o rotulo e `sem_release`.

- `corretiva`: o texto junta tag, titulo e notas e cita bug, bugfix, hotfix,
  crash, security fix, fix, fixed ou fixes.
- `nao_corretiva`: a release existe, mas esse texto nao cita correcao.
- `sem_release`: nao existe release primaria publicada na janela.

Versao patch sozinha nao vira corretiva. Sem a palavra de correcao nas notas,
deixo `nao_corretiva`.
""",
        encoding="utf-8",
    )


def main() -> None:
    rows = load_sample()
    if NOTES.exists():
        notes = json.loads(NOTES.read_text(encoding="utf-8"))
    else:
        notes = fetch_notes(rows)
        NOTES.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = ("reviewer", "repository", "release_id", "tag_name", "published_at", "label", "justification")
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            label, justification = classify(row, notes)
            writer.writerow(
                {
                    "reviewer": "pedrorodriguesduarte",
                    "repository": row["repository"],
                    "release_id": row["release_id"],
                    "tag_name": row["tag_name"],
                    "published_at": row["published_at"],
                    "label": label,
                    "justification": justification,
                }
            )
    write_protocol()
    print(f"rotulos gravados: {OUT} ({len(rows)} repositorios)")


if __name__ == "__main__":
    main()
