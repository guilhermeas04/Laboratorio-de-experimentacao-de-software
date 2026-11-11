"""Textos interpretativos de G3 e G4 gerados a partir dos resultados."""

from __future__ import annotations

import math

import pandas as pd

from .plots_s02 import TEST_LABELS

TEXT_SITUATIONS = {
    "ideal": "situação ideal",
    "small_sample": "amostra pequena",
    "extreme_outlier": "presença de outliers",
}


def _label_test(name: str) -> str:
    return TEST_LABELS.get(name, name)


def _label_situation(name: str) -> str:
    return TEXT_SITUATIONS.get(name, name)


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def _hours(value: float) -> str:
    return f"{value:.2f} h".replace(".", ",")


def monte_carlo_margin(alpha: float, replications: int) -> float:
    """Meia largura do IC de 95% para uma proporção igual a alpha."""

    return 1.96 * math.sqrt(alpha * (1 - alpha) / replications)


def classify_type_i(rate: float, alpha: float, replications: int) -> str:
    margin = monte_carlo_margin(alpha, replications)
    if rate > alpha + margin:
        return "liberal"
    if rate < alpha - margin:
        return "conservador"
    return "adequado"


def interpret_g3(type_i: pd.DataFrame) -> str:
    alpha = float(type_i["alpha"].iloc[0])
    reps = int(type_i["replications"].iloc[0])
    margin = monte_carlo_margin(alpha, reps)
    frame = type_i.copy()
    frame["classification"] = [classify_type_i(rate, alpha, reps) for rate in frame["rejection_rate"]]

    sentences = []
    for test in ("mann_whitney", "welch_t"):
        rows = frame[frame["test_name"] == test]
        if rows.empty:
            continue
        rates = ", ".join(f"{_pct(row.rejection_rate, 2)} na {_label_situation(row.situation)}" for row in rows.itertuples())
        classes = set(rows["classification"])
        if classes == {"adequado"}:
            verdict = f"ficou dentro da margem de Monte Carlo de ±{_pct(margin, 2)} em torno de {_pct(alpha, 0)}"
        elif len(classes) == 1:
            verdict = f"foi {classes.pop()} em todas as situações"
        else:
            deviating = rows[rows["classification"] != "adequado"]
            verdict = "foi " + ", ".join(
                f"{row.classification} na {_label_situation(row.situation)}" for row in deviating.itertuples()
            ) + " e adequado nas demais"
        sentences.append(f"O {_label_test(test)} teve erro tipo I de {rates} e {verdict}.")

    sentences.append(_type_i_reason(frame))
    return " ".join(sentences)


def _type_i_reason(frame: pd.DataFrame) -> str:
    welch = frame[frame["test_name"] == "welch_t"]
    mann = frame[frame["test_name"] == "mann_whitney"]
    if (welch["classification"] == "conservador").any():
        return (
            "O desvio do Welch vem da assimetria lognormal e das caudas longas, que inflam a variância "
            "amostral e encolhem a estatística t, enquanto o Mann-Whitney usa postos e quase não sente valores extremos."
        )
    if (welch["classification"] == "liberal").any():
        return (
            "O excesso de rejeições do Welch indica que a aproximação t falha com dados muito assimétricos "
            "e amostras pequenas, enquanto o Mann-Whitney, baseado em postos, preserva melhor o nível nominal."
        )
    if (mann["classification"] == "conservador").any():
        return (
            "O Mann-Whitney fica conservador em amostras pequenas porque a distribuição dos postos é discreta "
            "e poucos p-valores possíveis ficam abaixo de alpha."
        )
    return (
        "Como os dois grupos vêm da mesma distribuição sob H0, a troca de pressupostos não alterou de forma "
        "relevante o controle do erro tipo I."
    )


def interpret_g4(power: pd.DataFrame) -> str:
    frame = power[power["effect_hours"] > 0]
    pivot = frame.pivot_table(index=["situation", "effect_hours"], columns="test_name", values="power").reset_index()
    pivot["diff"] = pivot["mann_whitney"] - pivot["welch_t"]

    ideal = pivot[pivot["situation"] == "ideal"]
    reference = ideal if not ideal.empty else pivot
    leader = "mann_whitney" if reference["diff"].mean() > 0 else "welch_t"
    other = "welch_t" if leader == "mann_whitney" else "mann_whitney"
    largest = reference.loc[reference["effect_hours"].idxmax()]
    smallest = reference.loc[reference["effect_hours"].idxmin()]

    sentences = [
        f"Na situação ideal, o {_label_test(leader)} teve maior poder, chegando a {_pct(largest[leader])} "
        f"contra {_pct(largest[other])} do {_label_test(other)} no efeito de {_hours(largest['effect_hours'])}.",
        f"A diferença cresceu com o efeito, de {_pct(abs(smallest['diff']))} em {_hours(smallest['effect_hours'])} "
        f"para {_pct(abs(largest['diff']))} em {_hours(largest['effect_hours'])}.",
    ]

    switches = []
    for situation, group in pivot.groupby("situation"):
        signs = set((group["diff"] > 0).tolist())
        mean_leader = "mann_whitney" if group["diff"].mean() > 0 else "welch_t"
        if len(signs) > 1:
            switches.append(f"na {_label_situation(situation)} a vantagem alternou conforme o efeito")
        elif mean_leader != leader:
            switches.append(f"na {_label_situation(situation)} o {_label_test(mean_leader)} passou à frente")
    if switches:
        sentences.append("A vantagem mudou de lado " + "; ".join(switches) + ".")
    else:
        gaps = pivot.groupby("situation")["diff"].mean().abs()
        widest, narrowest = gaps.idxmax(), gaps.idxmin()
        sentences.append(
            f"A vantagem não mudou de lado em nenhuma situação: a diferença média foi maior na "
            f"{_label_situation(widest)} ({_pct(gaps.max())}) e menor na {_label_situation(narrowest)} "
            f"({_pct(gaps.min())}), onde os dois testes perdem poder."
        )
    return " ".join(sentences)
