from lab02.kata_catalog import KATAS_BY_ID
from lab02.kata_contract import run_definition


def test_kata_02_cases_are_accepted(solver):
    results = run_definition(KATAS_BY_ID["kata-02"], solver)
    assert all(passed for _, passed, _ in results), results
