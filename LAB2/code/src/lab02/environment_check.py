"""Verificação automatizada do ambiente experimental do LAB02."""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .static_metrics import STATUS_OK, analyze_trial_source
from .trial_timer import TrialTimer

LAB2_ROOT = Path(__file__).resolve().parents[3]
DEMO_TRIAL_ID = "DEMO-SMOKE-P00-K00-MANUAL"


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True)
class SmokeReport:
    checks: list[CheckResult] = field(default_factory=list)
    demo_trial_path: Path | None = None
    demo_metrics_path: Path | None = None

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


Clock = Callable[[], datetime]


class EnvironmentChecker:
    """Executa o smoke test sem gravar nada em data/raw."""

    def __init__(
        self,
        *,
        lab2_root: Path = LAB2_ROOT,
        demo_dir: Path | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.lab2_root = Path(lab2_root)
        self.demo_dir = Path(demo_dir) if demo_dir is not None else self.lab2_root / "data" / "demo"
        self._clock = clock

    def run(self) -> SmokeReport:
        report = SmokeReport()
        report.checks.append(self._check_python())
        report.checks.append(self._check_directories())
        report.checks.append(self._check_radon())
        report.checks.append(self._check_package_imports())
        report.checks.extend(self._run_demo_integration(report))
        return report

    def _check_python(self) -> CheckResult:
        version = sys.version_info
        ok = version.major == 3 and version.minor == 13
        detail = (
            f"Python {platform.python_version()} em {sys.executable}"
            if ok
            else f"esperado Python 3.13.x; encontrado {platform.python_version()}"
        )
        return CheckResult("python", ok, detail)

    def _check_directories(self) -> CheckResult:
        required = (
            self.lab2_root / "code",
            self.lab2_root / "data" / "examples",
            self.lab2_root / "data" / "raw",
            self.lab2_root / "data" / "processed",
            self.lab2_root / "data" / "sessions",
            self.demo_dir,
            self.lab2_root / "docs",
            self.lab2_root / "reports",
        )
        missing = [str(path.relative_to(self.lab2_root)) for path in required if not path.exists()]
        if missing:
            return CheckResult("diretorios", False, "ausentes: " + ", ".join(missing))
        return CheckResult("diretorios", True, "estrutura LAB2 presente")

    def _check_radon(self) -> CheckResult:
        if importlib.util.find_spec("radon") is None:
            return CheckResult(
                "radon",
                False,
                "pacote radon ausente; instale requirements-dev.txt e o pacote lab02",
            )
        try:
            import radon
            from radon.complexity import cc_visit
            from radon.metrics import mi_visit
            from radon.raw import analyze

            sample = "def ok():\n    return 1\n"
            analyze(sample)
            cc_visit(sample)
            mi_visit(sample, True)
        except Exception as error:
            return CheckResult("radon", False, f"radon instalado, mas falhou: {error}")
        return CheckResult("radon", True, f"radon {radon.__version__} operacional")

    def _check_package_imports(self) -> CheckResult:
        try:
            from lab02 import TrialTimer, analyze_trial_source
        except Exception as error:
            return CheckResult("pacote_lab02", False, f"falha ao importar lab02: {error}")
        if TrialTimer is None or analyze_trial_source is None:
            return CheckResult("pacote_lab02", False, "símbolos essenciais ausentes")
        return CheckResult("pacote_lab02", True, "TrialTimer e analyze_trial_source disponíveis")

    def _run_demo_integration(self, report: SmokeReport) -> list[CheckResult]:
        checks: list[CheckResult] = []
        sessions_dir = self.demo_dir / "sessions"
        output_dir = self.demo_dir / "raw"
        metrics_dir = self.demo_dir / "metrics"
        source = self.lab2_root / "code" / "tests" / "fixtures" / "metrics" / "valid"

        for path in (sessions_dir, output_dir, metrics_dir):
            path.mkdir(parents=True, exist_ok=True)

        for leftover in (
            sessions_dir / f"{DEMO_TRIAL_ID}.json",
            output_dir / f"{DEMO_TRIAL_ID}.json",
            metrics_dir / f"metrics-{DEMO_TRIAL_ID}.json",
        ):
            if leftover.exists():
                leftover.unlink()

        started = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
        ticks = iter(
            [
                started,
                started + timedelta(seconds=90),
                started + timedelta(seconds=90),
            ]
        )

        def clock() -> datetime:
            try:
                return next(ticks)
            except StopIteration:
                return started + timedelta(seconds=90)

        try:
            timer = TrialTimer(sessions_dir=sessions_dir, output_dir=output_dir, clock=clock)
            timer.start(
                trial_id=DEMO_TRIAL_ID,
                participant="participant-demo",
                kata_id="kata-demo",
                treatment="manual",
                execution_order=1,
            )
            status = timer.status(DEMO_TRIAL_ID)
            record, trial_path = timer.finish(
                DEMO_TRIAL_ID,
                tests_total=3,
                tests_passing=3,
            )
        except Exception as error:
            checks.append(CheckResult("integracao_timer", False, f"falha no trial demo: {error}"))
            return checks

        raw_root = (self.lab2_root / "data" / "raw").resolve()
        if trial_path.resolve().is_relative_to(raw_root):
            checks.append(
                CheckResult(
                    "isolamento_demo",
                    False,
                    f"demonstração gravou em data/raw: {trial_path}",
                )
            )
            return checks

        checks.append(
            CheckResult(
                "integracao_timer",
                True,
                f"trial demo {record.trial_id} em {trial_path} (tempo={record.elapsed_seconds}s)",
            )
        )
        report.demo_trial_path = trial_path

        if not source.exists():
            checks.append(
                CheckResult(
                    "integracao_metricas",
                    False,
                    f"fixture de métricas ausente: {source}",
                )
            )
            return checks

        try:
            metrics = analyze_trial_source(trial_id=DEMO_TRIAL_ID, source=source)
            metrics_path = metrics_dir / f"metrics-{DEMO_TRIAL_ID}.json"
            metrics_path.write_text(
                json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception as error:
            checks.append(CheckResult("integracao_metricas", False, f"falha nas métricas demo: {error}"))
            return checks

        ok = metrics.status == STATUS_OK and metrics.loc is not None
        detail = (
            f"métricas demo status={metrics.status} loc={metrics.loc} arquivo={metrics_path}"
            if ok
            else f"métricas demo incompletas: status={metrics.status} mensagens={metrics.messages}"
        )
        checks.append(CheckResult("integracao_metricas", ok, detail))
        if ok:
            report.demo_metrics_path = metrics_path

        checks.append(CheckResult("isolamento_demo", True, "saídas gravadas apenas em data/demo"))
        checks.append(
            CheckResult(
                "status_timer",
                status.elapsed_seconds >= 0,
                f"status demo decorrido={status.elapsed_seconds}s",
            )
        )
        return checks
