"""Prepara os rotulos independentes da Amanda para a amostra-ouro."""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "interim" / "manual_validation" / "guilherme_labels.csv"
OUT = ROOT / "data" / "interim" / "manual_validation" / "amanda_labels.csv"
PROTOCOL = ROOT / "data" / "interim" / "manual_validation" / "amanda_protocol.md"

CORRECTION = re.compile(
    r"\b(fix(?:ed|es)?|bug(?:fix)?|hotfix|security|vulnerabilit(?:y|ies)|"
    r"regression|crash(?:ed|es)?|correct(?:ed|ion)?|resolve(?:d|s)?|"
    r"failure|error)\b",
    re.IGNORECASE,
)


def load_lot() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        return [
            {
                "repository": row["repository"],
                "release_id": row["release_id"],
                "tag_name": row["tag_name"],
                "published_at": row["published_at"],
            }
            for row in csv.DictReader(handle)
        ]


def get_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lab03-amanda-labels",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code != 401 or "Authorization" not in headers:
            raise
        headers.pop("Authorization")
        request = Request(url, headers=headers)
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def get_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "lab03-amanda-labels"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def linked_notes(body: str) -> str:
    links = re.findall(r"https?://[^\s)]+", body)
    notes = []
    for link in links:
        clean_link = link.rstrip(".,")
        parsed = urlparse(clean_link)
        if "/wiki/" not in parsed.path:
            continue
        owner_repo, page = parsed.path.split("/wiki/", 1)
        raw_url = f"https://raw.githubusercontent.com/wiki/{owner_repo}/{page}.md"
        try:
            notes.append(get_text(raw_url))
        except Exception:
            continue
    return "\n".join(notes)


def classify(payload: dict | None, notes: str) -> tuple[str, str]:
    if payload is None:
        return "incerta", "nao foi possivel consultar a release; revisar a pagina do GitHub manualmente"
    if not payload:
        return "sem_release", "nao existe release primaria publicada na janela para avaliar"

    name = str(payload.get("name") or "")
    body = str(payload.get("body") or "")
    evidence = " ".join((name, body, notes))
    if CORRECTION.search(evidence):
        return "corretiva", "release notes ou changelog registram correcao de erro, falha, bug, regressao ou seguranca"
    if name or body or notes:
        return "nao_corretiva", "release notes e changelog nao registram correcao de defeito"
    return "incerta", "release publicada sem titulo, notas ou changelog disponivel"


def main() -> None:
    rows = load_lot()
    if len(rows) != 60:
        raise RuntimeError(f"lote incompleto: {len(rows)} linhas")

    output = []
    for row in rows:
        payload: dict | None = {}
        notes = ""
        if row["release_id"]:
            url = f"https://api.github.com/repos/{row['repository']}/releases/{row['release_id']}"
            try:
                payload = get_json(url)
                notes = linked_notes(str(payload.get("body") or ""))
            except Exception:
                payload = None

        label, justification = classify(payload, notes)
        release_url = str(payload.get("html_url") or "") if payload else ""
        if not release_url and row["tag_name"]:
            release_url = f"https://github.com/{row['repository']}/releases/tag/{row['tag_name']}"
        output.append(
            {
                "reviewer": "amanda",
                "repository": row["repository"],
                "release_id": row["release_id"],
                "tag_name": row["tag_name"],
                "published_at": row["published_at"],
                "release_url": release_url,
                "label": label,
                "justification": justification,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = tuple(output[0])
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    PROTOCOL.write_text(
        """# Protocolo de rotulacao — Amanda

O lote possui 60 repositorios. Foram preservados o repositorio, o id da release,
a tag e a data da release. Linhas sem release publicada receberam `sem_release`.
Os rotulos dos demais avaliadores nao foram usados.

## Procedimento

Para cada release, foram consultados o titulo, o corpo da release, os links de
release notes indicados pelo proprio GitHub e, quando disponivel, o changelog.

- `corretiva`: as notas ou o changelog indicam correcao de bug, erro, falha,
  regressao, crash, vulnerabilidade ou seguranca.
- `nao_corretiva`: existe release e as notas consultadas nao indicam correcao
  de defeito.
- `incerta`: existe release, mas nao ha titulo, notas ou changelog suficiente.
- `sem_release`: nao existe release primaria publicada na janela.

A versao final deve ser revisada manualmente nas paginas das releases antes da
consolidacao da concordancia.
""",
        encoding="utf-8",
    )
    print(f"rotulos gravados: {OUT} ({len(output)} repositorios)")


if __name__ == "__main__":
    main()
