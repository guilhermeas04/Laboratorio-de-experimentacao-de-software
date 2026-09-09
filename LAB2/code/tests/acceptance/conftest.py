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
