from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_final_dashboard_contains_required_sections_and_artifacts() -> None:
    dashboard = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")

    for section in (
        "1. Cenário",
        "2. Os dados — G1",
        "3. Como os testes funcionam — G2",
        "4. Erro tipo I — G3",
        "5. Poder — G4",
        "6. Dados reais",
        "7. Conclusão",
    ):
        assert section in dashboard
    assert dashboard.index("1. Cenário") < dashboard.index("2. Os dados — G1") < dashboard.index("7. Conclusão")
    for artifact in ("g1_histograms.png", "g2_null_distribution.png", "g3_type_i_error.png", "g4_power.png"):
        assert artifact in dashboard
    assert "p-valor" in dashboard
    assert "cohens_d" in dashboard
    assert "rank_biserial" in dashboard
    assert "github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software" in dashboard
    assert "github.com/users/guilhermeas04/projects/3" in dashboard