"""Detecção de duplicação por blocos de linhas normalizadas."""

from __future__ import annotations

import re
from collections import defaultdict

_COMMENT_OR_BLANK = re.compile(r"^\s*(#.*)?$")
_INDENT = re.compile(r"^\s+")


def normalize_source_lines(source: str) -> list[str]:
    """Remove comentários/linhas vazias e colapsa indentação para comparação."""

    normalized: list[str] = []
    for line in source.splitlines():
        if _COMMENT_OR_BLANK.match(line):
            continue
        cleaned = _INDENT.sub("", line).rstrip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def duplication_percentage(sources: list[str], *, min_block_lines: int = 4) -> float:
    """Calcula o percentual de linhas que participam de blocos duplicados.

    A análise é determinística e independente do Radon. Arquivos sem linhas
    úteis resultam em 0.0 somente quando há código analisável em outros
    arquivos; o chamador deve tratar fontes vazias antes desta função.
    """

    if min_block_lines < 2:
        raise ValueError("min_block_lines deve ser pelo menos 2")

    all_lines: list[tuple[int, int]] = []
    blocks: dict[tuple[str, ...], list[tuple[int, int]]] = defaultdict(list)

    for file_index, source in enumerate(sources):
        lines = normalize_source_lines(source)
        for offset, _line in enumerate(lines):
            all_lines.append((file_index, offset))
        if len(lines) < min_block_lines:
            continue
        for start in range(0, len(lines) - min_block_lines + 1):
            block = tuple(lines[start : start + min_block_lines])
            blocks[block].append((file_index, start))

    duplicated: set[tuple[int, int]] = set()
    for occurrences in blocks.values():
        if len(occurrences) < 2:
            continue
        for file_index, start in occurrences:
            for offset in range(start, start + min_block_lines):
                duplicated.add((file_index, offset))

    if not all_lines:
        return 0.0
    return round(100.0 * len(duplicated) / len(all_lines), 3)
