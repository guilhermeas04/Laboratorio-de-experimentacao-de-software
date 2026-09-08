"""Cronometragem e persistência dos trials do experimento."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .trial_record import MAX_TRIAL_SECONDS, TREATMENTS, TrialRecord, TrialValidationError

Clock = Callable[[], datetime]
TRIAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SESSIONS_DIR = LAB2_ROOT / "data" / "sessions"
DEFAULT_OUTPUT_DIR = LAB2_ROOT / "data" / "raw"


class TrialTimerError(RuntimeError):
    """Indica uso inválido ou estado inconsistente do cronômetro."""


@dataclass(frozen=True, slots=True)
class TrialSession:
    """Metadados congelados quando o cronômetro é iniciado."""

    schema_version: str
    trial_id: str
    participant: str
    kata_id: str
    treatment: str
    execution_order: int
    started_at: str
    assistant_name: str | None
    assistant_version: str | None


@dataclass(frozen=True, slots=True)
class TrialStatus:
    """Visão calculada do tempo de uma sessão em andamento."""

    trial_id: str
    started_at: str
    elapsed_seconds: float
    remaining_seconds: float
    time_box_reached: bool


class TrialTimer:
    """Gerencia sessões e gera registros finais imutáveis."""

    def __init__(
        self,
        sessions_dir: Path = DEFAULT_SESSIONS_DIR,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        clock: Clock | None = None,
    ) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.output_dir = Path(output_dir)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def start(
        self,
        *,
        trial_id: str,
        participant: str,
        kata_id: str,
        treatment: str,
        execution_order: int,
        assistant_name: str | None = None,
        assistant_version: str | None = None,
    ) -> TrialSession:
        """Inicia uma sessão sem sobrescrever registros existentes."""

        self._validate_identity(trial_id, participant, kata_id)
        self._validate_treatment(treatment, assistant_name, assistant_version)
        if not isinstance(execution_order, int) or isinstance(execution_order, bool) or execution_order < 1:
            raise TrialTimerError("execution_order deve ser um inteiro positivo")

        session_path = self._session_path(trial_id)
        output_path = self._output_path(trial_id)
        if session_path.exists() or output_path.exists():
            raise TrialTimerError(f"trial '{trial_id}' já foi iniciado ou concluído")

        started_at = self._aware_now()
        session = TrialSession(
            schema_version="1.0",
            trial_id=trial_id,
            participant=participant.strip(),
            kata_id=kata_id.strip(),
            treatment=treatment,
            execution_order=execution_order,
            started_at=started_at.isoformat(),
            assistant_name=self._clean_optional_text(assistant_name),
            assistant_version=self._clean_optional_text(assistant_version),
        )
        self._write_json_once(session_path, asdict(session))
        return session

    def status(self, trial_id: str) -> TrialStatus:
        """Retorna tempo transcorrido e restante sem alterar a sessão."""

        session = self._load_session(trial_id)
        started_at = datetime.fromisoformat(session.started_at)
        raw_elapsed = self._elapsed(started_at, self._aware_now())
        elapsed = min(raw_elapsed, float(MAX_TRIAL_SECONDS))
        return TrialStatus(
            trial_id=trial_id,
            started_at=session.started_at,
            elapsed_seconds=elapsed,
            remaining_seconds=max(0.0, MAX_TRIAL_SECONDS - raw_elapsed),
            time_box_reached=raw_elapsed >= MAX_TRIAL_SECONDS,
        )

    def finish(
        self,
        trial_id: str,
        *,
        tests_total: int,
        tests_passing: int,
        prompt_count: int | None = None,
    ) -> tuple[TrialRecord, Path]:
        """Encerra um trial válido e grava seu resultado final uma única vez."""

        self._validate_test_counts(tests_total, tests_passing)
        if prompt_count is not None and (
            not isinstance(prompt_count, int) or isinstance(prompt_count, bool) or prompt_count < 0
        ):
            raise TrialTimerError("prompt_count deve ser nulo ou um inteiro não negativo")

        session = self._load_session(trial_id)
        output_path = self._output_path(trial_id)
        if output_path.exists():
            raise TrialTimerError(f"resultado do trial '{trial_id}' já existe e é imutável")

        started_at = datetime.fromisoformat(session.started_at)
        observed_at = self._aware_now()
        raw_elapsed = self._elapsed(started_at, observed_at)
        all_green = tests_passing == tests_total

        if all_green and raw_elapsed <= MAX_TRIAL_SECONDS:
            censored = False
            elapsed = raw_elapsed
            time_to_green = raw_elapsed
            finished_at = observed_at
        elif not all_green and raw_elapsed >= MAX_TRIAL_SECONDS:
            censored = True
            elapsed = float(MAX_TRIAL_SECONDS)
            time_to_green = None
            finished_at = started_at + timedelta(seconds=MAX_TRIAL_SECONDS)
        elif all_green:
            raise TrialTimerError(
                "todos os testes passaram após o limite; não é possível determinar o time-to-green"
            )
        else:
            remaining = MAX_TRIAL_SECONDS - raw_elapsed
            raise TrialTimerError(
                f"trial ainda incompleto; aguarde o time-box ({remaining:.1f} segundos restantes)"
            )

        try:
            record = TrialRecord(
                schema_version=session.schema_version,
                trial_id=session.trial_id,
                participant=session.participant,
                kata_id=session.kata_id,
                treatment=session.treatment,
                execution_order=session.execution_order,
                started_at=session.started_at,
                finished_at=finished_at.isoformat(),
                elapsed_seconds=round(elapsed, 3),
                time_to_green_seconds=None if time_to_green is None else round(time_to_green, 3),
                censored=censored,
                tests_total=tests_total,
                tests_passing=tests_passing,
                success_rate=tests_passing / tests_total * 100,
                prompt_count=prompt_count,
                assistant_name=session.assistant_name,
                assistant_version=session.assistant_version,
            )
        except TrialValidationError as error:
            raise TrialTimerError(str(error)) from error

        self._write_json_once(output_path, record.to_dict())
        return record, output_path

    def _load_session(self, trial_id: str) -> TrialSession:
        self._validate_trial_id(trial_id)
        path = self._session_path(trial_id)
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
            return TrialSession(**payload)
        except FileNotFoundError as error:
            raise TrialTimerError(f"trial '{trial_id}' não foi iniciado") from error
        except (OSError, json.JSONDecodeError, TypeError) as error:
            raise TrialTimerError(f"sessão do trial '{trial_id}' está inválida: {error}") from error

    def _session_path(self, trial_id: str) -> Path:
        return self.sessions_dir / f"{trial_id}.json"

    def _output_path(self, trial_id: str) -> Path:
        return self.output_dir / f"{trial_id}.json"

    def _aware_now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise TrialTimerError("o relógio deve retornar datetime com fuso horário")
        return value

    @staticmethod
    def _elapsed(started_at: datetime, observed_at: datetime) -> float:
        elapsed = (observed_at - started_at).total_seconds()
        if elapsed < 0:
            raise TrialTimerError("o relógio atual não pode ser anterior ao início do trial")
        return elapsed

    @staticmethod
    def _write_json_once(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary.replace(path)
        except FileExistsError as error:
            raise TrialTimerError(f"arquivo temporário já existe: {temporary}") from error
        except OSError as error:
            raise TrialTimerError(f"não foi possível gravar {path}: {error}") from error

    @classmethod
    def _validate_identity(cls, trial_id: str, participant: str, kata_id: str) -> None:
        cls._validate_trial_id(trial_id)
        for name, value in (("participant", participant), ("kata_id", kata_id)):
            if not isinstance(value, str) or not value.strip():
                raise TrialTimerError(f"{name} deve ser um texto não vazio")

    @staticmethod
    def _validate_trial_id(trial_id: str) -> None:
        if not isinstance(trial_id, str) or not TRIAL_ID_PATTERN.fullmatch(trial_id):
            raise TrialTimerError(
                "trial_id deve ter de 1 a 100 caracteres: letras, números, ponto, hífen ou sublinhado"
            )

    @classmethod
    def _validate_treatment(
        cls,
        treatment: str,
        assistant_name: str | None,
        assistant_version: str | None,
    ) -> None:
        if treatment not in TREATMENTS:
            raise TrialTimerError("treatment deve ser 'with_ai' ou 'manual'")
        if treatment == "with_ai" and (
            cls._clean_optional_text(assistant_name) is None
            or cls._clean_optional_text(assistant_version) is None
        ):
            raise TrialTimerError("tratamento with_ai exige assistant_name e assistant_version")
        if treatment == "manual" and (assistant_name is not None or assistant_version is not None):
            raise TrialTimerError("tratamento manual não aceita dados de assistente")

    @staticmethod
    def _validate_test_counts(tests_total: int, tests_passing: int) -> None:
        valid_total = isinstance(tests_total, int) and not isinstance(tests_total, bool) and tests_total > 0
        valid_passing = isinstance(tests_passing, int) and not isinstance(tests_passing, bool)
        if not valid_total:
            raise TrialTimerError("tests_total deve ser um inteiro positivo")
        if not valid_passing or not 0 <= tests_passing <= tests_total:
            raise TrialTimerError("tests_passing deve estar entre 0 e tests_total")

    @staticmethod
    def _clean_optional_text(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None
