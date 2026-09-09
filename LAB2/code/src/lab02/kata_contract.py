"""Shared contract and deterministic execution helpers for the six katas."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class AcceptanceCase:
    """One frozen acceptance example; invalid cases expect ValueError."""

    name: str
    input: Any
    expected: Any = None
    invalid: bool = False


@dataclass(frozen=True, slots=True)
class KataDefinition:
    """Public metadata and acceptance cases for one kata."""

    kata_id: str
    title: str
    cases: tuple[AcceptanceCase, ...]


def load_solver(path: Path) -> Callable[[Any], Any]:
    """Load a participant module without importing any reference solution."""

    module_path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location("participant_solution", module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"nao foi possivel carregar a solucao: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    solver = getattr(module, "solve", None)
    if not callable(solver):
        raise ValueError("a solucao deve exportar uma funcao solve(value)")
    return solver


def execute_case(solver: Callable[[Any], Any], case: AcceptanceCase) -> tuple[bool, str]:
    """Execute one case with an isolated input and return result plus message."""

    try:
        actual = solver(deepcopy(case.input))
    except ValueError as error:
        if case.invalid:
            return True, "ValueError esperado"
        return False, f"erro inesperado: ValueError({error})"
    except Exception as error:  # noqa: BLE001 - report participant failures uniformly
        if case.invalid:
            return False, f"erro invalido: esperado ValueError, recebido {type(error).__name__}"
        return False, f"erro inesperado: {type(error).__name__}: {error}"

    if case.invalid:
        return False, "esperado ValueError para entrada invalida"
    if actual != case.expected:
        return False, f"esperado {case.expected!r}, recebido {actual!r}"
    return True, "ok"


def run_definition(definition: KataDefinition, solver: Callable[[Any], Any]) -> list[tuple[str, bool, str]]:
    """Run every frozen case in declaration order."""

    return [(case.name, *execute_case(solver, case)) for case in definition.cases]


def load_module(path: Path) -> ModuleType:
    """Load a solution module for callers that need module metadata."""

    module_path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location("participant_solution", module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"nao foi possivel carregar a solucao: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
