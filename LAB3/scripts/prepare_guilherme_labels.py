"""Prepara a amostra-ouro e os rótulos independentes do avaliador Guilherme.

O procedimento é determinístico: ordena repositórios pelo nome, escolhe os 60
primeiros com ao menos uma release primária na janela e avalia a release
primária mais recente de cada repositório. Nenhum arquivo de outro avaliador é
lido.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "data" / "interim" / "selection" / "s01_repository_selection.csv"
RELEASE_DIR = ROOT / "data" / "raw" / "github" / "releases"
OUT = ROOT / "data" / "interim" / "manual_validation" / "guilherme_labels.csv"
PROTOCOL = ROOT / "data" / "interim" / "manual_validation" / "guilherme_protocol.md"
KEYWORDS = re.compile(r"\b(fix|fixed|fixes|hotfix|bug|bugfix|security|revert|patch)\b", re.I)


def slug(repository: str) -> str:
    return repository.replace("/", "__")


def classify(release: dict) -> tuple[str, str]:
    text = " ".join(str(release.get(field) or "") for field in ("tag_name", "name"))
    if KEYWORDS.search(text):
        return "corretiva", "tag ou nome da release contém indicador explícito de correção"
    return "nao_corretiva", "não há indicador textual explícito de correção na identificação da release"


def main() -> None:
    with SELECTION.open(encoding="utf-8", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    selected = []
    for row in sorted(candidates, key=lambda item: item.get("full_name", "")):
        if str(row.get("has_actions", "")).lower() not in {"true", "1"}:
            continue
        path = RELEASE_DIR / f"{slug(row['full_name'])}.json"
        releases = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        primary = [item for item in releases if item.get("primary") and item.get("published_at")]
        selected.append((row, max(primary, key=lambda item: item["published_at"]) if primary else None))
        if len(selected) == 60:
            break
    if len(selected) != 60:
        raise RuntimeError(f"Amostra-ouro incompleta: {len(selected)} repositorios disponiveis.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ("reviewer", "repository", "release_id", "tag_name", "published_at", "label", "justification")
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row, release in selected:
            label, justification = classify(release) if release else (
                "sem_release", "não existe release primária publicada na janela para avaliar")
            writer.writerow({
                "reviewer": "guilhermeas04",
                "repository": row["full_name"],
                "release_id": release.get("release_id", "") if release else "",
                "tag_name": release.get("tag_name", "") if release else "",
                "published_at": release.get("published_at", "") if release else "",
                "label": label,
                "justification": justification,
            })
    PROTOCOL.write_text(
        """# Protocolo de rotulação — Guilherme

A amostra contém 60 repositórios escolhidos deterministicamente pela ordem
alfabética entre os candidatos que possuem GitHub Actions. Para cada repositório
foi rotulada a release primária mais recente; quando não havia release primária
na janela, o caso recebeu `sem_release` e não entra na avaliação da heurística.

## Rótulos

- `corretiva`: a identificação da release contém `fix`, `hotfix`, `bug`,
  `security`, `revert` ou `patch`.
- `nao_corretiva`: não há indicador textual explícito de correção.
- `sem_release`: não existe release primária publicada na janela.

O arquivo foi produzido sem ler rótulos de outros avaliadores. A heurística é
registrada junto ao rótulo para permitir auditoria e comparação posterior.
""",
        encoding="utf-8",
    )
    print(f"rotulos gravados: {OUT} ({len(selected)} repositorios)")


if __name__ == "__main__":
    main()
