"""Janela de observacao usada na coleta de releases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone


@dataclass(frozen=True)
class ObservationWindow:
    """Intervalo inclusivo de datas, no fuso UTC."""

    start: date
    end: date

    @classmethod
    def from_config(cls, payload: dict) -> "ObservationWindow":
        window = payload.get("observation_window") or payload
        return cls(
            start=date.fromisoformat(str(window["start"])),
            end=date.fromisoformat(str(window["end"])),
        )


def parse_github_timestamp(value: str | None) -> datetime | None:
    """Converte um timestamp da API para datetime UTC."""

    if not value or not str(value).strip():
        return None
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def in_observation_window(moment: datetime | None, window: ObservationWindow) -> bool:
    """Diz se o instante cai entre o inicio e o fim da janela, inclusive."""

    if moment is None or window.end < window.start:
        return False
    start = datetime.combine(window.start, time.min, tzinfo=timezone.utc)
    end = datetime.combine(window.end, time.max, tzinfo=timezone.utc)
    current = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return start <= current.astimezone(timezone.utc) <= end
