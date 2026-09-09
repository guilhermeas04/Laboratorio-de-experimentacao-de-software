from __future__ import annotations

from pathlib import Path

import pytest

from lab02.kata_contract import load_solver


@pytest.fixture
def solver(request):
    path = request.config.getoption("--candidate")
    if path is None:
        pytest.skip("use --candidate=path\\para\\solucao.py para executar uma solucao")
    return load_solver(Path(path))


def pytest_addoption(parser):
    parser.addoption("--candidate", action="store", default=None)
    parser.addoption(
        "--kata-id",
        action="store",
        choices=tuple(f"kata-{index:02d}" for index in range(1, 7)),
        default=None,
    )


def pytest_collection_modifyitems(config, items):
    candidate = config.getoption("--candidate")
    kata_id = config.getoption("--kata-id")
    if candidate and kata_id is None:
        raise pytest.UsageError("--kata-id é obrigatório quando --candidate é informado")
    if kata_id is None:
        return

    selected_file = f"test_{kata_id.replace('-', '_')}.py"
    skip = pytest.mark.skip(reason=f"execução selecionada para {kata_id}")
    for item in items:
        if "acceptance" in item.path.parts and item.path.name != selected_file:
            item.add_marker(skip)
