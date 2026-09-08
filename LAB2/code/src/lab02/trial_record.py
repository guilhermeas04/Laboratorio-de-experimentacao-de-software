"""Contrato executável para os registros produzidos em cada trial."""

from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, fields
from datetime import datetime
from math import isclose
from typing import Any, Mapping

MAX_TRIAL_SECONDS = 35 * 60
TREATMENTS = {"with_ai", "manual"}


class TrialValidationError(ValueError):
    """Indica que um registro não respeita o protocolo experimental."""


@dataclass(frozen=True, slots=True)
class TrialRecord:
    """Representa o resultado final e imutável de um trial."""

    schema_version: str
    trial_id: str
    participant: str
    kata_id: str
    treatment: str
    execution_order: int
    started_at: str
    finished_at: str
    elapsed_seconds: float
    time_to_green_seconds: float | None
    censored: bool
    tests_total: int
    tests_passing: int
    success_rate: float
    prompt_count: int | None = None
    assistant_name: str | None = None
    assistant_version: str | None = None
    loc: int | None = None
    cyclomatic_complexity_mean: float | None = None
    cyclomatic_complexity_max: int | None = None
    duplication_percentage: float | None = None
    maintainability_index: float | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []

        self._require_text(errors, "schema_version", self.schema_version)
        if self.schema_version != "1.0":
            errors.append("schema_version deve ser '1.0'")
        for name in ("trial_id", "participant", "kata_id"):
            self._require_text(errors, name, getattr(self, name))

        if self.treatment not in TREATMENTS:
            errors.append("treatment deve ser 'with_ai' ou 'manual'")
        if not self._is_integer(self.execution_order) or self.execution_order < 1:
            errors.append("execution_order deve ser um inteiro positivo")

        started = self._parse_datetime(errors, "started_at", self.started_at)
        finished = self._parse_datetime(errors, "finished_at", self.finished_at)
        if started and finished and finished < started:
            errors.append("finished_at não pode ser anterior a started_at")

        if not self._is_number(self.elapsed_seconds) or not 0 <= self.elapsed_seconds <= MAX_TRIAL_SECONDS:
            errors.append(f"elapsed_seconds deve estar entre 0 e {MAX_TRIAL_SECONDS}")
        if not isinstance(self.censored, bool):
            errors.append("censored deve ser booleano")

        valid_tests_total = self._is_integer(self.tests_total) and self.tests_total > 0
        if not valid_tests_total:
            errors.append("tests_total deve ser um inteiro positivo")
        valid_tests_passing = self._is_integer(self.tests_passing)
        if not valid_tests_passing:
            errors.append("tests_passing deve estar entre 0 e tests_total")
        elif valid_tests_total and not 0 <= self.tests_passing <= self.tests_total:
            errors.append("tests_passing deve estar entre 0 e tests_total")

        if valid_tests_total and valid_tests_passing:
            expected_rate = self.tests_passing / self.tests_total * 100
            if not self._is_number(self.success_rate) or not isclose(
                self.success_rate, expected_rate, abs_tol=1e-6
            ):
                errors.append("success_rate deve ser 100 * tests_passing / tests_total")

        if self.censored is True:
            if self.elapsed_seconds != MAX_TRIAL_SECONDS:
                errors.append(f"trial censurado deve registrar {MAX_TRIAL_SECONDS} segundos")
            if self.time_to_green_seconds is not None:
                errors.append("trial censurado não pode ter time_to_green_seconds")
            if self.tests_passing == self.tests_total:
                errors.append("trial censurado deve ter pelo menos um teste falhando")
        elif self.censored is False:
            if not self._is_number(self.time_to_green_seconds):
                errors.append("trial concluído deve ter time_to_green_seconds")
            elif not self._is_number(self.elapsed_seconds) or not isclose(
                self.time_to_green_seconds, self.elapsed_seconds, abs_tol=1e-6
            ):
                errors.append("time_to_green_seconds deve ser igual a elapsed_seconds")
            if self.tests_passing != self.tests_total:
                errors.append("trial não censurado deve ter todos os testes passando")

        if self.treatment == "with_ai":
            self._require_text(errors, "assistant_name", self.assistant_name)
            self._require_text(errors, "assistant_version", self.assistant_version)
        elif self.treatment == "manual" and (self.assistant_name is not None or self.assistant_version is not None):
            errors.append("tratamento manual não pode identificar assistente de IA")

        self._optional_non_negative_integer(errors, "prompt_count", self.prompt_count)
        self._optional_non_negative_integer(errors, "loc", self.loc)
        self._optional_non_negative_integer(
            errors, "cyclomatic_complexity_max", self.cyclomatic_complexity_max
        )
        self._optional_non_negative_number(
            errors, "cyclomatic_complexity_mean", self.cyclomatic_complexity_mean
        )
        self._optional_percentage(errors, "duplication_percentage", self.duplication_percentage)
        self._optional_percentage(errors, "maintainability_index", self.maintainability_index)

        if (
            self._is_number(self.cyclomatic_complexity_mean)
            and self._is_integer(self.cyclomatic_complexity_max)
            and self.cyclomatic_complexity_mean > self.cyclomatic_complexity_max
        ):
            errors.append("complexidade média não pode superar a complexidade máxima")

        if errors:
            raise TrialValidationError("Registro de trial inválido:\n- " + "\n- ".join(errors))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TrialRecord":
        """Cria e valida um registro, rejeitando campos ausentes ou desconhecidos."""

        known = {field.name for field in fields(cls)}
        required = {
            field.name
            for field in fields(cls)
            if field.default is MISSING and field.default_factory is MISSING
        }
        unknown = sorted(set(data) - known)
        missing = sorted(required - set(data))
        problems = []
        if unknown:
            problems.append(f"campos desconhecidos: {', '.join(unknown)}")
        if missing:
            problems.append(f"campos obrigatórios ausentes: {', '.join(missing)}")
        if problems:
            raise TrialValidationError("; ".join(problems))
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Converte o registro validado em estrutura serializável."""

        return asdict(self)

    @staticmethod
    def _parse_datetime(errors: list[str], name: str, value: Any) -> datetime | None:
        if not isinstance(value, str):
            errors.append(f"{name} deve ser texto no formato ISO 8601")
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{name} deve usar o formato ISO 8601")
            return None
        if parsed.tzinfo is None:
            errors.append(f"{name} deve incluir fuso horário")
            return None
        return parsed

    @staticmethod
    def _require_text(errors: list[str], name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} deve ser um texto não vazio")

    @staticmethod
    def _is_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _optional_non_negative_integer(cls, errors: list[str], name: str, value: Any) -> None:
        if value is not None and (not cls._is_integer(value) or value < 0):
            errors.append(f"{name} deve ser nulo ou um inteiro não negativo")

    @classmethod
    def _optional_non_negative_number(cls, errors: list[str], name: str, value: Any) -> None:
        if value is not None and (not cls._is_number(value) or value < 0):
            errors.append(f"{name} deve ser nulo ou um número não negativo")

    @classmethod
    def _optional_percentage(cls, errors: list[str], name: str, value: Any) -> None:
        if value is not None and (not cls._is_number(value) or not 0 <= value <= 100):
            errors.append(f"{name} deve ser nulo ou estar entre 0 e 100")
