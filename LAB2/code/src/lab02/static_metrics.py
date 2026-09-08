"""Pipeline de métricas estáticas para a RQ3."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze

from .duplication import duplication_percentage

LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = LAB2_ROOT / "code" / "static_metrics.toml"
DEFAULT_METRICS_DIR = LAB2_ROOT / "data" / "processed"

STATUS_OK = "ok"
STATUS_EMPTY = "empty_source"
STATUS_INVALID = "invalid_code"
STATUS_MISSING = "missing_source"


class StaticMetricsError(RuntimeError):
    """Indica falha operacional na coleta de métricas estáticas."""


@dataclass(frozen=True, slots=True)
class StaticMetricsResult:
    """Saída estruturada associada a um trial, alinhada ao esquema da #47."""

    trial_id: str
    source_path: str
    status: str
    loc: int | None
    cyclomatic_complexity_mean: float | None
    cyclomatic_complexity_max: int | None
    duplication_percentage: float | None
    maintainability_index: float | None
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def metric_fields(self) -> dict[str, Any]:
        """Campos que podem ser mesclados em um TrialRecord."""

        return {
            "loc": self.loc,
            "cyclomatic_complexity_mean": self.cyclomatic_complexity_mean,
            "cyclomatic_complexity_max": self.cyclomatic_complexity_max,
            "duplication_percentage": self.duplication_percentage,
            "maintainability_index": self.maintainability_index,
        }


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {"radon": {"loc_field": "sloc"}, "duplication": {"min_block_lines": 4}}
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise StaticMetricsError(f"configuração inválida em {config_path}")
    return data


def discover_python_files(source: Path) -> list[Path]:
    root = Path(source)
    if not root.exists():
        raise StaticMetricsError(f"caminho de origem inexistente: {root}")
    if root.is_file():
        if root.suffix != ".py":
            raise StaticMetricsError(f"arquivo de origem precisa ser .py: {root}")
        return [root]
    files = sorted(path for path in root.rglob("*.py") if path.is_file())
    return files


def analyze_trial_source(
    *,
    trial_id: str,
    source: Path,
    config_path: Path | None = None,
) -> StaticMetricsResult:
    """Analisa o código final de um trial e devolve métricas ou ausência explícita."""

    if not isinstance(trial_id, str) or not trial_id.strip():
        raise StaticMetricsError("trial_id deve ser um texto não vazio")

    config = load_config(config_path)
    loc_field = str(config.get("radon", {}).get("loc_field", "sloc"))
    min_block_lines = int(config.get("duplication", {}).get("min_block_lines", 4))
    source_path = Path(source)

    try:
        files = discover_python_files(source_path)
    except StaticMetricsError as error:
        return StaticMetricsResult(
            trial_id=trial_id.strip(),
            source_path=str(source_path),
            status=STATUS_MISSING,
            loc=None,
            cyclomatic_complexity_mean=None,
            cyclomatic_complexity_max=None,
            duplication_percentage=None,
            maintainability_index=None,
            messages=[str(error)],
        )

    if not files:
        return StaticMetricsResult(
            trial_id=trial_id.strip(),
            source_path=str(source_path),
            status=STATUS_EMPTY,
            loc=None,
            cyclomatic_complexity_mean=None,
            cyclomatic_complexity_max=None,
            duplication_percentage=None,
            maintainability_index=None,
            messages=["nenhum arquivo .py encontrado para análise"],
        )

    sources: list[str] = []
    messages: list[str] = []
    total_loc = 0
    complexities: list[int] = []
    mi_values: list[tuple[float, int]] = []
    invalid_files = 0
    empty_files = 0

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        if not text.strip():
            empty_files += 1
            messages.append(f"arquivo vazio ignorado: {file_path.name}")
            continue
        try:
            raw = analyze(text)
            blocks = cc_visit(text)
            mi_score = mi_visit(text, multi=True)
        except SyntaxError as error:
            invalid_files += 1
            messages.append(f"código inválido em {file_path.name}: {error.msg}")
            continue
        except Exception as error:
            invalid_files += 1
            messages.append(f"falha do Radon em {file_path.name}: {error}")
            continue

        loc_value = getattr(raw, loc_field, None)
        if not isinstance(loc_value, int):
            invalid_files += 1
            messages.append(f"resultado ausente de LOC em {file_path.name}")
            continue

        sources.append(text)
        total_loc += loc_value
        complexities.extend(int(block.complexity) for block in blocks)
        mi_values.append((float(mi_score), max(loc_value, 1)))

    if not sources:
        if invalid_files:
            status = STATUS_INVALID
            detail = "nenhum arquivo pôde ser analisado por erro de sintaxe ou da ferramenta"
        else:
            status = STATUS_EMPTY
            detail = "apenas arquivos vazios foram encontrados"
        return StaticMetricsResult(
            trial_id=trial_id.strip(),
            source_path=str(source_path),
            status=status,
            loc=None,
            cyclomatic_complexity_mean=None,
            cyclomatic_complexity_max=None,
            duplication_percentage=None,
            maintainability_index=None,
            messages=[*messages, detail],
        )

    if complexities:
        mean_cc = round(sum(complexities) / len(complexities), 3)
        max_cc = max(complexities)
    else:
        # Módulos só com atribuições podem não expor blocos CC; isso não é falha.
        mean_cc = 0.0
        max_cc = 0
        messages.append("nenhum bloco ciclomático encontrado; complexidade registrada como 0")

    weight_sum = sum(weight for _mi, weight in mi_values)
    maintainability = round(
        sum(mi * weight for mi, weight in mi_values) / weight_sum,
        3,
    )
    duplication = duplication_percentage(sources, min_block_lines=min_block_lines)

    status = STATUS_OK
    if invalid_files:
        messages.append(
            f"{invalid_files} arquivo(s) inválido(s) foram excluídos; métricas usam só o restante"
        )

    return StaticMetricsResult(
        trial_id=trial_id.strip(),
        source_path=str(source_path),
        status=status,
        loc=total_loc,
        cyclomatic_complexity_mean=mean_cc,
        cyclomatic_complexity_max=max_cc,
        duplication_percentage=duplication,
        maintainability_index=maintainability,
        messages=messages,
    )


def write_metrics_result(result: StaticMetricsResult, output_path: Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise StaticMetricsError(f"resultado já existe e não será sobrescrito: {path}")
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def default_output_path(trial_id: str, metrics_dir: Path | None = None) -> Path:
    directory = Path(metrics_dir) if metrics_dir is not None else DEFAULT_METRICS_DIR
    return directory / f"metrics-{trial_id}.json"
